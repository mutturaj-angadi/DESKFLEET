from unittest.mock import patch

from app.config import settings
from app.graph.edges import route_after_input_guardrail, route_after_reviewer
from app.graph.nodes import (
    Classification,
    ReviewVerdict,
    classifier_node,
    fallback_node,
    reviewer_node,
)
from app.graph.state import new_state


def test_classifier_sets_valid_category():
    with patch(
        "app.graph.nodes.structured_completion",
        return_value=Classification(category="order", reasoning="mentions order status"),
    ):
        state = new_state("t1", "Where is my order ORD-5001?")
        result = classifier_node(state)
        assert result["category"] == "order"


def test_classifier_falls_back_to_other_on_bad_category():
    with patch(
        "app.graph.nodes.structured_completion",
        return_value=Classification(category="not-a-real-category", reasoning="n/a"),
    ):
        state = new_state("t1", "Some ambiguous ticket")
        result = classifier_node(state)
        assert result["category"] == "other"


def test_reviewer_approve_sets_resolved():
    with patch(
        "app.graph.nodes.structured_completion",
        return_value=ReviewVerdict(verdict="approve", reason="grounded and correct"),
    ):
        state = new_state("t1", "ticket")
        state["draft"] = "Your order has shipped."
        state["conversation"] = [
            {"iteration": 0, "draft": "Your order has shipped.", "feedback": None}
        ]
        result = reviewer_node(state)
        assert result["decision"] == "RESOLVED"


def test_reviewer_retry_increments_iterations_below_cap():
    with patch(
        "app.graph.nodes.structured_completion",
        return_value=ReviewVerdict(verdict="retry", reason="needs more detail"),
    ):
        state = new_state("t1", "ticket")
        state["draft"] = "draft"
        state["iterations"] = 0
        state["conversation"] = [{"iteration": 0, "draft": "draft", "feedback": None}]
        result = reviewer_node(state)
        assert "decision" not in result
        assert result["iterations"] == 1


def test_reviewer_escalates_at_max_iterations():
    """The loop must terminate — hitting the iteration cap forces ESCALATE
    even if the reviewer keeps saying 'retry'."""
    with patch(
        "app.graph.nodes.structured_completion",
        return_value=ReviewVerdict(verdict="retry", reason="still not good enough"),
    ):
        state = new_state("t1", "ticket")
        state["draft"] = "draft"
        state["iterations"] = settings.max_reviewer_iterations - 1
        state["conversation"] = [{"iteration": 0, "draft": "draft", "feedback": None}]
        result = reviewer_node(state)
        assert result["decision"] == "ESCALATE"
        assert "escalation_reason" in result


def test_reviewer_explicit_escalate_is_respected():
    with patch(
        "app.graph.nodes.structured_completion",
        return_value=ReviewVerdict(verdict="escalate", reason="out of policy scope"),
    ):
        state = new_state("t1", "ticket")
        state["draft"] = "draft"
        state["conversation"] = [{"iteration": 0, "draft": "draft", "feedback": None}]
        result = reviewer_node(state)
        assert result["decision"] == "ESCALATE"


def test_route_after_input_guardrail_refuse_short_circuits():
    from langgraph.graph import END

    state = new_state("t1", "ticket")
    state["decision"] = "REFUSE"
    assert route_after_input_guardrail(state) == END


def test_route_after_input_guardrail_proceeds_to_classifier():
    state = new_state("t1", "ticket")
    assert route_after_input_guardrail(state) == "classifier"


def test_route_after_reviewer_loops_back_when_no_decision():
    state = new_state("t1", "ticket")
    assert route_after_reviewer(state) == "responder"


def test_route_after_reviewer_ends_loop_on_resolved():
    state = new_state("t1", "ticket")
    state["decision"] = "RESOLVED"
    assert route_after_reviewer(state) == "output_guardrail"


def test_fallback_resolves_order_lookup_without_llm(mocker):
    mocked_tool = mocker.patch(
        "app.graph.nodes.call_tool",
        return_value={
            "tool_name": "get_order_status",
            "arguments": {"order_id": "ORD-5001"},
            "result": {
                "order_id": "ORD-5001",
                "status": "shipped",
                "eta": "2026-07-18",
                "tracking_number": "TRK-88213",
            },
            "status": "ok",
            "latency_ms": 1.0,
        },
    )

    result = fallback_node({"ticket_body": "Where is ORD-5001?", "order_id": "ORD-5001"})

    assert result["decision"] == "RESOLVED"
    assert "shipped" in result["draft"]
    mocked_tool.assert_called_once_with("get_order_status", {"order_id": "ORD-5001"})


def test_fallback_accepts_prd_product_id(mocker):
    mocked_tool = mocker.patch(
        "app.graph.nodes.call_tool",
        return_value={
            "tool_name": "get_product",
            "arguments": {"product_id": "P-1001"},
            "result": {
                "title": "Aurora Wireless Headphones",
                "price": 79.99,
                "in_stock": True,
                "description": "Noise-cancelling headphones.",
            },
            "status": "ok",
            "latency_ms": 1.0,
        },
    )

    result = fallback_node({"ticket_body": "Tell me about product PRD-1001"})

    assert result["decision"] == "RESOLVED"
    assert result["category"] == "product"
    mocked_tool.assert_called_once_with("get_product", {"product_id": "P-1001"})
