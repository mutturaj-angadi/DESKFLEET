"""
app.graph.nodes
================
The four agent nodes. Each node function takes the current
`TicketState` and returns a partial dict of updates — LangGraph
merges that back into state. Nodes never call tools directly; the
Researcher routes every tool invocation through
`app.tools.registry.call_tool` so the allowlist can never be
bypassed.
"""

from __future__ import annotations

import re
import time

from openai import RateLimitError
from pydantic import BaseModel, Field

from app.config import settings
from app.graph.llm import structured_completion, tool_calling_completion
from app.graph.state import TicketState
from app.metrics.cost import count_tokens, estimate_cost_usd
from app.tools.registry import TOOL_SCHEMAS, call_tool


def _with_node_metric(
    state: TicketState, updates: dict, *, node: str, started: float, text: str = ""
) -> dict:
    """Attach a durable per-node latency/token/cost record to graph state."""
    tokens = count_tokens(text)
    metrics = list(state.get("node_metrics", []))
    metrics.append(
        {
            "node": node,
            "latency_ms": (time.monotonic() - started) * 1000,
            "tokens": tokens,
            "cost_usd": estimate_cost_usd(tokens),
        }
    )
    updates["node_metrics"] = metrics
    return updates


# ---------------------------------------------------------------- Classifier
class Classification(BaseModel):
    category: str = Field(description="One of: order, product, refund, other")
    reasoning: str = Field(description="One-sentence justification")


def classifier_node(state: TicketState) -> dict:
    started = time.monotonic()
    try:
        result = structured_completion(
            system_prompt=(
                "You are a support-ticket classifier. Read the ticket and assign "
                "exactly one category: 'order' (shipping/status questions), "
                "'product' (questions about a product's features/availability), "
                "'refund' (refund or return requests), or 'other' (anything else)."
            ),
            user_prompt=state["ticket_body"],
            response_model=Classification,
        )
    except RateLimitError:
        return _with_node_metric(
            state,
            {"llm_unavailable_reason": "The AI provider is temporarily rate-limited."},
            node="classifier",
            started=started,
            text=state["ticket_body"],
        )
    category = result.category.strip().lower()
    if category not in {"order", "product", "refund", "other"}:
        category = "other"
    return _with_node_metric(
        state,
        {"category": category},
        node="classifier",
        started=started,
        text=state["ticket_body"] + result.reasoning,
    )


# ---------------------------------------------------- Deterministic fallback
def fallback_node(state: TicketState) -> dict:
    """Resolve straightforward order/product lookups without an LLM.

    This keeps the operator workflow available during a temporary provider
    outage or quota limit. Ambiguous requests still escalate for human review.
    """
    ticket = state["ticket_body"]
    order_match = re.search(r"\bORD-\d+\b", state.get("order_id") or ticket, re.I)
    if order_match:
        order_id = order_match.group(0).upper()
        record = call_tool("get_order_status", {"order_id": order_id})
        if record["status"] != "ok":
            return {
                "category": "order",
                "tool_calls": [record],
                "decision": "ESCALATE",
                "escalation_reason": record.get("result", {}).get(
                    "error", "Order lookup could not be completed."
                ),
            }
        order = record["result"]
        details = [
            f"Your order {order_id} is currently {order.get('status', 'being processed') }."
        ]
        if order.get("eta"):
            details.append(f"Expected delivery: {order['eta']}.")
        if order.get("tracking_number"):
            details.append(f"Tracking number: {order['tracking_number']}.")
        return {
            "category": "order",
            "facts": [{"tool": record["tool_name"], "data": order}],
            "tool_calls": [record],
            "draft": " ".join(details),
            "decision": "RESOLVED",
        }

    product_match = re.search(r"\b(?:P|PRD)-\d+\b", ticket, re.I)
    if product_match:
        product_id = product_match.group(0).upper().replace("PRD-", "P-")
        record = call_tool("get_product", {"product_id": product_id})
        if record["status"] != "ok":
            return {
                "category": "product",
                "tool_calls": [record],
                "decision": "ESCALATE",
                "escalation_reason": record.get("result", {}).get(
                    "error", "Product lookup could not be completed."
                ),
            }
        product = record["result"]
        stock = "in stock" if product.get("in_stock") else "currently out of stock"
        reply = (
            f"{product.get('title', product_id)} costs ${product.get('price')} and is {stock}. "
            f"{product.get('description', '')}"
        ).strip()
        return {
            "category": "product",
            "facts": [{"tool": record["tool_name"], "data": product}],
            "tool_calls": [record],
            "draft": reply,
            "decision": "RESOLVED",
        }

    return {
        "category": "other",
        "decision": "ESCALATE",
        "escalation_reason": (
            "The AI provider is rate-limited and this request needs a support agent."
        ),
    }


# ---------------------------------------------------------------- Researcher
def researcher_node(state: TicketState) -> dict:
    """Tool-calling agent: decides which allowlisted tools to invoke
    based on the ticket + category, then records both the raw tool
    outputs (as `facts`) and a full audit trail (`tool_calls`).
    """
    user_prompt = (
        f"Ticket category: {state['category']}\n"
        f"Order ID mentioned (if any): {state.get('order_id') or 'none'}\n"
        f"Ticket:\n{state['ticket_body']}\n\n"
        "Call whichever tools you need to gather the facts required to answer "
        "this ticket. Only call tools that are actually relevant."
    )
    started = time.monotonic()
    response = tool_calling_completion(
        system_prompt=(
            "You are a research agent for a customer support system. You have "
            "access to order/product lookup tools. Call the tools needed to "
            "gather facts before handing off to the reply-drafting agent. Do "
            "not guess at facts you can look up."
        ),
        user_prompt=user_prompt,
        tools=TOOL_SCHEMAS,
    )

    facts: list[dict] = list(state.get("facts", []))
    tool_calls: list[dict] = list(state.get("tool_calls", []))

    for call in response["tool_calls"]:
        record = call_tool(call["name"], call["arguments"])
        tool_calls.append(record)
        if record["status"] == "ok":
            facts.append({"tool": record["tool_name"], "data": record["result"]})

    return _with_node_metric(
        state,
        {"facts": facts, "tool_calls": tool_calls},
        node="researcher",
        started=started,
        text=user_prompt + (response.get("content") or ""),
    )


# ---------------------------------------------------------------- Responder
class DraftReply(BaseModel):
    reply: str = Field(description="The drafted customer-facing reply")


def responder_node(state: TicketState) -> dict:
    started = time.monotonic()
    facts_text = "\n".join(f"- {f['tool']}: {f['data']}" for f in state.get("facts", []))
    feedback = None
    conversation = list(state.get("conversation", []))
    if conversation:
        feedback = conversation[-1].get("feedback")

    user_prompt = (
        f"Ticket:\n{state['ticket_body']}\n\n"
        f"Facts gathered so far:\n{facts_text or '(no facts gathered)'}\n\n"
        + (f"Reviewer feedback on your last draft: {feedback}\n\n" if feedback else "")
        + "Draft a helpful, concise customer-facing reply. Only state facts that "
        "appear above — never invent an order status, price, or ETA."
    )
    result = structured_completion(
        system_prompt=(
            "You are a customer support reply-drafting agent. Your reply must be "
            "grounded strictly in the facts provided — do not invent details."
        ),
        user_prompt=user_prompt,
        response_model=DraftReply,
    )

    iteration = state.get("iterations", 0)
    conversation.append({"iteration": iteration, "draft": result.reply, "feedback": None})
    return _with_node_metric(
        state,
        {"draft": result.reply, "conversation": conversation},
        node="responder",
        started=started,
        text=user_prompt + result.reply,
    )


# ---------------------------------------------------------------- Reviewer
class ReviewVerdict(BaseModel):
    verdict: str = Field(description="One of: approve, retry, escalate")
    reason: str = Field(description="One-sentence justification")


def reviewer_node(state: TicketState) -> dict:
    started = time.monotonic()
    facts_text = "\n".join(f"- {f['tool']}: {f['data']}" for f in state.get("facts", []))
    user_prompt = (
        f"Ticket:\n{state['ticket_body']}\n\n"
        f"Facts available:\n{facts_text or '(none)'}\n\n"
        f"Drafted reply:\n{state['draft']}\n\n"
        "Review the draft: is every claim grounded in the facts above? Is the "
        "tone appropriate? Respond with verdict 'approve' if it's ready to send, "
        "'retry' if it needs a specific fix the responder can make, or "
        "'escalate' if this needs a human (e.g. facts are missing or the "
        "situation is out of policy scope)."
    )
    result = structured_completion(
        system_prompt=(
            "You are a strict quality reviewer for customer support replies. "
            "Flag any claim not backed by the facts provided."
        ),
        user_prompt=user_prompt,
        response_model=ReviewVerdict,
    )

    verdict = result.verdict.strip().lower()
    if verdict not in {"approve", "retry", "escalate"}:
        verdict = "escalate"

    iterations = state.get("iterations", 0)
    conversation = list(state.get("conversation", []))
    if conversation:
        conversation[-1]["feedback"] = result.reason

    updates: dict = {"conversation": conversation, "_reviewer_reason": result.reason}

    if verdict == "approve":
        updates["decision"] = "RESOLVED"
    elif verdict == "retry" and iterations + 1 < settings.max_reviewer_iterations:
        updates["iterations"] = iterations + 1
    else:
        # Either the reviewer said escalate, or we've hit the iteration cap.
        updates["decision"] = "ESCALATE"
        if iterations + 1 >= settings.max_reviewer_iterations and verdict == "retry":
            updates["escalation_reason"] = (
                f"Exceeded max reviewer iterations ({settings.max_reviewer_iterations}) "
                f"without approval. Last reviewer note: {result.reason}"
            )
        else:
            updates["escalation_reason"] = result.reason

    return _with_node_metric(
        state,
        updates,
        node="reviewer",
        started=started,
        text=user_prompt + result.reason,
    )
