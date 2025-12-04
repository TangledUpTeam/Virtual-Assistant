from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any, Dict, List, Optional

from chromadb import Collection

from ingestion.embed import get_embedding_service

from app.domain.report.core.chunker import (
    ALLOWED_CHUNK_TYPES,
    ChunkValidationError,
    validate_metadata,
)
from app.domain.report.search.retriever import UnifiedSearchResult


@dataclass
class SearchKeywords:
    chunk_types: List[str]
    single_date: Optional[str] = None
    date_range: Optional[Dict[str, date]] = None


class QueryAnalyzer:
    """Lightweight keyword analyzer to guide filters."""

    @staticmethod
    def extract_keywords(query: str, base_date: Optional[date] = None) -> SearchKeywords:
        lower = query.lower()
        chunk_types: List[str] = []

        if any(word in lower for word in ["계획", "plan", "익일"]):
            chunk_types.append("plan")
        if any(word in lower for word in ["미종결", "pending", "이슈", "issue"]):
            chunk_types.append("pending")
        if any(word in lower for word in ["요약", "summary"]):
            chunk_types.append("summary")
        if any(word in lower for word in ["todo", "할 일", "진행 업무"]):
            chunk_types.append("todo")
        if not chunk_types:
            chunk_types = ["detail", "todo", "pending", "plan", "summary"]

        return SearchKeywords(chunk_types=chunk_types)


class HybridSearcher:
    """Simple hybrid search that applies metadata filters then vector search."""

    def __init__(self, collection: Collection, embedding_model_type: Optional[str] = None) -> None:
        self.collection = collection
        self.embedding_service = get_embedding_service(model_type=embedding_model_type)

    def _build_date_list(self, start: date, end: date) -> List[str]:
        dates = []
        current = start
        while current <= end:
            dates.append(current.strftime("%Y-%m-%d"))
            current += timedelta(days=1)
        return dates

    def _build_where(
        self,
        keywords: SearchKeywords,
        owner: Optional[str],
        base_date_range: Optional[Dict[str, date]],
    ) -> Dict[str, Any]:
        conditions: List[Dict[str, Any]] = [{"report_type": "daily"}]

        if keywords.chunk_types:
            valid = [ctype for ctype in keywords.chunk_types if ctype in ALLOWED_CHUNK_TYPES]
            if valid:
                conditions.append({"chunk_type": {"$in": valid}})

        if owner:
            conditions.append({"owner": owner})

        if keywords.single_date:
            conditions.append({"date": keywords.single_date})
        elif keywords.date_range or base_date_range:
            date_range = keywords.date_range or base_date_range
            if date_range:
                dates = self._build_date_list(date_range["start"], date_range["end"])
                conditions.append({"date": {"$in": dates}})

        return {"$and": conditions} if len(conditions) > 1 else conditions[0]

    def search(
        self,
        query: str,
        keywords: SearchKeywords,
        owner: Optional[str] = None,
        base_date_range: Optional[Dict[str, date]] = None,
        top_k: int = 5,
    ) -> List[UnifiedSearchResult]:
        where_filter = self._build_where(keywords, owner, base_date_range)
        query_embedding = self.embedding_service.embed_text(query)

        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where_filter if where_filter else None,
        )

        search_results: List[UnifiedSearchResult] = []
        if not results or not results.get("ids"):
            return search_results

        ids = results["ids"][0]
        documents = results["documents"][0]
        metadatas = results["metadatas"][0]
        distances = results["distances"][0]

        for i in range(len(ids)):
            metadata = metadatas[i] or {}
            try:
                metadata = validate_metadata(metadata)
            except ChunkValidationError:
                continue

            if metadata.get("chunk_type") not in ALLOWED_CHUNK_TYPES:
                continue
            if metadata.get("report_type") != "daily":
                continue

            score = 1.0 / (1.0 + distances[i])
            search_results.append(
                UnifiedSearchResult(
                    chunk_id=ids[i],
                    doc_id=metadata.get("doc_id", ""),
                    doc_type=metadata.get("report_type", "daily"),
                    chunk_type=metadata.get("chunk_type", ""),
                    text=documents[i],
                    score=score,
                    metadata=metadata,
                )
            )

        # Return best matches first
        search_results.sort(key=lambda r: -r.score)
        return search_results[:top_k]
