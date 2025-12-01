"""
Insurance RAG 청킹 핵심 모듈

Production-grade 토큰 기반 청킹 시스템

⚠️ 중요: 이 모듈은 extractor.py의 output schema에 정확히 맞춰져 있어야 합니다.
extractor.py는 page["content"] 필드에 이미 병합된 최종 텍스트를 제공합니다.
따라서 이 모듈은 content 필드만 사용하며, tables_markdown, vision_markdown 등의
별도 필드는 존재하지 않습니다.

- tiktoken 기반 토큰 단위 청킹
- 문단 기반 pre-split
- OCR 실패 메시지 자동 필터링
- 강화된 청크 유효성 검증
"""

import json
import uuid
from pathlib import Path
from typing import List, Dict, Any

from ..config import insurance_config
from ..utils import get_logger
from .splitter import pre_split_paragraphs
from .tokenizer import token_chunk, get_encoder
from .filters import is_ocr_failure_message, filter_chunk, MIN_CHUNK_LENGTH

logger = get_logger(__name__)


def extract_page_content(page: Dict[str, Any]) -> str:
    """
    페이지에서 content 필드를 추출
    
    extractor.py는 page["content"]에 이미 병합된 최종 텍스트를 제공합니다.
    이 함수는 단순히 content 필드를 반환하며, OCR 실패 메시지는 필터링합니다.
    
    Args:
        page: 페이지 딕셔너리 (extractor.py 출력 구조)
        
    Returns:
        페이지 텍스트 (OCR 실패 메시지 제외)
    """
    content = page.get("content", "").strip()
    
    if not content:
        return ""
    
    # OCR 실패 메시지 필터링
    if is_ocr_failure_message(content):
        page_num = page.get("page", "?")
        logger.warning(
            f"페이지 {page_num}: OCR 실패 메시지 감지 및 제외 "
            f"(길이: {len(content)}자, 내용: '{content[:50]}...')"
        )
        return ""
    
    return content


def chunk_text_with_tokens(
    text: str,
    max_tokens: int = 500,
    overlap_tokens: int = 80
) -> List[str]:
    """
    문단 기반 pre-split 후 토큰 기반 청킹 적용
    
    프로세스:
    1. paragraph split
    2. 문단을 순차적으로 합치되, 토큰이 max_tokens를 초과하는 순간 token_chunk()에 위임
    3. token_chunk는 "슬라이딩 윈도우 기반 작은 조각 분리"만 수행
    
    Args:
        text: 원본 텍스트
        max_tokens: 최대 토큰 수
        overlap_tokens: 오버랩 토큰 수
        
    Returns:
        최종 청크 리스트
    """
    if not text or not text.strip():
        return []
    
    # 1) 문단 단위로 pre-split
    paragraphs = pre_split_paragraphs(text)
    
    if not paragraphs:
        return []
    
    # 2) tiktoken 인코딩 초기화
    try:
        enc = get_encoder()
    except Exception as e:
        logger.error(f"tiktoken 인코딩 초기화 실패: {e}")
        # fallback: 문단을 그대로 반환
        return [p.strip() for p in paragraphs if p.strip()]
    
    # 3) paragraph 단위로 token-safe하게 chunk 모으기
    all_chunks = []
    current_chunk_parts = []
    
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        
        # 현재 청크에 문단 추가 시 토큰 수 확인
        test_parts = current_chunk_parts + [para]
        test_text = "\n\n".join(test_parts)
        
        try:
            test_tokens = enc.encode(test_text)
            
            if len(test_tokens) <= max_tokens:
                # 현재 청크에 추가 가능
                current_chunk_parts.append(para)
            else:
                # 현재 청크 저장 (overflow 발생)
                if current_chunk_parts:
                    current_chunk_text = "\n\n".join(current_chunk_parts)
                    # 현재 청크가 너무 길면 token_chunk로 분할
                    if len(enc.encode(current_chunk_text)) > max_tokens:
                        sub_chunks = token_chunk(current_chunk_text, max_tokens, overlap_tokens)
                        all_chunks.extend(sub_chunks)
                    else:
                        all_chunks.append(current_chunk_text)
                
                # 새 문단 처리
                para_tokens = enc.encode(para)
                if len(para_tokens) > max_tokens:
                    # 새 문단도 너무 길면 token_chunk로 분할
                    sub_chunks = token_chunk(para, max_tokens, overlap_tokens)
                    all_chunks.extend(sub_chunks)
                else:
                    current_chunk_parts = [para]
        except Exception as e:
            logger.warning(f"문단 토큰 계산 중 오류 (문단 길이: {len(para)}자): {e}")
            # 오류 발생 시 현재 청크 저장 후 새 문단 시작
            if current_chunk_parts:
                all_chunks.append("\n\n".join(current_chunk_parts))
            all_chunks.append(para)
            current_chunk_parts = []
    
    # 마지막 청크 추가
    if current_chunk_parts:
        current_chunk_text = "\n\n".join(current_chunk_parts)
        try:
            if len(enc.encode(current_chunk_text)) > max_tokens:
                sub_chunks = token_chunk(current_chunk_text, max_tokens, overlap_tokens)
                all_chunks.extend(sub_chunks)
            else:
                all_chunks.append(current_chunk_text)
        except Exception:
            # 인코딩 실패 시 그대로 추가
            all_chunks.append(current_chunk_text)
    
    return all_chunks


def chunk_json(json_path: Path) -> Path:
    """
    추출된 JSON 파일을 토큰 기반 청크로 변환
    
    이 함수는 extractor.py의 출력 구조에 정확히 맞춰져 있습니다:
    - page["content"]: 이미 병합된 최종 텍스트
    - page["mode"]: 페이지 모드 (text, vision, vision-fallback, empty)
    - page["page"]: 페이지 번호
    
    Args:
        json_path: 추출된 JSON 파일 경로
        
    Returns:
        Path: 생성된 청크 JSON 파일 경로
    """
    json_path = Path(json_path)
    
    if not json_path.exists():
        raise FileNotFoundError(f"JSON 파일을 찾을 수 없습니다: {json_path}")
    
    logger.info(f"청킹 시작: {json_path.name}")
    
    # JSON 파일 로드
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        logger.error(f"JSON 파싱 실패: {json_path} - {e}")
        raise
    except Exception as e:
        logger.error(f"파일 읽기 실패: {json_path} - {e}")
        raise
    
    # 문서별 고유 UUID 생성
    document_uuid = uuid.uuid4().hex[:8]
    source_filename = Path(data.get("file", "")).name or json_path.stem
    
    logger.info(
        f"문서 처리 시작: UUID={document_uuid}, 파일={source_filename}, "
        f"총 페이지={len(data.get('pages', []))}"
    )
    
    # 페이지 처리 (reducer-style)
    output_chunks = []
    chunk_index = 0
    processed_pages = 0
    skipped_pages = 0
    
    for page in data.get("pages", []):
        page_num = page.get("page", 0)
        page_mode = page.get("mode", "unknown")
        
        # 빈 페이지 스킵
        if page_mode == "empty":
            skipped_pages += 1
            continue
        
        # 페이지 content 추출
        page_text = extract_page_content(page)
        
        if not page_text or len(page_text.strip()) < MIN_CHUNK_LENGTH:
            skipped_pages += 1
            continue
        
        # 토큰 기반 청킹
        chunks = chunk_text_with_tokens(
            page_text,
            max_tokens=insurance_config.RAG_CHUNK_TOKENS,
            overlap_tokens=insurance_config.RAG_CHUNK_OVERLAP_TOKENS
        )
        
        if not chunks:
            skipped_pages += 1
            continue
        
        processed_pages += 1
        
        # 청크 필터링 및 추가
        for chunk_text in chunks:
            chunk_text = chunk_text.strip()
            
            if not filter_chunk(chunk_text):
                continue
            
            chunk_uuid = uuid.uuid4().hex
            unique_chunk_id = f"ins_{document_uuid}_{chunk_uuid}"
            chunk_index += 1
            
            output_chunks.append({
                "id": unique_chunk_id,
                "content": chunk_text,
                "metadata": {
                    "page": page_num,
                    "page_mode": page_mode,
                    "filename": source_filename,
                    "document_uuid": document_uuid,
                    "chunk_uuid": chunk_uuid,
                    "chunk_index": chunk_index
                }
            })
    
    # 결과 저장
    out_path = insurance_config.PROCESSED_DIR / f"{json_path.stem}_chunks.json"
    
    try:
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(output_chunks, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"청크 파일 저장 실패: {out_path} - {e}")
        raise
    
    logger.info(
        f"청킹 완료: {out_path} "
        f"(총 청크: {len(output_chunks)}개, 처리된 페이지: {processed_pages}개, "
        f"스킵된 페이지: {skipped_pages}개)"
    )
    
    return out_path

