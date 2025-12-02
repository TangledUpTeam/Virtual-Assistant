"""
Base interface for vector store implementations
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Tuple
from ...core.models import InsuranceDocument, Chunk


class BaseVectorStore(ABC):
    """Vector Store 추상 인터페이스"""
    
    @abstractmethod
    def add_documents(
        self, 
        documents: List[InsuranceDocument],
        embeddings: Optional[List[List[float]]] = None
    ) -> List[str]:
        """
        문서를 벡터 스토어에 추가
        
        Args:
            documents: 추가할 문서 리스트
            embeddings: 사전 계산된 임베딩 (선택사항)
            
        Returns:
            추가된 문서의 ID 리스트
        """
        pass
    
    @abstractmethod
    def search(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> Tuple[List[InsuranceDocument], List[float]]:
        """
        임베딩 벡터로 유사 문서 검색
        
        Args:
            query_embedding: 쿼리 임베딩 벡터
            top_k: 반환할 문서 개수
            filter_metadata: 메타데이터 필터
            
        Returns:
            (문서 리스트, 유사도 점수 리스트)
        """
        pass
    
    @abstractmethod
    def search_by_text(
        self,
        query_text: str,
        top_k: int = 5,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> Tuple[List[InsuranceDocument], List[float]]:
        """
        텍스트로 유사 문서 검색 (임베딩은 내부에서 처리)
        
        Args:
            query_text: 쿼리 텍스트
            top_k: 반환할 문서 개수
            filter_metadata: 메타데이터 필터
            
        Returns:
            (문서 리스트, 유사도 점수 리스트)
        """
        pass
    
    @abstractmethod
    def delete_documents(self, document_ids: List[str]) -> bool:
        """
        문서 삭제
        
        Args:
            document_ids: 삭제할 문서 ID 리스트
            
        Returns:
            성공 여부
        """
        pass
    
    @abstractmethod
    def get_document_count(self) -> int:
        """
        저장된 문서 개수 반환
        
        Returns:
            문서 개수
        """
        pass
    
    @abstractmethod
    def clear(self) -> bool:
        """
        모든 문서 삭제
        
        Returns:
            성공 여부
        """
        pass
    
    @abstractmethod
    def get_collection_info(self) -> Dict[str, Any]:
        """
        컬렉션 정보 반환
        
        Returns:
            컬렉션 메타데이터
        """
        pass
