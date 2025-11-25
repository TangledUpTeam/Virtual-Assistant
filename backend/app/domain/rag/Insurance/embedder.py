"""
Insurance RAG 임베딩 모듈

한국어 → 영어 번역 후 임베딩 생성 및 ChromaDB 저장

ID 충돌 방지:
- 청크 ID는 UUID 기반으로 생성되어 항상 고유함
- 동일 PDF를 여러 번 처리해도 ID 충돌이 발생하지 않음
"""

import json
import uuid
from pathlib import Path
from typing import List

from openai import OpenAI
from chromadb import PersistentClient

from .config import insurance_config
from .utils import get_logger

logger = get_logger(__name__)

# OpenAI 클라이언트는 함수 내에서 lazy loading
_client = None


def get_openai_client() -> OpenAI:
    """OpenAI 클라이언트 lazy loading"""
    global _client
    if _client is None:
        _client = OpenAI(api_key=insurance_config.OPENAI_API_KEY)
        logger.info("OpenAI 클라이언트 초기화 완료")
    return _client


def translate(text: str) -> str:
    """
    한국어 텍스트를 영어로 번역 (GPT-4o-mini 사용)
    
    Args:
        text: 번역할 한국어 텍스트
        
    Returns:
        str: 번역된 영어 텍스트
    """
    client = get_openai_client()
    
    try:
        resp = client.chat.completions.create(
            model=insurance_config.TRANSLATION_MODEL,
            temperature=0,
            messages=[{
                "role": "user",
                "content": f"Translate this Korean text to English, preserving meaning:\n{text}"
            }],
        )
        translated = resp.choices[0].message.content.strip()
        logger.debug(f"번역 완료: {len(text)}자 → {len(translated)}자")
        return translated
    except Exception as e:
        logger.error(f"번역 중 오류 발생: {e}")
        raise


def embed(text: str) -> List[float]:
    """
    영어 텍스트를 임베딩 벡터로 변환 (text-embedding-3-large 사용)
    
    Args:
        text: 임베딩할 영어 텍스트
        
    Returns:
        List[float]: 임베딩 벡터
    """
    client = get_openai_client()
    
    try:
        emb = client.embeddings.create(
            model=insurance_config.EMBEDDING_MODEL,
            input=text
        )
        vector = emb.data[0].embedding
        logger.debug(f"임베딩 생성 완료: {len(vector)}차원")
        return vector
    except Exception as e:
        logger.error(f"임베딩 생성 중 오류 발생: {e}")
        raise


def embed_chunks(chunks_path: Path) -> bool:
    """
    청크 파일을 읽어서 번역, 임베딩 후 ChromaDB에 저장
    
    Args:
        chunks_path: 청크 JSON 파일 경로
        
    Returns:
        bool: 성공 여부
    """
    logger.info(f"청크 임베딩 시작: {chunks_path}")
    
    try:
        # 청크 파일 읽기
        with open(chunks_path, "r", encoding="utf-8") as f:
            chunks = json.load(f)
        
        logger.info(f"청크 {len(chunks)}개 로드 완료")
        
        # ChromaDB 연결
        db = PersistentClient(path=insurance_config.CHROMA_PERSIST_DIRECTORY)
        
        # 컬렉션 가져오기 또는 생성
        try:
            col = db.get_collection(insurance_config.CHROMA_COLLECTION_NAME)
            logger.info(f"기존 컬렉션 로드: {insurance_config.CHROMA_COLLECTION_NAME}")
        except Exception:
            col = db.create_collection(insurance_config.CHROMA_COLLECTION_NAME)
            logger.info(f"새 컬렉션 생성: {insurance_config.CHROMA_COLLECTION_NAME}")
        
        # 각 청크 처리
        success_count = 0
        skipped_count = 0
        
        for idx, ch in enumerate(chunks, 1):
            try:
                text = ch.get("content", "").strip()
                
                # 빈 청크 또는 너무 짧은 청크 스킵
                if not text or len(text) < 10:
                    logger.debug(f"청크 {idx}: 빈 청크 또는 너무 짧은 청크 스킵 ({len(text)}자)")
                    skipped_count += 1
                    continue
                
                # OCR 실패 메시지 체크 (추가 안전장치)
                ocr_failure_indicators = [
                    "i'm sorry", "can't assist", "can't transcribe",
                    "image appears to be blank", "provide a different image"
                ]
                if any(indicator in text.lower() for indicator in ocr_failure_indicators):
                    logger.warning(f"청크 {idx}: OCR 실패 메시지 감지, 스킵: {text[:50]}...")
                    skipped_count += 1
                    continue
                
                # 청크 ID 확인 및 생성 (UUID 기반으로 이미 고유함)
                chunk_id = ch.get("id")
                if not chunk_id:
                    # ID가 없는 경우 (이전 버전 호환성) UUID 생성
                    # 형식: ins_{문서UUID}_{청크UUID} (chunker와 동일)
                    chunk_uuid = uuid.uuid4().hex
                    doc_uuid = uuid.uuid4().hex[:8]  # 8자리 짧은 UUID
                    chunk_id = f"ins_{doc_uuid}_{chunk_uuid}"
                    logger.warning(f"청크 {idx}: ID가 없어 새 UUID 생성: {chunk_id}")
                
                # 번역
                translated = translate(text)
                
                # 번역 결과 검증
                if not translated or len(translated.strip()) < 10:
                    logger.warning(f"청크 {idx}: 번역 결과가 비어있거나 너무 짧음, 스킵")
                    skipped_count += 1
                    continue
                
                # 임베딩
                vector = embed(translated)
                
                # ChromaDB에 추가
                # UUID 기반 고유 ID 사용으로 ID 충돌 발생하지 않음
                col.add(
                    ids=[chunk_id],
                    embeddings=[vector],
                    metadatas=[ch.get("metadata", {})],
                    documents=[text],  # 원본 한국어 텍스트 저장
                )
                
                success_count += 1
                if idx % 10 == 0:
                    logger.info(f"진행 상황: {idx}/{len(chunks)}개 청크 처리 완료 (성공: {success_count}, 스킵: {skipped_count})")
                    
            except Exception as e:
                error_msg = str(e)
                # ChromaDB ID 충돌 오류 처리 (UUID 사용으로 거의 발생하지 않음)
                if "existing" in error_msg.lower() or "duplicate" in error_msg.lower() or "already exists" in error_msg.lower():
                    logger.warning(f"청크 {idx}: ID 충돌로 인한 오류 (스킵): {chunk_id} - {error_msg}")
                    skipped_count += 1
                else:
                    logger.error(f"청크 {idx} 처리 중 오류 (ID: {chunk_id}): {e}")
                continue
        
        logger.info(f"임베딩 완료: 성공 {success_count}개 / 스킵 {skipped_count}개 / 전체 {len(chunks)}개")
        
        if success_count == 0 and skipped_count > 0:
            logger.warning("모든 청크가 스킵되었습니다. 컬렉션을 초기화하고 다시 시도하세요: python -m app.domain.rag.Insurance.cli reset")
        
        return success_count > 0
        
    except Exception as e:
        logger.exception(f"임베딩 프로세스 중 오류 발생: {e}")
        raise
