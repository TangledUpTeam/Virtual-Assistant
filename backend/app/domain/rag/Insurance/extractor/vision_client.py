"""
Insurance RAG PDF 추출 모듈 - Vision/LLM 클라이언트

Vision OCR 및 LLM 병합 기능을 제공하는 클라이언트 모듈
의존성 주입을 통해 테스트 가능하도록 구성
"""

from typing import List

from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from ..config import insurance_config
from ..utils import get_logger
from ..cache_utils import cache_key, get_cache, set_cache
from ..constants import OCR_FAILURE_INDICATORS
from .prompts import VISION_OCR_PROMPT, get_llm_merge_prompt

logger = get_logger(__name__)


def is_vision_failure(text: str) -> bool:
    """
    Vision OCR 실패 판정
    
    Args:
        text: Vision OCR 결과 텍스트
        
    Returns:
        bool: 실패 여부
    """
    if not text:
        return True
    
    text_lower = text.lower().strip()
    for indicator in OCR_FAILURE_INDICATORS:
        if indicator in text_lower:
            return True
    
    if len(text_lower) < 10:
        return True
    
    return False


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(Exception),
    reraise=True
)
def vision_ocr(jpeg_data_url: str, client: OpenAI) -> str:
    """
    Vision API OCR (재시도 로직 + 디스크 캐싱)
    
    최대 3번까지 재시도하며, 재시도 간격은 지수 백오프 방식(2초, 4초, 8초)으로 증가합니다.
    성공한 결과는 디스크에 캐싱되어 재사용됩니다.
    
    Args:
        jpeg_data_url: JPEG base64 data URL
        client: OpenAI 클라이언트 (의존성 주입)
        
    Returns:
        OCR 결과 텍스트 (Markdown 형식)
        
    Raises:
        Exception: Vision OCR 실패 시 (3번 재시도 후)
    """
    # 캐시 확인
    key = cache_key("vision", jpeg_data_url)
    cached = get_cache(key)
    if cached is not None:
        logger.debug(f"Vision OCR 캐시 히트: {len(cached)}자")
        return cached
    
    try:
        resp = client.chat.completions.create(
            model=insurance_config.OPENAI_VISION_MODEL,
            temperature=0,
            max_tokens=2000,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": VISION_OCR_PROMPT},
                    {"type": "image_url", "image_url": {"url": jpeg_data_url}}
                ]
            }]
        )
        result = resp.choices[0].message.content or ""
        logger.debug(f"Vision OCR 성공: {len(result)}자 추출")
        
        # 성공한 결과만 캐싱 (실패 메시지는 캐싱하지 않음)
        if not is_vision_failure(result):
            set_cache(key, result)
        
        return result
    except Exception as e:
        logger.warning(f"Vision OCR 시도 실패: {e}")
        raise


def merge_with_llm(raw_text: str, vision_markdown: str, client: OpenAI) -> str:
    """
    Vision OCR 결과와 raw_text를 LLM으로 병합 (디스크 캐싱)
    
    Args:
        raw_text: PyMuPDF로 추출한 원문 텍스트
        vision_markdown: Vision OCR로 추출한 Markdown 텍스트
        client: OpenAI 클라이언트 (의존성 주입)
        
    Returns:
        병합된 Markdown 형식의 텍스트
    """
    # 캐시 확인
    key = cache_key("merge", raw_text + "|" + vision_markdown)
    cached = get_cache(key)
    if cached is not None:
        logger.debug(f"LLM 병합 캐시 히트: {len(cached)}자")
        return cached
    
    prompt = get_llm_merge_prompt(raw_text, vision_markdown)
    
    try:
        resp = client.chat.completions.create(
            model=insurance_config.OPENAI_MODEL,
            temperature=0,
            max_tokens=insurance_config.OPENAI_MAX_TOKENS,
            messages=[{
                "role": "user",
                "content": prompt
            }]
        )
        result = resp.choices[0].message.content or ""
        logger.debug(f"LLM 병합 완료: {len(result)}자 생성")
        
        # 성공한 결과 캐싱
        set_cache(key, result)
        
        return result
    except Exception as e:
        logger.error(f"LLM 병합 중 오류 발생: {e}")
        # 오류 발생 시 Vision 결과를 우선 사용
        return vision_markdown if vision_markdown.strip() else raw_text
