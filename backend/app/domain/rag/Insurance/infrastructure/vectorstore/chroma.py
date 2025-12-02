"""
ChromaDB implementation of vector store
"""
import os
from typing import List, Dict, Any, Optional, Tuple
import chromadb
from chromadb.config import Settings

from .base import BaseVectorStore
from ...core.models import InsuranceDocument
from ...core.exceptions import VectorStoreException
from ...core.config import config


class ChromaVectorStore(BaseVectorStore):
    """ChromaDB 구현체"""
    
    def __init__(
        self,
        collection_name: Optional[str] = None,
        persist_directory: Optional[str] = None,
        embedding_function=None
    ):
        """
        ChromaDB 초기화
        
        Args:
            collection_name: 컬렉션 이름
            persist_directory: 저장 디렉토리
            embedding_function: 임베딩 함수 (ChromaDB 호환)
        """
        self.collection_name = collection_name or config.collection_name
        self.persist_directory = persist_directory or config.vector_store_path
        self.embedding_function = embedding_function
        
        # ChromaDB 클라이언트 초기화
        try:
            abs_path = os.path.abspath(self.persist_directory)
            self.client = chromadb.PersistentClient(path=abs_path)
            
            # 컬렉션 로드 또는 생성
            if self.embedding_function:
                self.collection = self.client.get_or_create_collection(
                    name=self.collection_name,
                    embedding_function=self.embedding_function
                )
            else:
                self.collection = self.client.get_or_create_collection(
                    name=self.collection_name
                )
                
        except Exception as e:
            raise VectorStoreException(
                f"Failed to initialize ChromaDB: {str(e)}",
                details={"persist_directory": abs_path, "collection": self.collection_name}
            )
    
    def add_documents(
        self,
        documents: List[InsuranceDocument],
        embeddings: Optional[List[List[float]]] = None
    ) -> List[str]:
        """문서 추가"""
        try:
            ids = [doc.id for doc in documents]
            contents = [doc.content for doc in documents]
            metadatas = [doc.metadata for doc in documents]
            
            if embeddings:
                self.collection.add(
                    ids=ids,
                    documents=contents,
                    metadatas=metadatas,
                    embeddings=embeddings
                )
            else:
                self.collection.add(
                    ids=ids,
                    documents=contents,
                    metadatas=metadatas
                )
            
            return ids
            
        except Exception as e:
            raise VectorStoreException(
                f"Failed to add documents: {str(e)}",
                details={"num_documents": len(documents)}
            )
    
    def search(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> Tuple[List[InsuranceDocument], List[float]]:
        """임베딩으로 검색"""
        try:
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                where=filter_metadata
            )
            
            documents = []
            scores = []
            
            if results and results['documents'] and len(results['documents']) > 0:
                for i in range(len(results['documents'][0])):
                    doc = InsuranceDocument(
                        id=results['ids'][0][i],
                        content=results['documents'][0][i],
                        metadata=results['metadatas'][0][i] if results['metadatas'] else {}
                    )
                    documents.append(doc)
                    
                    # ChromaDB는 distance를 반환 (작을수록 유사)
                    # similarity로 변환: 1 / (1 + distance)
                    distance = results['distances'][0][i] if results['distances'] else 0
                    similarity = 1 / (1 + distance)
                    scores.append(similarity)
            
            return documents, scores
            
        except Exception as e:
            raise VectorStoreException(
                f"Failed to search documents: {str(e)}",
                details={"top_k": top_k}
            )
    
    def search_by_text(
        self,
        query_text: str,
        top_k: int = 5,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> Tuple[List[InsuranceDocument], List[float]]:
        """텍스트로 검색 (임베딩 함수가 설정되어 있어야 함)"""
        try:
            results = self.collection.query(
                query_texts=[query_text],
                n_results=top_k,
                where=filter_metadata
            )
            
            documents = []
            scores = []
            
            if results and results['documents'] and len(results['documents']) > 0:
                for i in range(len(results['documents'][0])):
                    doc = InsuranceDocument(
                        id=results['ids'][0][i],
                        content=results['documents'][0][i],
                        metadata=results['metadatas'][0][i] if results['metadatas'] else {}
                    )
                    documents.append(doc)
                    
                    distance = results['distances'][0][i] if results['distances'] else 0
                    similarity = 1 / (1 + distance)
                    scores.append(similarity)
            
            return documents, scores
            
        except Exception as e:
            raise VectorStoreException(
                f"Failed to search by text: {str(e)}",
                details={"query": query_text, "top_k": top_k}
            )
    
    def delete_documents(self, document_ids: List[str]) -> bool:
        """문서 삭제"""
        try:
            self.collection.delete(ids=document_ids)
            return True
        except Exception as e:
            raise VectorStoreException(
                f"Failed to delete documents: {str(e)}",
                details={"document_ids": document_ids}
            )
    
    def get_document_count(self) -> int:
        """문서 개수 반환"""
        try:
            return self.collection.count()
        except Exception as e:
            raise VectorStoreException(f"Failed to get document count: {str(e)}")
    
    def clear(self) -> bool:
        """모든 문서 삭제"""
        try:
            self.client.delete_collection(name=self.collection_name)
            self.collection = self.client.create_collection(
                name=self.collection_name,
                embedding_function=self.embedding_function
            )
            return True
        except Exception as e:
            raise VectorStoreException(f"Failed to clear collection: {str(e)}")
    
    def get_collection_info(self) -> Dict[str, Any]:
        """컬렉션 정보 반환"""
        try:
            return {
                "name": self.collection_name,
                "count": self.get_document_count(),
                "persist_directory": self.persist_directory
            }
        except Exception as e:
            raise VectorStoreException(f"Failed to get collection info: {str(e)}")
