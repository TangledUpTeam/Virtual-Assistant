"""
벡터 저장소 모듈

KoSentenceBERT를 사용한 임베딩 생성 및 ChromaDB 저장을 처리합니다.
"""

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Any, Optional
import uuid

from .config import rag_config
from .schemas import DocumentChunk, ProcessedDocument
from .utils import get_logger

logger = get_logger(__name__)


class VectorStore:
    """벡터 저장소 관리"""
    
    def __init__(self, collection_name: Optional[str] = None):
        self.config = rag_config
        self.collection_name = collection_name or self.config.CHROMA_COLLECTION_NAME
        
        # KoSentenceBERT 모델 로드
        logger.info(f"임베딩 모델 로드 중: {self.config.KOREAN_EMBEDDING_MODEL}")
        self.embedding_model = SentenceTransformer(self.config.KOREAN_EMBEDDING_MODEL)
        
        # ChromaDB 클라이언트 초기화
        self.client = chromadb.PersistentClient(
            path=self.config.CHROMA_PERSIST_DIRECTORY,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        # 컬렉션 가져오기 또는 생성
        self.collection = self._get_or_create_collection()
        
        logger.info(f"벡터 저장소 초기화 완료: {self.collection_name}")
    
    def _get_or_create_collection(self):
        """컬렉션 가져오기 또는 생성"""
        try:
            collection = self.client.get_collection(name=self.collection_name)
            logger.info(f"기존 컬렉션 로드: {self.collection_name}")
        except:
            collection = self.client.create_collection(
                name=self.collection_name,
                metadata={"description": "RAG 문서 임베딩"}
            )
            logger.info(f"새 컬렉션 생성: {self.collection_name}")
        
        return collection
    
    def embed_text(self, text: str) -> List[float]:
        """
        텍스트를 벡터로 임베딩
        
        Args:
            text: 임베딩할 텍스트
            
        Returns:
            List[float]: 임베딩 벡터
        """
        embedding = self.embedding_model.encode(text, convert_to_numpy=True)
        return embedding.tolist()
    
    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """
        여러 텍스트를 벡터로 임베딩
        
        Args:
            texts: 임베딩할 텍스트 리스트
            
        Returns:
            List[List[float]]: 임베딩 벡터 리스트
        """
        embeddings = self.embedding_model.encode(
            texts, 
            convert_to_numpy=True,
            show_progress_bar=True
        )
        return embeddings.tolist()
    
    def add_chunks(self, chunks: List[DocumentChunk]) -> int:
        """
        청크를 벡터 저장소에 추가
        
        Args:
            chunks: 추가할 청크 리스트
            
        Returns:
            int: 추가된 청크 수
        """
        if not chunks:
            logger.warning("추가할 청크가 없습니다")
            return 0
        
        logger.info(f"{len(chunks)}개 청크 임베딩 중...")
        
        # 텍스트 추출
        texts = [chunk.text for chunk in chunks]
        
        # 임베딩 생성
        embeddings = self.embed_texts(texts)
        
        # 메타데이터 준비
        metadatas = []
        ids = []
        
        for chunk in chunks:
            # 고유 ID 생성 (chunk_id 사용 또는 UUID)
            chunk_id = chunk.metadata.chunk_id or str(uuid.uuid4())
            ids.append(chunk_id)
            
            # 메타데이터 (ChromaDB는 문자열, 숫자, 불리언만 지원)
            metadata = {
                "document_id": chunk.metadata.document_id,
                "filename": chunk.metadata.filename,
                "page_number": chunk.metadata.page_number,
                "content_type": chunk.metadata.content_type,
                "chunk_index": chunk.metadata.chunk_index,
            }
            
            if chunk.metadata.total_chunks:
                metadata["total_chunks"] = chunk.metadata.total_chunks
            
            metadatas.append(metadata)
        
        # ChromaDB에 추가
        self.collection.add(
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas,
            ids=ids
        )
        
        logger.info(f"{len(chunks)}개 청크를 벡터 저장소에 추가 완료")
        return len(chunks)
    
    def add_document(self, processed_doc: ProcessedDocument, chunks: List[DocumentChunk]) -> int:
        """
        처리된 문서와 청크를 벡터 저장소에 추가
        
        Args:
            processed_doc: 처리된 문서
            chunks: 문서 청크 리스트
            
        Returns:
            int: 추가된 청크 수
        """
        logger.info(f"문서 추가 중: {processed_doc.filename}")
        return self.add_chunks(chunks)
    
    def search(
        self, 
        query: str, 
        top_k: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        쿼리로 유사한 청크 검색
        
        Args:
            query: 검색 쿼리
            top_k: 반환할 결과 수
            
        Returns:
            Dict: 검색 결과
        """
        if top_k is None:
            top_k = self.config.RAG_TOP_K
        
        # 쿼리 임베딩
        query_embedding = self.embed_text(query)
        
        # 검색
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            include=["documents", "metadatas", "distances"]
        )
        
        return results
    
    def delete_document(self, document_id: str) -> bool:
        """
        문서 ID로 모든 관련 청크 삭제
        
        Args:
            document_id: 문서 ID
            
        Returns:
            bool: 삭제 성공 여부
        """
        try:
            # 해당 문서의 모든 청크 찾기
            results = self.collection.get(
                where={"document_id": document_id}
            )
            
            if results and results['ids']:
                self.collection.delete(ids=results['ids'])
                logger.info(f"문서 삭제 완료: {document_id} ({len(results['ids'])}개 청크)")
                return True
            else:
                logger.warning(f"삭제할 문서를 찾을 수 없습니다: {document_id}")
                return False
                
        except Exception as e:
            logger.error(f"문서 삭제 중 오류: {e}")
            return False
    
    def count_documents(self) -> int:
        """저장된 총 청크 수 반환"""
        return self.collection.count()
    
    def reset_collection(self):
        """컬렉션 초기화 (모든 데이터 삭제)"""
        self.client.delete_collection(name=self.collection_name)
        self.collection = self._get_or_create_collection()
        logger.info(f"컬렉션 초기화 완료: {self.collection_name}")

