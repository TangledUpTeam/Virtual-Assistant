"""
문단 분할 모듈 (표 분할 방지 개선)
"""

import re
from typing import List


def is_table_paragraph(para: str) -> bool:
    """
    문단이 마크다운 표인지 판정
    
    마크다운 표 패턴:
    - |로 시작하는 줄이 2줄 이상
    - |---|--- 패턴 포함
    
    Args:
        para: 문단 텍스트
        
    Returns:
        bool: 표 여부
    """
    lines = para.split('\n')
    pipe_lines = [line for line in lines if line.strip().startswith('|')]
    
    # |로 시작하는 줄이 2줄 이상이고, |---| 패턴이 있으면 표로 판정
    has_separator = any(re.search(r'\|[\s-]+\|', line) for line in lines)
    
    return len(pipe_lines) >= 2 and has_separator


def pre_split_paragraphs(text: str) -> List[str]:
    """
    텍스트를 문단 단위로 나눔 (청킹 전 pre-processing)
    
    개선사항: 표 분할 방지 로직 강화
    
    안정적인 문단 분할 규칙:
    1. 이중 줄바꿈 (\\n\\n+)으로 기본 분할
    2. 제목 패턴 (#으로 시작하는 줄)
    3. 표 패턴 (|로 시작하는 줄) - 강화된 감지
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
    i = 0
    while i < len(paragraphs):
        para = paragraphs[i].strip()
        if not para:
            i += 1
            continue
        
        # 제목 패턴: #으로 시작하는 줄
        if re.match(r'^#+\s+', para):
            result.append(para)
            i += 1
            continue
        
        # 표 패턴: 여러 문단에 걸친 표를 하나로 병합
        if is_table_paragraph(para):
            table_parts = [para]
            # 다음 문단들도 표의 일부인지 확인
            j = i + 1
            while j < len(paragraphs):
                next_para = paragraphs[j].strip()
                if next_para and is_table_paragraph(next_para):
                    table_parts.append(next_para)
                    j += 1
                else:
                    break
            
            # 표 전체를 하나의 문단으로 병합
            result.append('\n\n'.join(table_parts))
            i = j
            continue
        
        # bullet 패턴: -, •, *로 시작하는 줄
        if re.match(r'^[-•*]\s+', para):
            result.append(para)
            i += 1
            continue
        
        # 일반 문단
        result.append(para)
        i += 1
    
    return result
