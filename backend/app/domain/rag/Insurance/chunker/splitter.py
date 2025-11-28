"""
문단 분할 모듈
"""

import re
from typing import List


def pre_split_paragraphs(text: str) -> List[str]:
    """
    텍스트를 문단 단위로 나눔 (청킹 전 pre-processing)
    
    안정적인 문단 분할 규칙:
    1. 이중 줄바꿈 (\n\n+)으로 기본 분할
    2. 제목 패턴 (#으로 시작하는 줄)
    3. 표 패턴 (|로 시작하는 줄)
    4. bullet 패턴 (-, •, *로 시작하는 줄)
    
    Args:
        text: 원본 텍스트
        
    Returns:
        문단 단위로 나뉜 텍스트 리스트
    """
    if not text or not text.strip():
        return []
    
    # 이중 줄바꿈으로 기본 분할
    paragraphs = re.split(r'\n\n+', text)
    
    result = []
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        
        # 제목 패턴: #으로 시작하는 줄
        if re.match(r'^#+\s+', para):
            result.append(para)
            continue
        
        # 표 패턴: |로 시작하거나 |---| 패턴이 있는 경우
        if re.search(r'^\s*\|', para, re.MULTILINE) or re.search(r'\|[\s-]+\|', para):
            result.append(para)
            continue
        
        # bullet 패턴: -, •, *로 시작하는 줄
        if re.match(r'^[-•*]\s+', para):
            result.append(para)
            continue
        
        # 일반 문단
        result.append(para)
    
    return result

