"""
Unified Vector Store 클라이언트

Chroma Cloud에서 unified_documents 컬렉션을 관리합니다.

Author: AI Assistant
Created: 2025-11-18
"""
import chromadb
from chromadb import Collection
from typing import Optional


# Chroma Cloud 설정 (고정값)
CHROMA_API_KEY = "ck-BcnEUpVpQa3x18paPEMqLSobcLHFSaga1kekufxB24tn"
CHROMA_TENANT = "87acc175-c5c2-44df-97ff-c0b914e35994"
CHROMA_DATABASE = "Virtual_Assistant"

# 통합 컬렉션 이름
UNIFIED_COLLECTION_NAME = "unified_documents"


class UnifiedVectorStore:
    """Unified Documents Vector Store 클라이언트"""
    
    def __init__(self):
        """Chroma Cloud 클라이언트 초기화"""
        self.client = chromadb.CloudClient(
            api_key=CHROMA_API_KEY,
            tenant=CHROMA_TENANT,
            database=CHROMA_DATABASE
        )
        self._collection: Optional[Collection] = None
    
    def get_unified_collection(self) -> Collection:
        """
        unified_documents 컬렉션 반환
        
        Returns:
            unified_documents Collection 객체
        """
        if self._collection is None:
            try:
                self._collection = self.client.get_or_create_collection(
                    name=UNIFIED_COLLECTION_NAME
                )
            except KeyError:
                # _type 오류 발생 시 재시도
                self._collection = self.client.get_or_create_collection(
                    name=UNIFIED_COLLECTION_NAME
                )
        
        return self._collection
    
    def get_collection_info(self) -> dict:
        """
        컬렉션 정보 조회
        
        Returns:
            컬렉션 정보 딕셔너리
        """
        collection = self.get_unified_collection()
        return {
            "name": collection.name,
            "count": collection.count(),
            "metadata": collection.metadata
        }
    
    def reset_collection(self):
        """컬렉션 초기화 (재연결)"""
        self._collection = None


# ========================================
# 싱글톤 인스턴스
# ========================================

_vector_store: Optional[UnifiedVectorStore] = None


def get_vector_store() -> UnifiedVectorStore:
    """
    UnifiedVectorStore 싱글톤 인스턴스 반환
    
    Returns:
        UnifiedVectorStore 인스턴스
    """
    global _vector_store
    if _vector_store is None:
        _vector_store = UnifiedVectorStore()
    return _vector_store


def get_unified_collection() -> Collection:
    """
    unified_documents 컬렉션 가져오기 (헬퍼 함수)
    
    Returns:
        Collection 객체
    """
    store = get_vector_store()
    return store.get_unified_collection()

