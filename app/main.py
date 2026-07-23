"""
app.main
=========
FastAPI application entrypoint.

    uvicorn app.main:app --reload --port 8000
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Response

from app.config import settings
from app.database.db import init_db
from app.metrics.prometheus import metrics_response

# LangSmith reads these from the environment at import time of langchain/langgraph,
# so set them before importing the router (which imports the graph).
if settings.langchain_tracing_v2:
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_API_KEY"] = settings.langchain_api_key
    os.environ["LANGCHAIN_PROJECT"] = settings.langchain_project

from app.routers.tickets import router as tickets_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="DeskFleet",
    description="AI Multi-Agent Customer Support System",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(tickets_router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/metrics")
def metrics() -> Response:
    body, content_type = metrics_response()
    return Response(content=body, media_type=content_type)
