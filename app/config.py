"""
app.config
==========
Single source of truth for environment-driven settings. Every other
module imports `settings` from here rather than calling `os.getenv`
directly, so the whole app has one place to look when tuning behaviour.
"""

from __future__ import annotations

import os

from dotenv import load_dotenv
from pydantic import BaseModel

# Load local development settings before Settings reads the environment.  Docker
# Compose and hosted deployments already provide environment variables; with
# override=False those values continue to take precedence over .env.
load_dotenv(override=False)


class Settings(BaseModel):
    # --- LLM ---
    # DeskFleet's code calls the OpenAI SDK, but any OpenAI-compatible endpoint
    # works by pointing llm_base_url elsewhere — Gemini publishes one at
    # generativelanguage.googleapis.com/v1beta/openai/. Swap LLM_PROVIDER back
    # to "openai" (and clear LLM_BASE_URL) to use real OpenAI instead.
    llm_provider: str = os.getenv("LLM_PROVIDER", "gemini")
    # LLM_API_KEY / OPENAI_MODEL are the documented names.  Keep the Gemini
    # aliases as a convenience for existing local setups.
    llm_api_key: str = os.getenv("GEMINI_API_KEY") or os.getenv(
        "LLM_API_KEY", os.getenv("OPENAI_API_KEY", "")
    )
    llm_base_url: str = os.getenv(
        "LLM_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai/"
    )
    openai_model: str = os.getenv("GEMINI_MODEL") or os.getenv(
        "OPENAI_MODEL", "gemini-2.0-flash"
    )

    # --- LangSmith tracing ---
    langchain_tracing_v2: bool = os.getenv("LANGCHAIN_TRACING_V2", "false").lower() == "true"
    langchain_api_key: str = os.getenv("LANGCHAIN_API_KEY", "")
    langchain_project: str = os.getenv("LANGCHAIN_PROJECT", "deskfleet")

    # --- Mock order/product API ---
    mock_api_base_url: str = os.getenv("MOCK_API_BASE_URL", "http://localhost:9000")

    # --- Agent loop control ---
    max_reviewer_iterations: int = int(os.getenv("MAX_REVIEWER_ITERATIONS", "3"))

    # --- Guardrails ---
    injection_block_threshold: float = float(os.getenv("INJECTION_BLOCK_THRESHOLD", "0.5"))

    # --- Storage ---
    database_path: str = os.getenv("DATABASE_PATH", "deskfleet.db")

    # --- Server ---
    api_port: int = int(os.getenv("API_PORT", "8000"))


settings = Settings()
