"""
Insurance RAG 페이지 처리 모듈 단위 테스트

Mock을 사용한 페이지 처리 로직 테스트 (OpenAI 호출 없음)
"""

import sys
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from app.domain.rag.Insurance.extractor.models import PageAnalysis, BBox
from app.domain.rag.Insurance.extractor.page_processor import process_page


class MockPage:
    """Mock PyMuPDF Page"""
    pass


class MockClient:
    """Mock OpenAI Client"""
    class ChatCompletions:
        class Choice:
            class Message:
                def __init__(self, content):
                    self.content = content
            
            def __init__(self, content):
                self.message = self.Message(content)
        
        class Response:
            def __init__(self, content):
                self.choices = [MockClient.ChatCompletions.Choice(content)]
        
        def create(self, **kwargs):
            # Vision OCR mock
            if "image_url" in str(kwargs):
                return self.Response("MOCK VISION TEXT")
            # LLM merge mock
            else:
                return self.Response("MERGED TEXT")
    
    def __init__(self):
        self.chat = type('obj', (object,), {
            'completions': self.ChatCompletions()
        })()


def test_text_only_mode():
    """텍스트만 있는 페이지 처리 테스트"""
    mock_page = MockPage()
    mock_client = MockClient()
    
    analysis = PageAnalysis(
        page_num=1,
        raw_text="hello world",
        has_tables=False,
        has_images=False,
        table_bboxes=[],
        image_bboxes=[],
        variance=None,
        image_area_ratio=None,
        meaningful_image=None,
        tables_data=[]
    )
    
    result = process_page(mock_page, analysis, mock_client)
    
    assert result.mode == "text"
    assert "hello" in result.content
    assert result.has_tables == False
    assert result.has_images == False


def test_empty_page():
    """빈 페이지 처리 테스트"""
    mock_page = MockPage()
    mock_client = MockClient()
    
    analysis = PageAnalysis(
        page_num=2,
        raw_text="",
        has_tables=False,
        has_images=False,
        table_bboxes=[],
        image_bboxes=[],
        variance=None,
        image_area_ratio=None,
        meaningful_image=None,
        tables_data=[]
    )
    
    result = process_page(mock_page, analysis, mock_client)
    
    assert result.mode == "empty"
    assert result.content == ""


if __name__ == "__main__":
    test_text_only_mode()
    test_empty_page()
    print("✅ All page processor tests passed!")
