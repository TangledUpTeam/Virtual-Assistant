"""
Core data models for Insurance RAG system
"""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class DocumentType(str, Enum):
    """문서 타입"""
    POLICY = "policy"
    CLAIM = "claim"
    REGULATION = "regulation"
    FAQ = "faq"
    OTHER = "other"


class InsuranceDocument(BaseModel):
    """보험 문서 모델"""
    id: str = Field(..., description="문서 고유 ID")
    content: str = Field(..., description="문서 내용")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="메타데이터")
    doc_type: DocumentType = Field(default=DocumentType.OTHER, description="문서 타입")
    source: Optional[str] = Field(None, description="출처")
    page: Optional[int] = Field(None, description="페이지 번호")
    chunk_index: Optional[int] = Field(None, description="청크 인덱스")
    created_at: datetime = Field(default_factory=datetime.now, description="생성 시각")
    
    class Config:
        use_enum_values = True


class Query(BaseModel):
    """사용자 쿼리 모델"""
    question: str = Field(..., description="사용자 질문")
    query_id: Optional[str] = Field(None, description="쿼리 고유 ID")
    user_id: Optional[str] = Field(None, description="사용자 ID")
    context: Optional[Dict[str, Any]] = Field(default_factory=dict, description="추가 컨텍스트")
    timestamp: datetime = Field(default_factory=datetime.now, description="쿼리 시각")


class RetrievalResult(BaseModel):
    """검색 결과 모델"""
    documents: List[InsuranceDocument] = Field(default_factory=list, description="검색된 문서들")
    scores: List[float] = Field(default_factory=list, description="유사도 점수")
    query: Query = Field(..., description="원본 쿼리")
    retrieval_time_ms: float = Field(..., description="검색 소요 시간 (ms)")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="검색 메타데이터")


class GenerationResult(BaseModel):
    """생성 결과 모델"""
    answer: str = Field(..., description="생성된 답변")
    query: Query = Field(..., description="원본 쿼리")
    source_documents: List[InsuranceDocument] = Field(default_factory=list, description="참고 문서")
    confidence_score: Optional[float] = Field(None, description="신뢰도 점수")
    generation_time_ms: float = Field(..., description="생성 소요 시간 (ms)")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="생성 메타데이터")


class Chunk(BaseModel):
    """문서 청크 모델"""
    content: str = Field(..., description="청크 내용")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="청크 메타데이터")
    chunk_id: Optional[str] = Field(None, description="청크 고유 ID")
    parent_id: Optional[str] = Field(None, description="부모 문서 ID")
    embedding: Optional[List[float]] = Field(None, description="임베딩 벡터")


class EvaluationMetrics(BaseModel):
    """평가 지표 모델"""
    retrieval_hit_rate: float = Field(..., description="검색 적중률")
    semantic_similarity: float = Field(..., description="의미 유사도")
    judge_score: float = Field(..., description="LLM 판단 점수")
    keyword_hit_rate: float = Field(..., description="키워드 적중률")
    latency_ms: float = Field(..., description="응답 지연 시간")
    total_queries: int = Field(..., description="총 쿼리 수")
