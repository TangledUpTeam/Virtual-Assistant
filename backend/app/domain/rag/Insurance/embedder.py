"""
Insurance RAG 임베딩 모듈 (실무형 최적화 버전)

한국어 텍스트를 직접 임베딩하여 ChromaDB에 저장합니다.
- text-embedding-3-large는 한국어 임베딩이 매우 우수하므로 번역 과정 제거
- batch insert로 성능 최적화
- chunker에서 이미 처리된 검증은 중복 제거
"""

import json
from pathlib import Path
from typing import List, Dict, Any

from openai import OpenAI
from chromadb import PersistentClient

from .config import insurance_config
from .utils import get_logger
from .cache_utils import cache_key, get_cache, set_cache

logger = get_logger(__name__)

# OpenAI 클라이언트 lazy loading (thread-safe)
_client = None
_client_lock = None


def _get_lock():
    """Lock 객체 lazy initialization"""
    global _client_lock
    if _client_lock is None:
        from threading import Lock
        _client_lock = Lock()
    return _client_lock


def get_openai_client() -> OpenAI:
    """OpenAI 클라이언트 lazy loading (thread-safe)"""
    global _client
    if _client is None:
        with _get_lock():
            if _client is None:
                _client = OpenAI(api_key=insurance_config.OPENAI_API_KEY)
                logger.info("OpenAI 클라이언트 초기화 완료")
    return _client


def embed(text: str) -> List[float]:
    """
    한국어 텍스트를 임베딩 벡터로 변환 (text-embedding-3-large 사용 + 디스크 캐싱)
    
    Args:
        text: 임베딩할 한국어 텍스트
        
    Returns:
        List[float]: 임베딩 벡터
    """
    # 캐시 확인
    key = cache_key("embed", text)
    cached = get_cache(key)
    if cached is not None:
        logger.debug(f"임베딩 캐시 히트: {len(text)}자")
        return cached
    
    client = get_openai_client()
    emb = client.embeddings.create(
        model=insurance_config.EMBEDDING_MODEL,
        input=text
    )
    result = emb.data[0].embedding
    
    # 캐싱
    set_cache(key, result)
    
    return result


def embed_batch(texts: List[str]) -> List[List[float]]:
    """
    여러 텍스트를 배치로 임베딩 생성
    
    Args:
        texts: 임베딩할 텍스트 리스트
        
    Returns:
        List[List[float]]: 임베딩 벡터 리스트
        
    Raises:
        Exception: OpenAI API 호출 실패 시
    """
    if not texts:
        return []
    
    try:
        client = get_openai_client()
        emb = client.embeddings.create(
            model=insurance_config.EMBEDDING_MODEL,
            input=texts
        )
        return [item.embedding for item in emb.data]
    except Exception as e:
        logger.error(f"배치 임베딩 생성 실패: {e}")
        raise


def embed_chunks(chunks_path: Path, batch_size: int = 100) -> bool:
    """
    청크 파일을 읽어서 임베딩 후 ChromaDB에 배치 저장
    
    Args:
        chunks_path: 청크 JSON 파일 경로
        batch_size: 배치 크기 (기본값: 100)
        
    Returns:
        bool: 성공 여부
    """
    logger.info(f"청크 임베딩 시작: {chunks_path}")
    
    # 청크 파일 로드
    with open(chunks_path, "r", encoding="utf-8") as f:
        chunks = json.load(f)
    
    logger.info(f"청크 {len(chunks)}개 로드 완료")
    
    # ChromaDB 연결
    db = PersistentClient(path=insurance_config.CHROMA_PERSIST_DIRECTORY)
    
    try:
        col = db.get_collection(insurance_config.CHROMA_COLLECTION_NAME)
        logger.info(f"기존 컬렉션 로드: {insurance_config.CHROMA_COLLECTION_NAME}")
    except Exception:
        col = db.create_collection(insurance_config.CHROMA_COLLECTION_NAME)
        logger.info(f"새 컬렉션 생성: {insurance_config.CHROMA_COLLECTION_NAME}")
    
    # 유효한 청크만 필터링
    valid_chunks = []
    skipped_count = 0
    
    for idx, chunk in enumerate(chunks, 1):
        chunk_id = chunk.get("id")
        if not chunk_id:
            logger.error(f"청크 {idx}: ID가 없습니다. chunker에서 UUID를 생성해야 합니다.")
            skipped_count += 1
            continue
        
        text = chunk.get("content", "").strip()
        if not text or len(text) < 10:
            logger.debug(f"청크 {idx} (ID: {chunk_id}): 빈 텍스트 또는 너무 짧음, 스킵")
            skipped_count += 1
            continue
        
        valid_chunks.append({
            "id": chunk_id,
            "text": text,
            "metadata": chunk.get("metadata", {})
        })
    
    if not valid_chunks:
        logger.warning("유효한 청크가 없습니다.")
        return False
    
    logger.info(f"유효한 청크 {len(valid_chunks)}개 (스킵: {skipped_count}개)")
    
    # 배치 단위로 처리
    success_count = 0
    total_batches = (len(valid_chunks) + batch_size - 1) // batch_size
    
    for batch_idx in range(0, len(valid_chunks), batch_size):
        batch = valid_chunks[batch_idx:batch_idx + batch_size]
        current_batch_num = (batch_idx // batch_size) + 1
        
        # 배치 임베딩 생성
        texts = [item["text"] for item in batch]
        embeddings = embed_batch(texts)
        
        try:
            # ChromaDB 배치 추가
            col.add(
                ids=[item["id"] for item in batch],
                embeddings=embeddings,
                metadatas=[item["metadata"] for item in batch],
                documents=[item["text"] for item in batch],  # 원본 한국어 텍스트
            )
            
            success_count += len(batch)
            logger.info(
                f"[Batch {current_batch_num}/{total_batches}] {len(batch)} chunks saved "
                f"(total {success_count}/{len(valid_chunks)})"
            )
            
        except Exception as e:
            logger.error(f"[Batch {current_batch_num}] Error during batch insert: {e}")
            # 개별 청크로 fallback 시도 (재임베딩 금지: 이미 생성한 embeddings 재사용)
            for i, item in enumerate(batch):
                try:
                    vector = embeddings[i]  # 이미 생성한 임베딩 재사용
                    col.add(
                        ids=[item["id"]],
                        embeddings=[vector],
                        metadatas=[item["metadata"]],
                        documents=[item["text"]],
                    )
                    success_count += 1
                except Exception as e2:
                    logger.error(f"[Fallback] Failed to insert chunk {item['id']}: {e2}")
    
    logger.info(
        f"임베딩 완료: 성공 {success_count}개 / 스킵 {skipped_count}개 / 전체 {len(chunks)}개"
    )
    
    return success_count > 0
