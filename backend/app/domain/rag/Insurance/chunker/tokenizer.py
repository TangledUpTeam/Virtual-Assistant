"""
토큰화 유틸리티 모듈 (실무형 최적화 버전)
"""

import tiktoken
from typing import List
from app.domain.rag.Insurance.utils import get_logger

logger = get_logger(__name__)

TIKTOKEN_ENCODING = "cl100k_base"
_encoder = None


# ---------------------------------------------------------
# 인코더 초기화
# ---------------------------------------------------------
def get_encoder():
    """tiktoken 인코더 lazy-loading"""
    global _encoder
    if _encoder is None:
        try:
            _encoder = tiktoken.get_encoding(TIKTOKEN_ENCODING)
            logger.debug(f"tiktoken 인코더 로딩 완료: {TIKTOKEN_ENCODING}")
        except Exception as e:
            logger.error(f"tiktoken 인코더 초기화 실패: {e}")
            return None
    return _encoder


# ---------------------------------------------------------
# 기본 tokenize / detokenize
# ---------------------------------------------------------
def tokenize(text: str) -> List[int]:
    if not text:
        return []
    enc = get_encoder()
    if enc is None:
        logger.warning("인코더 없음. 공백 split fallback 사용.")
        return text.split()
    try:
        return enc.encode(text)
    except Exception:
        logger.warning("tiktoken encode 실패. 공백 split fallback 사용.")
        return text.split()


def detokenize(token_ids: List[int]) -> str:
    if not token_ids:
        return ""
    enc = get_encoder()
    if enc is None:
        return " ".join(token_ids)
    try:
        return enc.decode(token_ids)
    except Exception:
        logger.warning("tiktoken decode 실패.")
        return ""


# ---------------------------------------------------------
# 토큰 단위 슬라이싱 (실무형)
# ---------------------------------------------------------
def token_chunk(
    text: str,
    max_tokens: int = 500,
    overlap_tokens: int = 80
) -> List[str]:

    if not text or not text.strip():
        return []

    enc = get_encoder()
    if enc is None:
        # fallback: whitespace 단위 단순 슬라이스
        tokens = text.split()
    else:
        tokens = enc.encode(text)

    if max_tokens <= 0:
        max_tokens = 500
    if overlap_tokens < 0:
        overlap_tokens = 0
    if overlap_tokens >= max_tokens:
        overlap_tokens = max_tokens - 1

    # 짧으면 그대로
    if len(tokens) <= max_tokens:
        return [text.strip()]

    step = max_tokens - overlap_tokens
    if step <= 0:
        step = 1

    chunks = []

    for start in range(0, len(tokens), step):
        end = min(start + max_tokens, len(tokens))

        if enc is None:
            chunk_text = " ".join(tokens[start:end]).strip()
        else:
            chunk_text = enc.decode(tokens[start:end]).strip()

        if chunk_text:
            chunks.append(chunk_text)

        if end == len(tokens):
            break

    return chunks
