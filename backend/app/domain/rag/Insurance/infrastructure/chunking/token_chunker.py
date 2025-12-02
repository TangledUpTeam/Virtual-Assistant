"""
Token-based chunker using tiktoken
"""
import uuid
from typing import List, Dict, Any, Optional

import tiktoken

from .base import BaseChunker, ChunkingStrategy
from ...core.models import InsuranceDocument, Chunk
from ...core.config import config
from ...core.exceptions import DocumentProcessingException

# Import from services layer
from ...services.document_processor import TextChunker


class TokenChunker(BaseChunker):
    """
    tiktoken 기반 청킹
    
    서비스 레이어의 TextChunker를 BaseChunker 인터페이스로 래핑
    """
    
    def __init__(
        self,
        max_tokens: Optional[int] = None,
        overlap_tokens: Optional[int] = None,
        encoding_name: str = "cl100k_base"
    ):
        """
        토큰 청커 초기화
        
        Args:
            max_tokens: 최대 토큰 수 (기본값: config에서 가져옴)
            overlap_tokens: 오버랩 토큰 수 (기본값: config에서 가져옴)
            encoding_name: tiktoken 인코딩 이름
        """
        self.max_tokens = max_tokens or getattr(config, 'chunk_max_tokens', 500)
        self.overlap_tokens = overlap_tokens or getattr(config, 'chunk_overlap_tokens', 80)
        self.encoding_name = encoding_name
        
        try:
            self._chunker = TextChunker(
                max_tokens=self.max_tokens,
                overlap_tokens=self.overlap_tokens,
                encoding=encoding_name
            )
            self.encoder = self._chunker.encoder
        except Exception as e:
            raise DocumentProcessingException(
                f"tiktoken 인코더 초기화 실패: {str(e)}",
                details={"encoding_name": encoding_name}
            )
    
    def get_strategy(self) -> ChunkingStrategy:
        """청킹 전략 반환"""
        return ChunkingStrategy.TOKEN_BASED
    
    def chunk(
        self,
        text: str,
        metadata: Dict[str, Any] = None
    ) -> List[Chunk]:
        """
        텍스트를 토큰 기반으로 청크 분할
        
        Args:
            text: 원본 텍스트
            metadata: 메타데이터
            
        Returns:
            청크 리스트
        """
        if not text or not text.strip():
            return []
        
        # OCR 실패 메시지 필터링
        if self._chunker.is_ocr_failure_message(text):
            return []
        
        # 청크 분할
        chunks_text = self._chunker.chunk(text, filter_invalid=True)
        
        # Chunk 객체로 변환
        chunks = []
        for idx, chunk_text in enumerate(chunks_text):
            chunk_metadata = metadata.copy() if metadata else {}
            chunk_metadata['chunk_index'] = idx
            chunk_metadata['total_chunks'] = len(chunks_text)
            chunk_metadata['chunk_strategy'] = self.get_strategy().value
            
            chunk = Chunk(
                id=str(uuid.uuid4()),
                content=chunk_text,
                metadata=chunk_metadata,
                tokens=len(self.encoder.encode(chunk_text))
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
        
        try:
            tokens = self.encoder.encode(text)
            step = self.max_tokens - self.overlap_tokens
            if step <= 0:
                step = 1
            return max(1, (len(tokens) + step - 1) // step)
        except Exception:
            return 1
