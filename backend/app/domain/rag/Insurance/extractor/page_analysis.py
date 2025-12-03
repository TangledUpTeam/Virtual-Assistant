"""
Insurance RAG PDF 추출 모듈 - 페이지 분석

페이지에서 텍스트, 표, 이미지를 감지하고 분석하는 모듈
Vision/LLM 호출 없이 순수하게 분석만 수행
"""

import fitz
import pdfplumber

from ..utils import get_logger
from .models import PageAnalysis
from .utils_processing import (
    detect_tables,
    detect_images,
    calculate_image_variance,
    calculate_image_area_ratio,
    MIN_IMAGE_VARIANCE
)

logger = get_logger(__name__)


def analyze_page(
    page: fitz.Page,
    pdfplumber_page: pdfplumber.page.Page,
    page_num: int
) -> PageAnalysis:
    """
    페이지 분석 (Vision/LLM 호출 없음)
    
    페이지에서 텍스트, 표, 이미지를 감지하고 분석 결과를 반환합니다.
    실제 Vision OCR이나 LLM 병합은 수행하지 않습니다.
    
    Args:
        page: PyMuPDF 페이지 객체
        pdfplumber_page: pdfplumber 페이지 객체
        page_num: 페이지 번호
        
    Returns:
        PageAnalysis: 페이지 분석 결과
    """
    # 1) raw_text 추출
    try:
        raw_text = page.get_text("text") or ""
    except Exception as e:
        logger.warning(f"페이지 {page_num} 텍스트 추출 실패: {e}")
        raw_text = ""
    
    # 2) 표 감지
    try:
        tables_data, table_bboxes = detect_tables(pdfplumber_page)
        has_tables = len(tables_data) > 0
    except Exception as e:
        logger.warning(f"페이지 {page_num} 표 감지 실패: {e}")
        tables_data = []
        table_bboxes = []
        has_tables = False
    
    # 3) 이미지 감지
    try:
        image_bboxes = detect_images(page)
        has_images = len(image_bboxes) > 0
    except Exception as e:
        logger.warning(f"페이지 {page_num} 이미지 감지 실패: {e}")
        image_bboxes = []
        has_images = False
    
    # 4) 이미지 variance, 면적 비율, meaningful_image 계산 (이미지가 있는 경우만)
    variance = None
    image_area_ratio = None
    meaningful_image = None
    if has_images:
        try:
            variance = calculate_image_variance(page)
        except Exception as e:
            logger.warning(f"페이지 {page_num} variance 계산 실패: {e}")
            variance = None
        
        try:
            image_area_ratio = calculate_image_area_ratio(page, image_bboxes)
        except Exception as e:
            logger.warning(f"페이지 {page_num} 이미지 면적 비율 계산 실패: {e}")
            image_area_ratio = None
        
        # meaningful_image 계산 (variance >= MIN_IMAGE_VARIANCE)
        if variance is not None:
            meaningful_image = variance >= MIN_IMAGE_VARIANCE
        else:
            meaningful_image = False
    
    return PageAnalysis(
        page_num=page_num,
        raw_text=raw_text,
        has_tables=has_tables,
        has_images=has_images,
        table_bboxes=table_bboxes,
        image_bboxes=image_bboxes,
        variance=variance,
        image_area_ratio=image_area_ratio,
        meaningful_image=meaningful_image,
        tables_data=tables_data if has_tables else []
    )

