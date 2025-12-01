"""
Insurance RAG PDF 추출 모듈 - 페이지 처리

페이지 분석 결과를 기반으로 Vision/LLM을 적용하여 최종 결과를 생성하는 모듈
"""

from typing import Literal

import fitz
from openai import OpenAI

from ..utils import get_logger
from .models import PageAnalysis, PageResult
from .utils_processing import (
    page_to_jpeg_data_url,
    tables_to_markdown,
    MIN_IMAGE_VARIANCE,
    MIN_IMAGE_AREA_RATIO
)
from .vision_client import vision_ocr, merge_with_llm, is_vision_failure

logger = get_logger(__name__)


def process_page(
    page: fitz.Page,
    analysis: PageAnalysis,
    client: OpenAI
) -> PageResult:
    """
    페이지 처리 (정책 결정 및 Vision/LLM 적용)
    
    PageAnalysis 결과를 기반으로 모드를 결정하고,
    필요시 Vision OCR 및 LLM 병합을 수행합니다.
    
    [처리 규칙]
    1. 빈 페이지 → "empty" 모드
    2. 표 있으면 → Vision OCR + merge_with_llm → "vision" 또는 "vision-fallback"
    3. 이미지 있으면 → 이미지 면적 비율 >= 10%일 때만 Vision 실행
    4. 그 외 → raw_text만 사용 → "text" 모드
    5. Vision 실패 시 fallback (raw_text 사용)
    
    Args:
        page: PyMuPDF 페이지 객체 (이미지 변환용)
        analysis: 페이지 분석 결과
        client: OpenAI 클라이언트 (의존성 주입)
        
    Returns:
        PageResult: 페이지 처리 최종 결과
    """
    # 1) 빈 페이지 판정
    if analysis.is_empty():
        return PageResult(
            page=analysis.page_num,
            mode="empty",
            content="",
            has_tables=False,
            has_images=False,
            table_bboxes=[],
            image_bboxes=[]
        )
    
    # 2) 모드 결정 및 처리
    content = ""
    mode: Literal["text", "vision", "vision-fallback", "error"] = "text"
    
    # Case 1: 표 있으면 무조건 Vision + merge_with_llm
    if analysis.has_tables:
        mode = "vision"
        try:
            jpeg_data_url = page_to_jpeg_data_url(page)
            vision_markdown = vision_ocr(jpeg_data_url, client)
            
            if is_vision_failure(vision_markdown):
                # Vision 실패 시 fallback
                mode = "vision-fallback"
                tables_md = tables_to_markdown(analysis.tables_data)
                content = analysis.raw_text + "\n\n" + tables_md if analysis.raw_text.strip() else tables_md
            else:
                # Vision 성공 시 merge_with_llm
                content = merge_with_llm(analysis.raw_text, vision_markdown, client)
        except Exception as e:
            # RULE 2: Vision OCR 예외 발생 시 fallback
            logger.error(f"페이지 {analysis.page_num} Vision OCR 실패: {str(e)}")
            mode = "vision-fallback"
            tables_md = tables_to_markdown(analysis.tables_data)
            content = analysis.raw_text + "\n\n" + tables_md if analysis.raw_text.strip() else tables_md
    
    # Case 2: 이미지만 있는 경우
    elif analysis.has_images:
        # 이미지 비율 & 의미 이미지 여부 로드
        image_area_ratio = analysis.image_area_ratio or 0.0
        meaningful_image = analysis.meaningful_image

        # Vision 실행 조건 (텍스트 길이 조건 완전 삭제)
        run_vision = (
            image_area_ratio >= 0.35    # 이미지가 페이지 면적의 35% 이상일 때만 Vision 실행
            and meaningful_image         # variance 기반 의미 이미지
        )

        logger.info(
            f"[Vision Trigger] page={analysis.page_num}  "
            f"ratio={image_area_ratio:.2%},  "
            f"meaningful={meaningful_image},  "
            f"run={run_vision}"
        )

        if run_vision:
            mode = "vision"
            try:
                jpeg_data_url = page_to_jpeg_data_url(page)
                vision_markdown = vision_ocr(jpeg_data_url, client)

                if is_vision_failure(vision_markdown):
                    mode = "vision-fallback"
                    content = analysis.raw_text or ""

                else:
                    content = merge_with_llm(analysis.raw_text, vision_markdown, client)

            except Exception as e:
                mode = "vision-fallback"
                content = analysis.raw_text or ""
                logger.error(f"페이지 {analysis.page_num} Vision OCR 실패: {str(e)}")

        else:
            # Vision 실행 조건 만족 못하면 raw_text만 사용
            mode = "text"
            content = analysis.raw_text
    
    # Case 3: 그 외는 raw_text만 사용
    else:
        mode = "text"
        content = analysis.raw_text
    
    # 3) 결과 반환
    return PageResult(
        page=analysis.page_num,
        mode=mode,
        content=content,
        has_tables=analysis.has_tables,
        has_images=analysis.has_images,
        table_bboxes=analysis.table_bboxes,
        image_bboxes=analysis.image_bboxes
    )

