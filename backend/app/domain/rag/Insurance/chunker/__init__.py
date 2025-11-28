"""
Insurance RAG 청킹 모듈

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

from .core import chunk_json, chunk_text_with_tokens, extract_page_content
from .splitter import pre_split_paragraphs
from .tokenizer import token_chunk, tokenize, detokenize
from .filters import is_ocr_failure_message, filter_chunk, OCR_FAILURE_INDICATORS, MIN_CHUNK_LENGTH

__all__ = [
    # Public API
    'chunk_json',
    'chunk_text_with_tokens',
    'extract_page_content',
    # Utilities
    'pre_split_paragraphs',
    'token_chunk',
    'tokenize',
    'detokenize',
    'is_ocr_failure_message',
    'filter_chunk',
    # Constants
    'OCR_FAILURE_INDICATORS',
    'MIN_CHUNK_LENGTH',
]

