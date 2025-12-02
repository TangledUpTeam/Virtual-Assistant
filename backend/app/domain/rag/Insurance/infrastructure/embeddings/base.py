"""
Base interface for embedding providers
"""
from abc import ABC, abstractmethod
from typing import List, Union


class BaseEmbeddingProvider(ABC):
    """임베딩 제공자 추상 인터페이스"""
    
    @abstractmethod
    def embed_text(self, text: str) -> List[float]:
        """
        단일 텍스트를 임베딩 벡터로 변환
        
        Args:
            text: 임베딩할 텍스트
            
        Returns:
            임베딩 벡터
        """
        pass
    
    @abstractmethod
    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """
        여러 텍스트를 배치로 임베딩
        
        Args:
            texts: 임베딩할 텍스트 리스트
            
        Returns:
            임베딩 벡터 리스트
        """
        pass
    
    @abstractmethod
    def get_embedding_dimension(self) -> int:
        """
        임베딩 차원 수 반환
        
        Returns:
            임베딩 차원
        """
        pass
    
    @abstractmethod
    def get_model_name(self) -> str:
        """
        사용 중인 모델 이름 반환
        
        Returns:
            모델 이름
        """
        pass
