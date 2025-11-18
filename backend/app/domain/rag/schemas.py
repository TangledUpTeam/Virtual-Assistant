"""
RAG 시스템의 Pydantic 스키마 정의
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class ContentType(str, Enum):
    """컨텐츠 타입"""
    TEXT = "text"
    TABLE = "table"
    IMAGE = "image"
    CHART = "chart"


class DocumentMetadata(BaseModel):
    """문서 메타데이터"""
    filename: str
    page_number: int
    content_type: ContentType
    total_pages: Optional[int] = None
    processed_at: datetime = Field(default_factory=datetime.now)
    file_size: Optional[int] = None
    
    class Config:
        use_enum_values = True


class TableCell(BaseModel):
    """표 셀 정보"""
    row: int
    col: int
    text: str
    
    
class TableData(BaseModel):
    """표 데이터 구조"""
    headers: List[str]
    rows: List[List[str]]
    metadata: Optional[Dict[str, Any]] = None


class ProcessedContent(BaseModel):
    """처리된 컨텐츠"""
    content_type: ContentType
    text: str
    metadata: DocumentMetadata
    table_data: Optional[TableData] = None
    
    class Config:
        use_enum_values = True


class ProcessedDocument(BaseModel):
    """처리된 문서 전체"""
    filename: str
    total_pages: int
    contents: List[ProcessedContent]
    processed_at: datetime = Field(default_factory=datetime.now)
    file_path: Optional[str] = None


class ChunkMetadata(BaseModel):
    """청크 메타데이터"""
    chunk_id: str
    document_id: str
    filename: str
    page_number: int
    content_type: ContentType
    chunk_index: int
    total_chunks: Optional[int] = None
    
    class Config:
        use_enum_values = True


class DocumentChunk(BaseModel):
    """문서 청크"""
    text: str
    metadata: ChunkMetadata


class UploadResponse(BaseModel):
    """PDF 업로드 응답"""
    success: bool
    message: str
    filename: str
    total_pages: int
    total_chunks: int
    processed_file_path: Optional[str] = None


class QueryRequest(BaseModel):
    """질의응답 요청"""
    query: str
    top_k: Optional[int] = Field(default=3, ge=1, le=10)
    similarity_threshold: Optional[float] = Field(default=None, ge=0.0, le=1.0)  # 거리도 threshold
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

