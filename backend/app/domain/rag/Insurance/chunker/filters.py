"""
OCR 실패 감지 및 청크 필터링 모듈
"""

import re
from typing import List

# OCR 실패 indicator 목록 (extractor.py와 정확히 동일하게 유지)
OCR_FAILURE_INDICATORS: List[str] = [
    "i can't read",
    "i cannot read",
    "unable to transcribe",
    "cannot extract",
    "no readable text",
    "too blurry",
    "i'm sorry",
    "i'm sorry, i can't",
    "can't assist",
    "can't transcribe",
    "the image appears to be blank",
    "the image you provided is blank",
    "provide a different image",
    "check if the file is correct"
]

# 최소 청크 길이 (문자 단위)
MIN_CHUNK_LENGTH = 10


def is_ocr_failure_message(text: str) -> bool:
    """
    OCR 실패 메시지인지 확인
    
    - 길이로 판단하지 않고
    - '사과/실패' 계열 문구가 있을 때만 True
    
    Args:
        text: 확인할 텍스트
        
    Returns:
        bool: OCR 실패 메시지인 경우 True
    """
    if not text:
        return False
    
    text_lower = text.lower().strip()
    
    for indicator in OCR_FAILURE_INDICATORS:
        if indicator in text_lower:
            return True
    
    return False


def filter_chunk(chunk_text: str) -> bool:
    """
    청크가 유효한지 확인 (완화된 필터링)
    
    제거 조건:
    - 길이 < 10
    - OCR 실패 메시지
    - 공백/특수문자-only
    - "표", "그림", "페이지 N" 같은 단편적인 문장만 제거
    
    유지 조건 (구조적 정보):
    - "제 1 장", "제 2 절", "제 1 항" 같은 문서 구조 정보는 유지
    
    Args:
        chunk_text: 확인할 청크 텍스트
        
    Returns:
        bool: True면 유효, False면 제거
    """
    if not chunk_text:
        return False
    
    chunk_text = chunk_text.strip()
    
    # 최소 길이 검증
    if len(chunk_text) < MIN_CHUNK_LENGTH:
        return False
    
    # OCR 실패 메시지 검증
    if is_ocr_failure_message(chunk_text):
        return False
    
    # 공백만 포함된 경우
    if chunk_text.isspace():
        return False
    
    # 특수문자만 있는 경우 (한글/영문/숫자가 하나도 없으면 제외)
    if not re.search(r'[가-힣a-zA-Z0-9]', chunk_text):
        return False
    
    # 단편적 문장 패턴 제거 (구조적 정보는 유지)
    # "표", "그림", "페이지 N" 같은 단어만 있는 경우만 제거
    fragment_patterns = [
        r'^표\s*$',
        r'^그림\s*$',
        r'^페이지\s*\d+\s*$',
        r'^\d+\s*페이지\s*$',
    ]
    
    for pattern in fragment_patterns:
        if re.match(pattern, chunk_text, re.IGNORECASE):
            return False
    
    return True

