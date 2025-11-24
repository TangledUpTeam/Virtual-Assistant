"""
Insurance RAG 벡터 저장소 모듈

OpenAI text-embedding-3-large를 사용한 임베딩 생성 및 ChromaDB 직접 사용
한국어 → 영어 번역 후 임베딩 생성
"""

import chromadb
from chromadb.config import Settings
from typing import List, Dict, Any, Optional
import numpy as np

from .config import insurance_config
from .utils import get_logger

logger = get_logger(__name__)


class VectorStore:
    """Insurance RAG 벡터 저장소 관리 (ChromaDB 직접 사용, HR과 분리)"""
    
    def __init__(self, collection_name: Optional[str] = None):
        self.config = insurance_config
        self.collection_name = collection_name or self.config.CHROMA_COLLECTION_NAME
        
        # Lazy loading: 모델을 실제 사용 시에만 로드
        self._openai_client = None
        self._translation_client = None
        
        # ChromaDB 클라이언트 설정
        chroma_settings = Settings(
            anonymized_telemetry=False,
            allow_reset=True
        )
        
        # ChromaDB 클라이언트 초기화
        try:
            self.client = chromadb.PersistentClient(
                path=self.config.CHROMA_PERSIST_DIRECTORY,
                settings=chroma_settings
            )
        except Exception as e:
            logger.error(f"ChromaDB 클라이언트 초기화 실패: {e}")
            raise
        
        # 컬렉션 가져오기 또는 생성
        self.collection = self._get_or_create_collection()
        
        logger.info(f"Insurance 벡터 저장소 초기화 완료: {self.collection_name}")
    
    @property
    def openai_client(self):
        """OpenAI 클라이언트 lazy loading"""
        if self._openai_client is None:
            from openai import OpenAI
            self._openai_client = OpenAI(api_key=self.config.OPENAI_API_KEY)
            logger.info(f"OpenAI 임베딩 클라이언트 로드 완료: {self.config.EMBEDDING_MODEL}")
        return self._openai_client
    
    @property
    def translation_client(self):
        """번역용 OpenAI 클라이언트 lazy loading"""
        if self._translation_client is None:
            from openai import OpenAI
            self._translation_client = OpenAI(api_key=self.config.OPENAI_API_KEY)
            logger.info(f"번역 클라이언트 로드 완료: {self.config.TRANSLATION_MODEL}")
        return self._translation_client
    
    def _get_or_create_collection(self):
        """컬렉션 가져오기 또는 생성"""
        try:
            collection = self.client.get_collection(name=self.collection_name)
            logger.info(f"기존 Insurance 컬렉션 로드: {self.collection_name}")
        except Exception:
            try:
                collection = self.client.create_collection(
                    name=self.collection_name,
                    metadata={"description": "Insurance RAG 문서 임베딩"}
                )
                logger.info(f"새 Insurance 컬렉션 생성: {self.collection_name}")
            except Exception as e:
                logger.error(f"컬렉션 생성 실패: {e}")
                raise
        
        return collection
    
    def translate_to_english(self, korean_text: str) -> str:
        """
        한국어 텍스트를 영어로 번역 (GPT-4o-mini 사용)
        
        Args:
            korean_text: 번역할 한국어 텍스트
            
        Returns:
            str: 영어 번역 텍스트
        """
        try:
            response = self.translation_client.chat.completions.create(
                model=self.config.TRANSLATION_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a professional translator. Translate Korean text to English accurately. Only return the translated text, nothing else."
                    },
                    {
                        "role": "user",
                        "content": f"Translate this Korean text to English:\n\n{korean_text}"
                    }
                ],
                temperature=0.3,
                max_tokens=2000
            )
            
            translated_text = response.choices[0].message.content.strip()
            logger.debug(f"번역 완료: {len(korean_text)} chars -> {len(translated_text)} chars")
            return translated_text
            
        except Exception as e:
            logger.error(f"번역 중 오류: {e}")
            # 번역 실패 시 원본 텍스트 반환
            return korean_text
    
    def embed_text(self, text: str, translate: bool = True) -> List[float]:
        """
        텍스트를 벡터로 임베딩 (한→영 번역 후 임베딩)
        
        Args:
            text: 임베딩할 텍스트
            translate: 한→영 번역 여부
            
        Returns:
            List[float]: 임베딩 벡터
        """
        # 한국어 텍스트를 영어로 번역
        if translate:
            text_to_embed = self.translate_to_english(text)
        else:
            text_to_embed = text
        
        try:
            response = self.openai_client.embeddings.create(
                model=self.config.EMBEDDING_MODEL,
                input=text_to_embed
            )
            embedding = response.data[0].embedding
            logger.debug(f"임베딩 생성 완료: 차원 {len(embedding)}")
            return embedding
            
        except Exception as e:
            logger.error(f"임베딩 생성 중 오류: {e}")
            raise
    
    def calculate_cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """
        두 벡터 간의 cosine similarity 직접 계산
        
        Args:
            vec1: 첫 번째 벡터
            vec2: 두 번째 벡터
            
        Returns:
            float: Cosine similarity (0~1, 높을수록 유사)
        """
        vec1_np = np.array(vec1)
        vec2_np = np.array(vec2)
        
        # Cosine similarity = dot(A, B) / (||A|| * ||B||)
        dot_product = np.dot(vec1_np, vec2_np)
        norm1 = np.linalg.norm(vec1_np)
        norm2 = np.linalg.norm(vec2_np)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        similarity = dot_product / (norm1 * norm2)
        
        # 0~1 범위로 정규화
        similarity = max(0.0, min(1.0, similarity))
        
        return float(similarity)
    
    def search(
        self, 
        query: str, 
        top_k: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        쿼리로 유사한 청크 검색 (쿼리도 한→영 번역 후 검색)
        Internal cosine similarity 직접 계산
        
        Args:
            query: 검색 쿼리 (한국어)
            top_k: 반환할 결과 수
            
        Returns:
            Dict: 검색 결과 (기존 형식 유지, distances는 similarity score)
        """
        if top_k is None:
            top_k = self.config.RAG_TOP_K
        
        # 저장된 문서가 있는지 확인
        doc_count = self.collection.count()
        if doc_count == 0:
            logger.warning("저장된 Insurance 문서가 없습니다.")
            return {
                "documents": [[]],
                "metadatas": [[]],
                "distances": [[]]
            }
        
        # 쿼리 임베딩 (한→영 번역 후)
        try:
            logger.info(f"쿼리 번역 및 임베딩 생성 중: '{query}'")
            query_embedding = self.embed_text(query, translate=True)
            logger.debug(f"쿼리 임베딩 생성 완료 (차원: {len(query_embedding)})")
        except Exception as e:
            logger.error(f"쿼리 임베딩 생성 실패: {e}")
            return {
                "documents": [[]],
                "metadatas": [[]],
                "distances": [[]]
            }
        
        # ChromaDB에서 임베딩 포함하여 검색
        try:
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=min(top_k * 3, doc_count),  # 동적 threshold를 위해 더 많이 검색
                include=['documents', 'metadatas', 'embeddings']
            )
            logger.debug(f"ChromaDB 검색 결과: {len(results.get('ids', [[]])[0]) if results.get('ids') else 0}개")
        except Exception as e:
            logger.error(f"ChromaDB 검색 실패: {e}")
            return {
                "documents": [[]],
                "metadatas": [[]],
                "distances": [[]]
            }
        
        # 결과 처리 및 internal similarity 계산
        documents = []
        metadatas = []
        similarities = []
        
        if results and results.get('documents') and results['documents']:
            doc_list = results['documents'][0] if results['documents'][0] else []
            embeddings_list = results.get('embeddings', [[]])[0] if results.get('embeddings') else []
            
            for i in range(len(doc_list)):
                # 문서와 메타데이터 추가
                documents.append(doc_list[i])
                
                if results.get('metadatas') and results['metadatas'][0] and i < len(results['metadatas'][0]):
                    metadatas.append(results['metadatas'][0][i])
                else:
                    metadatas.append({})
                
                # Internal cosine similarity 직접 계산
                if embeddings_list is not None and i < len(embeddings_list):
                    doc_embedding = embeddings_list[i]
                    similarity = self.calculate_cosine_similarity(query_embedding, doc_embedding)
                    similarities.append(similarity)
                    logger.debug(f"문서 {i+1} cosine similarity: {similarity:.4f}")
                else:
                    similarities.append(0.0)
        
        logger.info(f"Insurance 검색 완료: {len(documents)}개 결과 반환")
        
        return {
            "documents": [documents],
            "metadatas": [metadatas],
            "distances": [similarities]  # similarities로 변경
        }
    
    def count_documents(self) -> int:
        """저장된 총 청크 수 반환"""
        return self.collection.count()
    
    def reset_collection(self):
        """컬렉션 초기화 (모든 데이터 삭제)"""
        try:
            self.client.delete_collection(name=self.collection_name)
            self.collection = self._get_or_create_collection()
            logger.info(f"Insurance 컬렉션 초기화 완료: {self.collection_name}")
        except Exception as e:
            logger.error(f"컬렉션 초기화 중 오류: {e}")
            raise



