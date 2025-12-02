"""
Base chunker interface
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any
from enum import Enum

from ...core.models import InsuranceDocument, Chunk


class ChunkingStrategy(str, Enum):
    """청킹 전략"""
    TOKEN_BASED = "token"  # tiktoken 기반
    SEMANTIC = "semantic"  # 의미 기반 (LangChain)
    FIXED_SIZE = "fixed"  # 고정 크기
    RECURSIVE = "recursive"  # 재귀적 분할


class BaseChunker(ABC):
    """청킹 추상 인터페이스"""
    
    @abstractmethod
    def chunk(
        self,
        text: str,
        metadata: Dict[str, Any] = None
    ) -> List[Chunk]:
        """
        텍스트를 청크로 분할
        
        Args:
            text: 원본 텍스트
            metadata: 메타데이터 (선택)
            
        Returns:
            청크 리스트
        """
        pass
    
    @abstractmethod
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
        pass
    
    @abstractmethod
    def get_strategy(self) -> ChunkingStrategy:
        """
        청킹 전략 반환
        
        Returns:
            청킹 전략
        """
        pass
    
    def estimate_chunks(self, text: str) -> int:
        """
        예상 청크 개수 추정 (옵션)
        
        Args:
            text: 원본 텍스트
            
        Returns:
            예상 청크 개수
        """
        return 1
