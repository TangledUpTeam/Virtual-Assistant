"""
RAG Agent

문서 검색 및 질의응답 에이전트
기존 RAGRetriever를 활용합니다.
"""

from typing import Dict, Any, Optional
from .base_agent import BaseAgent


class RAGAgent(BaseAgent):
    """
    문서 검색 및 질의응답 에이전트
    
    기존 RAGRetriever를 래핑하여 HR/Insurance 문서를 검색하고 답변합니다.
    """
    
    def __init__(self):
        super().__init__(
            name="rag",
            description="회사 문서, 규정, 정책 등을 검색하여 답변하는 에이전트입니다. "
                       "HR 규정, 복지 정책, 연차/휴가 규정 등의 질문에 답변합니다."
        )
        # Lazy loading: 실제 사용 시에만 RAGRetriever 로드
        self._rag_retriever = None
    
    @property
    def rag_retriever(self):
        """RAGRetriever lazy loading"""
        if self._rag_retriever is None:
            from app.domain.rag.HR.retriever import RAGRetriever
            # HR 컬렉션 사용
            self._rag_retriever = RAGRetriever(collection_name="hr_documents")
        return self._rag_retriever
    
    async def process(self, query: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        문서 검색 및 답변 생성
        
        Args:
            query: 사용자 질문
            context: 추가 컨텍스트 (top_k 등)
            
        Returns:
            str: RAG 기반 답변
        """
        try:
            from app.domain.rag.HR.schemas import QueryRequest
            
            # 컨텍스트에서 top_k 추출 (기본값: 5)
            top_k = 5
            if context and "top_k" in context:
                top_k = context["top_k"]
            
            # QueryRequest 생성
            request = QueryRequest(
                query=query,
                top_k=top_k
            )
            
            # RAG 검색 및 답변 생성
            response = self.rag_retriever.query(request)
            
            # 답변 반환
            return response.answer
            
        except Exception as e:
            return f"문서 검색 중 오류가 발생했습니다: {str(e)}"
    
    def get_capabilities(self) -> list:
        """에이전트 기능 목록"""
        return [
            "회사 문서 검색",
            "HR 규정 조회",
            "복지 정책 안내",
            "연차/휴가 규정 설명",
            "사내 정책 문의",
        ]

