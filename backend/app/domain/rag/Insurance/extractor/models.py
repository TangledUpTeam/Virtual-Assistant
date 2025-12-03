"""
Insurance RAG PDF 추출 모듈 - 데이터 모델

페이지 분석 및 처리 결과를 나타내는 dataclass 정의
"""

from dataclasses import dataclass, field
from typing import List, Literal, Optional


@dataclass
class BBox:
    """바운딩 박스 (테이블/이미지 위치 정보)"""
    x0: float
    y0: float
    x1: float
    y1: float
    
    def to_dict(self) -> dict:
        """딕셔너리로 변환"""
        return {
            "x0": self.x0,
            "y0": self.y0,
            "x1": self.x1,
            "y1": self.y1
        }


@dataclass
class PageAnalysis:
    """
    페이지 분석 결과
    
    Vision/LLM 호출 없이 순수하게 페이지에서 추출한 정보만 포함
    """
    page_num: int
    raw_text: str
    has_tables: bool
    has_images: bool
    table_bboxes: List[BBox]
    image_bboxes: List[BBox]
    variance: Optional[float] = None
    image_area_ratio: Optional[float] = None  # 이미지 총 면적 / 페이지 면적 비율
    meaningful_image: Optional[bool] = None  # variance 기반 의미 이미지 여부
    tables_data: List[List[List[str]]] = field(default_factory=list)  # vision-fallback 시 사용
    
    def is_empty(self) -> bool:
        """빈 페이지 여부 판정"""
        return (
            not self.raw_text.strip() 
            and not self.has_tables 
            and not self.has_images
        )


@dataclass
class PageResult:
    """
    페이지 처리 최종 결과
    
    Vision/LLM 처리까지 완료된 최종 결과
    """
    page: int
    mode: Literal["empty", "text", "vision", "vision-fallback", "error"]
    content: str
    has_tables: bool
    has_images: bool
    table_bboxes: List[BBox]
    image_bboxes: List[BBox]
    
    def to_dict(self) -> dict:
        """JSON 저장을 위한 딕셔너리로 변환"""
        return {
            "page": self.page,
            "mode": self.mode,
            "content": self.content,
            "has_tables": self.has_tables,
            "has_images": self.has_images,
            "table_bboxes": [bbox.to_dict() for bbox in self.table_bboxes],
            "image_bboxes": [bbox.to_dict() for bbox in self.image_bboxes]
        }

