"""
Insurance RAG 시스템의 Pydantic 스키마 정의
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


class QueryRequest(BaseModel):
    """질의응답 요청"""
    query: str
    top_k: Optional[int] = Field(default=3, ge=1, le=10)
    collection_name: Optional[str] = None


class RetrievedChunk(BaseModel):
    """검색된 청크"""
    text: str
    metadata: Dict[str, Any]
    score: float


class QueryResponse(BaseModel):
    """질의응답 응답"""
    query: str
    answer: str
    retrieved_chunks: List[RetrievedChunk]
    processing_time: float
    model_used: str



