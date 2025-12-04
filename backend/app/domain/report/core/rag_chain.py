from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Optional

from app.domain.report.search.hybrid_search import HybridSearcher, QueryAnalyzer, SearchKeywords
from app.domain.report.search.retriever import UnifiedSearchResult
from app.infrastructure.vector_store_report import get_report_vector_store
from app.llm.client import LLMClient


class ReportRAGChain:
    """Lightweight RAG chain for daily reports."""

    def __init__(
        self,
        owner: str,
        retriever: Optional[HybridSearcher] = None,
        llm: Optional[LLMClient] = None,
        top_k: int = 5,
    ) -> None:
        self.owner = owner
        self.top_k = top_k

        vector_store = get_report_vector_store()
        collection = vector_store.get_collection()
        self.searcher = retriever or HybridSearcher(collection=collection)

        self.llm = llm or LLMClient(model="gpt-4o-mini", temperature=0.7, max_tokens=2000)

    def retrieve(
        self,
        query: str,
        date_range: Optional[Dict[str, date]] = None,
    ) -> List[UnifiedSearchResult]:
        keywords: SearchKeywords = QueryAnalyzer.extract_keywords(query)
        results = self.searcher.search(
            query=query,
            keywords=keywords,
            owner=self.owner,
            base_date_range=date_range,
            top_k=self.top_k,
        )
        return results

    def format_context(self, results: List[UnifiedSearchResult]) -> str:
        if not results:
            return "검색 결과가 없습니다."

        lines = []
        for idx, result in enumerate(results, 1):
            meta = result.metadata
            date_str = meta.get("date", "")
            chunk_type = meta.get("chunk_type", "")
            lines.append(
                f"[{idx}] 날짜: {date_str}, 유형: {chunk_type}\n내용: {result.text}"
            )
        return "\n---\n".join(lines)

    async def generate_response(
        self,
        query: str,
        date_range: Optional[Dict[str, date]] = None,
    ) -> Dict[str, Any]:
        results = self.retrieve(query, date_range)
        if not results:
            return {
                "answer": "검색된 청크가 없습니다.",
                "sources": [],
                "has_results": False,
            }

        context = self.format_context(results)
        system_prompt = (
            "주어진 일일 보고서 청크들만 활용하여 사용자 질문에 답변하세요. "
            "문맥에 없는 내용은 추측하지 말고, 필요한 경우 청크에 없다고 명시하세요."
        )
        user_prompt = f"질문: {query}\n\n청크:\n{context}"

        answer = await self.llm.acomplete(system_prompt=system_prompt, user_prompt=user_prompt, temperature=0.5)

        sources = []
        for result in results:
            meta = result.metadata
            sources.append(
                {
                    "date": meta.get("date", ""),
                    "chunk_type": meta.get("chunk_type", ""),
                    "text_preview": result.text[:120],
                    "score": round(result.score, 3),
                }
            )

        return {
            "answer": answer,
            "sources": sources,
            "has_results": True,
        }
