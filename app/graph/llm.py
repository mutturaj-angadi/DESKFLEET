"""
app.graph.llm
==============
Thin wrapper around the OpenAI SDK so every node calls through one
place. This is also the seam tests patch: `app.graph.llm.get_client`
and the two completion functions are monkeypatched in unit tests so
agent logic can be exercised without hitting a real API or requiring
an API key.

Provider-agnostic by design: the OpenAI SDK works against any
OpenAI-compatible endpoint by swapping `base_url`. By default this
points at Gemini's OpenAI-compatible endpoint using LLM_API_KEY /
LLM_BASE_URL from app.config.
"""

from __future__ import annotations

import json
from functools import lru_cache
from typing import Any, TypeVar

from openai import OpenAI
from pydantic import BaseModel

from app.config import settings

T = TypeVar("T", bound=BaseModel)


@lru_cache(maxsize=1)
def get_client() -> OpenAI:
    if not settings.llm_api_key:
        raise RuntimeError(
            "LLM_API_KEY is not configured. Set it in .env and restart the API server."
        )
    kwargs: dict[str, Any] = {"api_key": settings.llm_api_key}
    if settings.llm_base_url:
        kwargs["base_url"] = settings.llm_base_url
    return OpenAI(**kwargs)


def _json_schema_instruction(response_model: type[BaseModel]) -> str:
    schema = response_model.model_json_schema()
    return (
        "Respond with ONLY a single JSON object matching this JSON schema — "
        "no markdown fences, no commentary before or after it:\n"
        f"{json.dumps(schema)}"
    )


def structured_completion(
    *, system_prompt: str, user_prompt: str, response_model: type[T]
) -> T:
    """Call the chat completions API and parse the response into a
    Pydantic model instance.

    Tries OpenAI's native `.beta.chat.completions.parse()` structured-output
    helper first (works for real OpenAI models). Not every OpenAI-compatible
    provider implements that beta surface identically, so on any failure this
    falls back to plain JSON-mode: ask for JSON matching the schema in the
    prompt, then validate the raw text with Pydantic.
    """
    client = get_client()
    try:
        completion = client.beta.chat.completions.parse(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format=response_model,
        )
        parsed = completion.choices[0].message.parsed
        if parsed is not None:
            return parsed
    except Exception:
        pass  # fall through to the JSON-mode path below

    completion = client.chat.completions.create(
        model=settings.openai_model,
        messages=[
            {
                "role": "system",
                "content": f"{system_prompt}\n\n{_json_schema_instruction(response_model)}",
            },
            {"role": "user", "content": user_prompt},
        ],
        response_format={"type": "json_object"},
    )
    content = completion.choices[0].message.content
    if not content:
        raise ValueError("Model returned an empty response")
    # Some providers still wrap JSON in ```json fences despite instructions.
    cleaned = (
        content.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    )
    return response_model.model_validate_json(cleaned)


def tool_calling_completion(
    *, system_prompt: str, user_prompt: str, tools: list[dict]
) -> dict[str, Any]:
    """Call the chat completions API with tool definitions and return
    a plain dict: {"content": str | None, "tool_calls": [{"name", "arguments"}]}.
    """
    client = get_client()
    completion = client.chat.completions.create(
        model=settings.openai_model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        tools=tools,
        tool_choice="auto",
    )
    message = completion.choices[0].message
    tool_calls = []
    for call in message.tool_calls or []:
        try:
            args = json.loads(call.function.arguments)
        except json.JSONDecodeError:
            args = {}
        tool_calls.append({"name": call.function.name, "arguments": args})
    return {"content": message.content, "tool_calls": tool_calls}
