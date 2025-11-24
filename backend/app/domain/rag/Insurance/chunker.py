"""
Insurance RAG 청킹 모듈

추출된 JSON을 텍스트 청크로 변환
"""

import json
import uuid
from pathlib import Path

from .config import insurance_config
from .utils import get_logger

logger = get_logger(__name__)


def merge_page_text(page):
    text = page.get("text", "").strip()

    for key, label in [
        ("tables_markdown", "[표]"),
        ("vision_markdown", "[스캔 OCR]"),
    ]:
        if page.get(key):
            value = page[key]
            if isinstance(value, list):
                value = "\n\n".join(value)
            text += f"\n\n{label}\n{value}"

    return text


def simple_chunk(text, chunk_size=900, overlap=200):
    chunks = []
    start = 0
    while start < len(text):
        end = min(len(text), start + chunk_size)
        chunks.append(text[start:end].strip())
        start += chunk_size - overlap
    return chunks


def chunk_json(json_path: Path) -> Path:
    """
    추출된 JSON 파일을 청크로 변환
    
    Args:
        json_path: 추출된 JSON 파일 경로
        
    Returns:
        Path: 생성된 청크 JSON 파일 경로
    """
    json_path = Path(json_path)
    
    if not json_path.exists():
        raise FileNotFoundError(f"JSON 파일을 찾을 수 없습니다: {json_path}")
    
    logger.info(f"청킹 시작: {json_path.name}")
    
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # 문서별 고유 UUID 생성 (동일 문서의 모든 청크가 동일한 prefix를 가짐)
        # 이를 통해 문서 단위로 청크를 식별할 수 있음
        document_uuid = uuid.uuid4().hex[:8]  # 8자리 짧은 UUID
        source_filename = Path(data.get("file", "")).name
        
        logger.info(f"문서별 UUID prefix 생성: {document_uuid} (파일: {source_filename})")
        
        output_chunks = []
        chunk_index = 0  # 순차 인덱스 (로그용)

        for page in data.get("pages", []):
            page_num = page.get("page", 1)
            page_text = merge_page_text(page)
            
            # 청크 생성
            chunks = simple_chunk(
                page_text,
                chunk_size=insurance_config.RAG_CHUNK_SIZE,
                overlap=insurance_config.RAG_CHUNK_OVERLAP
            )
            
            logger.debug(f"페이지 {page_num}: {len(chunks)}개 청크 생성")

            for c in chunks:
                if not c.strip():  # 빈 청크 스킵
                    continue
                
                # UUID 기반 고유 ID 생성 (충돌 방지)
                # 형식: ins_{문서UUID}_{청크UUID}
                chunk_uuid = uuid.uuid4().hex
                unique_chunk_id = f"ins_{document_uuid}_{chunk_uuid}"
                
                chunk_index += 1
                    
                output_chunks.append({
                    "id": unique_chunk_id,  # UUID 기반 고유 ID
                    "content": c.strip(),
                    "metadata": {
                        "page": page_num,
                        "source": source_filename,
                        "filename": source_filename,
                        "page_number": page_num,
                        "document_uuid": document_uuid,  # 문서 식별을 위한 UUID
                        "chunk_index": chunk_index  # 순차 인덱스 (디버깅용)
                    }
                })

        out_path = insurance_config.PROCESSED_DIR / f"{json_path.stem}_chunks.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(output_chunks, f, indent=2, ensure_ascii=False)

        logger.info(f"청킹 완료: {out_path} ({len(output_chunks)}개 청크)")
        return out_path
        
    except Exception as e:
        logger.exception(f"청킹 중 오류 발생: {e}")
        raise
