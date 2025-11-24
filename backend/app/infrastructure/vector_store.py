"""
Unified Vector Store 클라이언트

로컬 ChromaDB에서 unified_documents 컬렉션을 관리합니다.

Author: AI Assistant
Created: 2025-11-18
Updated: 2025-11-19 (로컬 ChromaDB로 전환)
"""
import chromadb
from chromadb import Collection
from chromadb.config import Settings
from typing import Optional
from pathlib import Path

# 로컬 ChromaDB 경로
CHROMA_PERSIST_DIR = Path("backend/Data/chroma")

# 통합 컬렉션 이름
UNIFIED_COLLECTION_NAME = "unified_documents"


class UnifiedVectorStore:
    """Unified Documents Vector Store 클라이언트"""
    
    def __init__(self):
        """로컬 ChromaDB 클라이언트 초기화"""
        # 디렉토리 생성
        CHROMA_PERSIST_DIR.mkdir(parents=True, exist_ok=True)
        
        # 로컬 ChromaDB 클라이언트 초기화
        self.client = chromadb.PersistentClient(
            path=str(CHROMA_PERSIST_DIR),
            settings=Settings(anonymized_telemetry=False)
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

