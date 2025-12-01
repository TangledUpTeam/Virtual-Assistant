"""
Insurance RAG 디스크 캐시 유틸리티

Vision OCR, LLM 병합, 임베딩 결과를 디스크에 캐싱하여 재사용
"""

from hashlib import sha256
from pathlib import Path
import json
from typing import Optional, Any

from .utils import get_logger

logger = get_logger(__name__)

# 캐시 디렉토리
CACHE_DIR = Path(__file__).parent / "insurance_cache"
CACHE_DIR.mkdir(exist_ok=True)


def cache_key(prefix: str, content: str) -> str:
    """
    캐시 키 생성 (SHA256 해시)
    
    Args:
        prefix: 캐시 타입 (vision, merge, embed)
        content: 입력 내용
        
    Returns:
        str: 캐시 키
    """
    h = sha256(content.encode("utf-8")).hexdigest()
    return f"{prefix}_{h}"


def get_cache(key: str) -> Optional[Any]:
    """
    캐시에서 값 조회
    
    Args:
        key: 캐시 키
        
    Returns:
        캐시된 값 또는 None
    """
    cache_file = CACHE_DIR / f"{key}.json"
    if cache_file.exists():
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                logger.debug(f"캐시 히트: {key}")
                return data["value"]
        except Exception as e:
            logger.warning(f"캐시 읽기 실패: {key} - {e}")
            return None
    return None


def set_cache(key: str, value: Any) -> None:
    """
    캐시에 값 저장
    
    Args:
        key: 캐시 키
        value: 저장할 값
    """
    cache_file = CACHE_DIR / f"{key}.json"
    try:
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump({"value": value}, f, ensure_ascii=False)
        logger.debug(f"캐시 저장: {key}")
    except Exception as e:
        logger.warning(f"캐시 저장 실패: {key} - {e}")
