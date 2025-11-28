"""
Insurance RAG PDF 추출 모듈

Hybrid extractor: PyMuPDF + pdfplumber + Vision OCR fallback
보험 약관 PDF를 위한 추출기

[처리 규칙]
1. 모든 페이지는 raw_text 추출
2. 표 있으면 → Vision OCR + merge_with_llm
3. 이미지 있으면 → variance 체크 → 높으면 Vision + merge, 낮으면 raw_text만
4. 빈 페이지 처리
5. Vision 실패 시 fallback
"""

import json
import base64
from pathlib import Path
from typing import List, Dict, Any, Tuple
from threading import Lock

import fitz
import pdfplumber
import numpy as np
from tqdm import tqdm
from openai import OpenAI

from .config import insurance_config
from .utils import get_logger

logger = get_logger(__name__)


# ========================================
# 상수 설정
# ========================================

DPI_FOR_VISION = 120
DPI_FOR_ANALYSIS = 50

# Vision OCR 실패 indicator
OCR_FAILURE_INDICATORS = [
    "i can't read",
    "i cannot read",
    "unable to transcribe",
    "cannot extract",
    "no readable text",
    "the image appears to be blank",
    "provide a different image"
]

# 이미지 variance 기준
MIN_IMAGE_VARIANCE = 50


# ========================================
# OpenAI 클라이언트
# ========================================

_client = None
_client_lock = Lock()


def get_openai_client() -> OpenAI:
    """OpenAI 클라이언트 lazy loading"""
    global _client
    if _client is None:
        with _client_lock:
            if _client is None:
                _client = OpenAI(api_key=insurance_config.OPENAI_API_KEY)
                logger.info("OpenAI 클라이언트 초기화 완료")
    return _client


# ========================================
# 헬퍼 함수: 이미지 변환
# ========================================

def page_to_jpeg_data_url(page: fitz.Page, dpi: int = DPI_FOR_VISION) -> str:
    """PyMuPDF 페이지를 JPEG base64 data URL로 변환 (quality=90)"""
    zoom = dpi / 72.0
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat)
    img_bytes = pix.tobytes("jpeg", quality=90)
    b64 = base64.b64encode(img_bytes).decode("utf-8")
    return f"data:image/jpeg;base64,{b64}"


def page_to_gray_array(page: fitz.Page, dpi: int = DPI_FOR_ANALYSIS) -> np.ndarray:
    """페이지를 저해상도 그레이스케일 배열로 변환"""
    zoom = dpi / 72.0
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat)
    img_array = np.frombuffer(pix.samples, dtype=np.uint8)
    img_array = img_array.reshape((pix.height, pix.width, pix.n))
    gray = np.mean(img_array, axis=2).astype(np.uint8)
    return gray


# ========================================
# 테이블/이미지 감지 함수
# ========================================

def detect_tables(pdfplumber_page: pdfplumber.page.Page) -> Tuple[List[List[List[str]]], List[Dict[str, float]]]:
    """표 감지"""
    try:
        tables_data = pdfplumber_page.extract_tables() or []
        detected_tables = pdfplumber_page.find_tables() or []
        table_bboxes = [
            {"x0": t.bbox[0], "y0": t.bbox[1], "x1": t.bbox[2], "y1": t.bbox[3]}
            for t in detected_tables
        ]
        return tables_data, table_bboxes
    except Exception as e:
        logger.warning(f"표 감지 실패: {e}")
        return [], []


def detect_images(page: fitz.Page) -> List[Dict[str, float]]:
    """이미지 감지"""
    try:
        image_bboxes = []
        for img in page.get_images():
            xref = img[0]
            for rect in page.get_image_rects(xref):
                image_bboxes.append({
                    "x0": rect.x0, "y0": rect.y0,
                    "x1": rect.x1, "y1": rect.y1
                })
        return image_bboxes
    except Exception as e:
        logger.warning(f"이미지 감지 실패: {e}")
        return []


def tables_to_markdown(tables: List[List[List[str]]]) -> str:
    """테이블을 Markdown으로 변환"""
    md_list = []
    for table in tables:
        if not table or len(table) == 0:
            continue
        table = [[cell if cell is not None else "" for cell in row] for row in table]
        if len(table) == 0:
            continue
        
        md = "| " + " | ".join(table[0]) + " |\n"
        md += "| " + " | ".join("---" for _ in table[0]) + " |\n"
        for row in table[1:]:
            md += "| " + " | ".join(row) + " |\n"
        md_list.append(md)
    return "\n\n".join(md_list)


# ========================================
# 이미지 variance 판정
# ========================================

def has_meaningful_image(page: fitz.Page) -> bool:
    """
    이미지 variance 기반 판정
    
    페이지 전체 grayscale variance를 계산하여 의미 있는 이미지 여부 판정
    
    Returns:
        bool: variance >= threshold 이면 True
    """
    try:
        gray = page_to_gray_array(page, DPI_FOR_ANALYSIS)
        variance = float(gray.var())
        return variance >= MIN_IMAGE_VARIANCE
    except Exception as e:
        logger.warning(f"이미지 variance 계산 실패: {e}")
        return True  # 안전하게 True 반환


# ========================================
# Vision OCR 함수
# ========================================

def is_vision_failure(text: str) -> bool:
    """Vision OCR 실패 판정"""
    if not text:
        return True
    
    text_lower = text.lower()
    for indicator in OCR_FAILURE_INDICATORS:
        if indicator in text_lower:
            return True
    
    if len(text.strip()) < 10:
        return True
    
    return False


def vision_ocr(jpeg_data_url: str) -> str:
    """Vision API OCR"""
    client = get_openai_client()
    
    prompt = (
        "You are an expert OCR and document formatter for Korean insurance manuals.\n"
        "Read the page image and output a clean, well-structured Markdown representation.\n"
        "- Preserve headings, bullet points, tables.\n"
        "- Only transcribe; do not add any explanation.\n"
    )
    
    try:
        resp = client.chat.completions.create(
            model=insurance_config.OPENAI_VISION_MODEL,
            temperature=0,
            max_tokens=2000,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": jpeg_data_url}}
                ]
            }]
        )
        return resp.choices[0].message.content or ""
    except Exception as e:
        logger.error(f"Vision OCR 실패: {e}")
        raise


# ========================================
# LLM 병합 함수
# ========================================

def merge_with_llm(raw_text: str, vision_markdown: str) -> str:
    """
    Vision OCR 결과와 raw_text를 LLM으로 병합
    
    Args:
        raw_text: PyMuPDF로 추출한 원문 텍스트
        vision_markdown: Vision OCR로 추출한 Markdown 텍스트
        
    Returns:
        병합된 Markdown 형식의 텍스트
    """
    client = get_openai_client()
    
    prompt = """당신은 보험약관 문서를 재구성하는 전문가입니다.

아래 두 개의 출처에서 추출한 텍스트를 합쳐
중복된 문장/문단/표는 하나로 통합하고,
구조가 자연스럽고 잘 정리된 Markdown 형태로 정리해주세요.

규칙:
- 동일하거나 유사한 내용은 하나로만 유지합니다.
- Vision OCR 특유의 오탈자는 raw_text 내용을 우선합니다.
- 표는 Vision OCR의 Markdown 테이블 형식을 우선합니다.
- 원래 문서의 논리 구조(제목 → 내용 → 표 → 내용)를 유지해주세요.
- 생성하지 말고, 주어진 내용만 재구성하세요.

아래는 두 가지 입력입니다.

[TEXT MODE EXTRACTED]
{raw_text}

[VISION OCR]
{vision_markdown}""".format(
        raw_text=raw_text if raw_text.strip() else "(텍스트 없음)",
        vision_markdown=vision_markdown if vision_markdown.strip() else "(Vision OCR 결과 없음)"
    )
    
    try:
        resp = client.chat.completions.create(
            model=insurance_config.OPENAI_MODEL,
            temperature=0,
            max_tokens=insurance_config.OPENAI_MAX_TOKENS,
            messages=[{
                "role": "user",
                "content": prompt
            }]
        )
        result = resp.choices[0].message.content or ""
        logger.debug(f"LLM 병합 완료: {len(result)}자 생성")
        return result
    except Exception as e:
        logger.error(f"LLM 병합 중 오류 발생: {e}")
        # 오류 발생 시 Vision 결과를 우선 사용
        return vision_markdown if vision_markdown.strip() else raw_text


# ========================================
# 페이지 처리 함수
# ========================================

def process_page(
    page: fitz.Page,
    pdfplumber_page: pdfplumber.page.Page,
    page_num: int
) -> Dict[str, Any]:
    """
    단일 페이지 처리
    
    [처리 규칙]
    1. raw_text 추출
    2. 표 있으면 → Vision + merge_with_llm
    3. 이미지 있으면 → variance 체크 → 높으면 Vision + merge, 낮으면 raw_text만
    4. 빈 페이지 처리
    5. Vision 실패 시 fallback
    """
    # 1) raw_text 추출
    try:
        raw_text = page.get_text("text") or ""
    except Exception as e:
        logger.warning(f"페이지 {page_num} 텍스트 추출 실패: {e}")
        raw_text = ""
    
    # 2) 표 감지
    tables_data, table_bboxes = detect_tables(pdfplumber_page)
    has_tables = len(tables_data) > 0
    
    # 3) 이미지 감지
    image_bboxes = detect_images(page)
    has_images = len(image_bboxes) > 0
    
    # 4) 빈 페이지 판정
    if raw_text.strip() == "" and not has_tables and not has_images:
        return {
            "page": page_num,
            "mode": "empty",
            "content": "",
            "has_tables": False,
            "has_images": False,
            "table_bboxes": [],
            "image_bboxes": []
        }
    
    # 5) 모드 결정 및 처리
    content = ""
    mode = "text"
    
    # Case 1: 표 있으면 무조건 Vision + merge_with_llm
    if has_tables:
        mode = "vision"
        try:
            jpeg_data_url = page_to_jpeg_data_url(page, DPI_FOR_VISION)
            vision_markdown = vision_ocr(jpeg_data_url)
            
            if is_vision_failure(vision_markdown):
                # Vision 실패 시 fallback
                mode = "vision-fallback"
                tables_md = tables_to_markdown(tables_data)
                content = raw_text + "\n\n" + tables_md if raw_text.strip() else tables_md
            else:
                # Vision 성공 시 merge_with_llm
                content = merge_with_llm(raw_text, vision_markdown)
        except Exception as e:
            logger.error(f"페이지 {page_num} Vision OCR 실패: {e}")
            mode = "vision-fallback"
            tables_md = tables_to_markdown(tables_data)
            content = raw_text + "\n\n" + tables_md if raw_text.strip() else tables_md
    
    # Case 2: 이미지만 있는 경우
    elif has_images:
        # variance 체크
        if has_meaningful_image(page):
            # variance 높으면 Vision + merge_with_llm
            mode = "vision"
            try:
                jpeg_data_url = page_to_jpeg_data_url(page, DPI_FOR_VISION)
                vision_markdown = vision_ocr(jpeg_data_url)
                
                if is_vision_failure(vision_markdown):
                    # Vision 실패 시 fallback
                    mode = "vision-fallback"
                    content = raw_text
                else:
                    # Vision 성공 시 merge_with_llm
                    content = merge_with_llm(raw_text, vision_markdown)
            except Exception as e:
                logger.error(f"페이지 {page_num} Vision OCR 실패: {e}")
                mode = "vision-fallback"
                content = raw_text
        else:
            # variance 낮으면 raw_text만 사용
            mode = "text"
            content = raw_text
    
    # Case 3: 그 외는 raw_text만 사용
    else:
        mode = "text"
        content = raw_text
    
    # 6) 결과 반환
    return {
        "page": page_num,
        "mode": mode,
        "content": content,
        "has_tables": has_tables,
        "has_images": has_images,
        "table_bboxes": table_bboxes,
        "image_bboxes": image_bboxes
    }


# ========================================
# 메인 Extract 함수
# ========================================

def extract_pdf(pdf_path: str, max_workers: int = 4) -> Path:
    """
    PDF 파일 추출 (순차 처리)
    
    Args:
        pdf_path: PDF 파일 경로
        max_workers: 사용하지 않음 (순차 처리)
        
    Returns:
        Path: 생성된 JSON 파일 경로
    """
    pdf_path = Path(pdf_path)
    
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF 파일을 찾을 수 없습니다: {pdf_path}")
    
    logger.info(f"PDF 추출 시작: {pdf_path.name}")
    
    out_json_path = insurance_config.PROCESSED_DIR / f"{pdf_path.stem}.json"
    
    try:
        # PDF 열기
        doc = fitz.open(pdf_path)
        plumber_pdf = pdfplumber.open(pdf_path)
        
        total_pages = len(doc)
        logger.info(f"총 {total_pages}페이지 처리 시작")
        
        # 순차 처리
        pages_output = []
        
        for i in tqdm(range(total_pages), desc=f"Extracting {pdf_path.name}"):
            page = doc[i]
            plumber_page = plumber_pdf.pages[i]
            page_num = i + 1
            
            try:
                page_info = process_page(page, plumber_page, page_num)
                pages_output.append(page_info)
            except Exception as e:
                logger.error(f"페이지 {page_num} 처리 중 오류: {e}")
                # 오류 발생 시 빈 페이지 정보 저장
                pages_output.append({
                    "page": page_num,
                    "mode": "error",
                    "content": "",
                    "has_tables": False,
                    "has_images": False,
                    "table_bboxes": [],
                    "image_bboxes": []
                })
        
        # PDF 닫기
        doc.close()
        plumber_pdf.close()
        
        # JSON 저장
        result = {
            "file": str(pdf_path),
            "total_pages": len(pages_output),
            "pages": pages_output,
        }
        
        with open(out_json_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        logger.info(f"PDF 추출 완료: {out_json_path} ({len(pages_output)}페이지)")
        return out_json_path
        
    except Exception as e:
        logger.exception(f"PDF 추출 중 오류 발생: {e}")
        raise
