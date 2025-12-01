"""
Insurance RAG 청킹 모듈 단위 테스트

표 분할 방지 및 기본 청킹 로직 테스트
"""

import sys
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from app.domain.rag.Insurance.chunker.splitter import is_table_paragraph, pre_split_paragraphs


def test_is_table_paragraph():
    """마크다운 표 감지 테스트"""
    # 표 패턴
    table_text = """| Column A | Column B |
|----------|----------|
| Value 1  | Value 2  |"""
    
    assert is_table_paragraph(table_text) == True
    
    # 일반 텍스트
    normal_text = "This is just normal text without tables"
    assert is_table_paragraph(normal_text) == False


def test_table_not_split():
    """표가 분할되지 않는지 테스트"""
    text_with_table = """일반 텍스트입니다.

| A | B |
|---|---|
| 1 | 2 |
| 3 | 4 |

다른 텍스트입니다."""
    
    paragraphs = pre_split_paragraphs(text_with_table)
    
    # 표가 하나의 문단으로 유지되어야 함
    assert len(paragraphs) == 3
    
    # 두 번째 문단이 표여야 함
    assert "| A | B |" in paragraphs[1]
    assert "| 1 | 2 |" in paragraphs[1]


def test_multiple_tables_merged():
    """여러 표가 병합되는지 테스트"""
    text = """| A | B |
|---|---|
| 1 | 2 |

| C | D |
|---|---|
| 3 | 4 |"""
    
    paragraphs = pre_split_paragraphs(text)
    
    # 두 표가 하나로 병합되어야 함
    assert len(paragraphs) == 1
    assert "| A | B |" in paragraphs[0]
    assert "| C | D |" in paragraphs[0]


if __name__ == "__main__":
    test_is_table_paragraph()
    test_table_not_split()
    test_multiple_tables_merged()
    print("✅ All chunker tests passed!")
