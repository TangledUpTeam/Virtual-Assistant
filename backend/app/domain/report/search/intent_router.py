from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

from app.domain.report.core.chunker import ALLOWED_CHUNK_TYPES


class QueryIntent(BaseModel):
    intent: Literal["daily", "mixed", "unknown"] = Field(..., description="Detected intent")
    reason: str = Field(..., description="Reasoning behind the routing decision")
    filters: dict = Field(default_factory=dict, description="Optional filters for retrieval")


class IntentRouter:
    """
    Lightweight intent router.
    We now store only daily report chunks, so the default intent is always "daily".
    """

    def __init__(self, *_: Optional[str], **__: Optional[str]) -> None:
        # Compatibility placeholder for previous API (api_key/model args)
        pass

    def _detect_chunk_types(self, query: str) -> list[str]:
        lower = query.lower()
        chunk_types = []
        if any(word in lower for word in ["계획", "plan", "익일"]):
            chunk_types.append("plan")
        if any(word in lower for word in ["미종결", "pending", "issue", "이슈"]):
            chunk_types.append("pending")
        if any(word in lower for word in ["todo", "할 일", "진행 업무"]):
            chunk_types.append("todo")
        if any(word in lower for word in ["요약", "summary"]):
            chunk_types.append("summary")
        if not chunk_types:
            chunk_types = list(ALLOWED_CHUNK_TYPES)
        return chunk_types

    def route(self, query: str) -> QueryIntent:
        filters = {"chunk_types": self._detect_chunk_types(query)}
        return QueryIntent(
            intent="daily",
            reason="Default route to daily reports with constrained chunk_types filter.",
            filters=filters,
        )
