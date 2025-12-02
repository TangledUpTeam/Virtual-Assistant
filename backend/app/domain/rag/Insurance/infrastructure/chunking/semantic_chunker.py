"""
Semantic chunker using LangChain
"""
import uuid
from typing import List, Dict, Any, Optional

from langchain.text_splitter import RecursiveCharacterTextSplitter

from .base import BaseChunker, ChunkingStrategy
from ...core.models import InsuranceDocument, Chunk
from ...core.config import config


class SemanticChunker(BaseChunker):
    """
    LangChain RecursiveCharacterTextSplitter 기반 청킹
    
    의미 단위 보존을 위한 재귀적 분할
    """
    
    def __init__(
        self,
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None,
        separators: Optional[List[str]] = None
    ):
        """
        의미 기반 청커 초기화
        
        Args:
            chunk_size: 청크 크기 (문자 수)
            chunk_overlap: 오버랩 크기
            separators: 구분자 리스트
        """
        self.chunk_size = chunk_size or config.chunk_size
        self.chunk_overlap = chunk_overlap or config.chunk_overlap
        self.separators = separators or config.chunk_separators
        
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            separators=self.separators,
            length_function=len
        )
    
    def get_strategy(self) -> ChunkingStrategy:
        """청킹 전략 반환"""
        return ChunkingStrategy.SEMANTIC
    
    def chunk(
        self,
        text: str,
        metadata: Dict[str, Any] = None
    ) -> List[Chunk]:
        """
        텍스트를 의미 단위로 청크 분할
        
        Args:
            text: 원본 텍스트
            metadata: 메타데이터
            
        Returns:
            청크 리스트
        """
        if not text or not text.strip():
            return []
        
        # LangChain splitter로 분할
        chunks_text = self.text_splitter.split_text(text)
        
        # Chunk 객체로 변환
        chunks = []
        for idx, chunk_text in enumerate(chunks_text):
            chunk_text = chunk_text.strip()
            if not chunk_text:
                continue
            
            chunk_metadata = metadata.copy() if metadata else {}
            chunk_metadata['chunk_index'] = idx
            chunk_metadata['total_chunks'] = len(chunks_text)
            chunk_metadata['chunk_strategy'] = self.get_strategy().value
            
            chunk = Chunk(
                id=str(uuid.uuid4()),
                content=chunk_text,
                metadata=chunk_metadata,
                tokens=None  # 토큰 수는 계산하지 않음
            )
            chunks.append(chunk)
        
        return chunks
    
    def chunk_documents(
        self,
        documents: List[InsuranceDocument]
    ) -> List[InsuranceDocument]:
        """
        문서 리스트를 청크로 분할
        
        Args:
            documents: 원본 문서 리스트
            
        Returns:
            청크된 문서 리스트
        """
        chunked_docs = []
        
        for doc in documents:
            chunks = self.chunk(doc.content, doc.metadata)
            
            for chunk in chunks:
                chunked_doc = InsuranceDocument(
                    id=chunk.id,
                    content=chunk.content,
                    metadata=chunk.metadata
                )
                chunked_docs.append(chunked_doc)
        
        return chunked_docs
    
    def estimate_chunks(self, text: str) -> int:
        """예상 청크 개수 추정"""
        if not text or not text.strip():
            return 0
        
        text_length = len(text)
        step = self.chunk_size - self.chunk_overlap
        if step <= 0:
            step = self.chunk_size
        
        return max(1, (text_length + step - 1) // step)
