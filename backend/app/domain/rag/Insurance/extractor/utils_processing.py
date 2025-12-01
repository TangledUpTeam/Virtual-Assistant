"""
Insurance RAG PDF 추출 모듈 - 저수준 처리 유틸리티

PDF 페이지 변환, 표/이미지 감지 등 저수준 처리 함수
"""

import base64
from typing import List, Tuple

import fitz
import pdfplumber
import numpy as np

from .models import BBox

# 상수 설정
DPI_FOR_VISION = 120
DPI_FOR_ANALYSIS = 50
MIN_IMAGE_VARIANCE = 250  # 50 → 250으로 상향 조정
MIN_IMAGE_AREA_RATIO = 0.10  # 이미지가 페이지 면적의 10% 이상일 때만 Vision 실행


def page_to_jpeg_data_url(page: fitz.Page, dpi: int = DPI_FOR_VISION) -> str:
    """
    PyMuPDF 페이지를 JPEG base64 data URL로 변환
    
    Note: PyMuPDF 1.23+ removed the quality parameter from tobytes()
    
    Args:
        page: PyMuPDF 페이지 객체
        dpi: 변환할 DPI (기본값: 120)
        
    Returns:
        base64 인코딩된 JPEG data URL
    """
    zoom = dpi / 72.0
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat)
    img_bytes = pix.tobytes("jpeg")
    b64 = base64.b64encode(img_bytes).decode("utf-8")
    return f"data:image/jpeg;base64,{b64}"


def page_to_gray_array(page: fitz.Page, dpi: int = DPI_FOR_ANALYSIS) -> np.ndarray:
    """
    페이지를 저해상도 그레이스케일 배열로 변환
    
    Args:
        page: PyMuPDF 페이지 객체
        dpi: 변환할 DPI (기본값: 50)
        
    Returns:
        그레이스케일 이미지 배열
    """
    zoom = dpi / 72.0
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat)
    img_array = np.frombuffer(pix.samples, dtype=np.uint8)
    img_array = img_array.reshape((pix.height, pix.width, pix.n))
    gray = np.mean(img_array, axis=2).astype(np.uint8)
    return gray


def detect_tables(
    pdfplumber_page: pdfplumber.page.Page
) -> Tuple[List[List[List[str]]], List[BBox]]:
    """
    표 감지
    
    Args:
        pdfplumber_page: pdfplumber 페이지 객체
        
    Returns:
        (표 데이터 리스트, 표 바운딩 박스 리스트) 튜플
    """
    try:
        tables_data = pdfplumber_page.extract_tables() or []
        detected_tables = pdfplumber_page.find_tables() or []
        table_bboxes = [
            BBox(
                x0=t.bbox[0],
                y0=t.bbox[1],
                x1=t.bbox[2],
                y1=t.bbox[3]
            )
            for t in detected_tables
        ]
        return tables_data, table_bboxes
    except Exception as e:
        # 예외 발생 시 빈 결과 반환 (로깅은 호출부에서 처리)
        return [], []


def detect_images(page: fitz.Page) -> List[BBox]:
    """
    이미지 감지
    
    Args:
        page: PyMuPDF 페이지 객체
        
    Returns:
        이미지 바운딩 박스 리스트
    """
    try:
        image_bboxes = []
        for img in page.get_images():
            xref = img[0]
            for rect in page.get_image_rects(xref):
                image_bboxes.append(BBox(
                    x0=rect.x0,
                    y0=rect.y0,
                    x1=rect.x1,
                    y1=rect.y1
                ))
        return image_bboxes
    except Exception as e:
        # 예외 발생 시 빈 결과 반환 (로깅은 호출부에서 처리)
        return []


def tables_to_markdown(tables: List[List[List[str]]]) -> str:
    """
    테이블을 Markdown으로 변환
    
    Args:
        tables: 표 데이터 리스트
        
    Returns:
        Markdown 형식의 테이블 문자열
    """
    md_list = []
    for table in tables:
        if not table:
            continue
        table = [[cell if cell is not None else "" for cell in row] for row in table]
        if not table:
            continue
        
        md = "| " + " | ".join(table[0]) + " |\n"
        md += "| " + " | ".join("---" for _ in table[0]) + " |\n"
        for row in table[1:]:
            md += "| " + " | ".join(row) + " |\n"
        md_list.append(md)
    return "\n\n".join(md_list)


def calculate_image_variance(page: fitz.Page) -> float:
    """
    이미지 variance 계산
    
    페이지 전체 grayscale variance를 계산하여 의미 있는 이미지 여부 판정에 사용
    
    Args:
        page: PyMuPDF 페이지 객체
        
    Returns:
        variance 값 (float)
    """
    try:
        gray = page_to_gray_array(page, DPI_FOR_ANALYSIS)
        variance = float(gray.var())
        return variance
    except Exception as e:
        # 오류 발생 시 안전하게 높은 값 반환 (Vision 처리하도록)
        return float('inf')


def calculate_image_area_ratio(page: fitz.Page, image_bboxes: List[BBox]) -> float:
    """
    이미지 총 면적 대비 페이지 면적 비율 계산
    
    Args:
        page: PyMuPDF 페이지 객체
        image_bboxes: 이미지 바운딩 박스 리스트
        
    Returns:
        float: 이미지 총 면적 / 페이지 면적 비율 (0.0 ~ 1.0)
    """
    if not image_bboxes:
        return 0.0
    
    try:
        # 페이지 면적 계산
        page_rect = page.rect
        page_area = page_rect.width * page_rect.height
        
        if page_area == 0:
            return 0.0
        
        # 이미지 총 면적 계산
        total_image_area = 0.0
        for bbox in image_bboxes:
            bbox_width = bbox.x1 - bbox.x0
            bbox_height = bbox.y1 - bbox.y0
            total_image_area += bbox_width * bbox_height
        
        # 비율 계산
        ratio = total_image_area / page_area
        return ratio
    except Exception as e:
        # 오류 발생 시 안전하게 0.0 반환 (Vision 실행하지 않음)
        return 0.0


def has_meaningful_image(page: fitz.Page, image_bboxes: List[BBox]) -> bool:
    """
    이미지 의미 판정 (variance + 면적 비율 기반)
    
    다음 두 조건을 모두 만족해야 True:
    1. variance >= MIN_IMAGE_VARIANCE (250)
    2. 이미지 총 면적 / 페이지 면적 >= MIN_IMAGE_AREA_RATIO (0.10)
    
    Args:
        page: PyMuPDF 페이지 객체
        image_bboxes: 이미지 바운딩 박스 리스트
        
    Returns:
        bool: 두 조건을 모두 만족하면 True
    """
    try:
        # 1) variance 체크
        variance = calculate_image_variance(page)
        variance_ok = variance >= MIN_IMAGE_VARIANCE
        
        # 2) 면적 비율 체크
        area_ratio = calculate_image_area_ratio(page, image_bboxes)
        area_ratio_ok = area_ratio >= MIN_IMAGE_AREA_RATIO
        
        # 두 조건 모두 만족해야 True
        return variance_ok and area_ratio_ok
    except Exception as e:
        # 오류 발생 시 안전하게 False 반환 (Vision 실행하지 않음)
        return False

