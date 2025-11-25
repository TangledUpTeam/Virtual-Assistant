"""
Insurance RAG PDF 추출 모듈

Hybrid extractor: PyMuPDF + pdfplumber + Vision OCR fallback
보험 약관 PDF를 위한 새로운 프로토타입 구현
"""

import os
import io
import json
import base64
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

import fitz
import pdfplumber
from PIL import Image
from tqdm import tqdm
from openai import OpenAI

from .config import insurance_config
from .utils import get_logger

logger = get_logger(__name__)


# 상수 설정
MIN_TEXT_CHARS_FOR_TEXT_MODE = 40
DPI_FOR_VISION = 200


# OpenAI 클라이언트는 함수 내에서 lazy loading
_client = None


def get_openai_client() -> OpenAI:
    """OpenAI 클라이언트 lazy loading"""
    global _client
    if _client is None:
        _client = OpenAI(api_key=insurance_config.OPENAI_API_KEY)
        logger.info("OpenAI Vision 클라이언트 초기화 완료")
    return _client


# ========================================
# 헬퍼 함수: 이미지 변환
# ========================================

def page_to_pil(page: fitz.Page, dpi: int = DPI_FOR_VISION) -> Image.Image:
    """
    PyMuPDF 페이지를 PIL Image로 변환
    
    Args:
        page: PyMuPDF Page 객체
        dpi: 렌더링 해상도
        
    Returns:
        PIL Image 객체
    """
    zoom = dpi / 72.0
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat)
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    return img


def pil_to_data_url(image: Image.Image) -> str:
    """
    PIL Image를 base64 data URL로 변환
    
    Args:
        image: PIL Image 객체
        
    Returns:
        base64 data URL 문자열
    """
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    img_bytes = buf.getvalue()
    b64 = base64.b64encode(img_bytes).decode("utf-8")
    return f"data:image/png;base64,{b64}"


# ========================================
# 테이블 처리 함수
# ========================================

def tables_to_markdown(tables: List[List[List[str]]]) -> List[str]:
    """
    테이블 데이터를 Markdown 형식으로 변환
    
    Args:
        tables: pdfplumber extract_tables() 결과
        
    Returns:
        Markdown 형식 테이블 리스트
    """
    md_tables = []
    for table in tables:
        if not table or len(table) == 0:
            continue
        
        # None 값을 빈 문자열로 변환
        table = [[cell if cell is not None else "" for cell in row] for row in table]
        
        if len(table) == 0:
            continue
            
        header = table[0]
        body = table[1:] if len(table) > 1 else []
        
        # Markdown 테이블 생성
        md = ""
        md += "| " + " | ".join(header) + " |\n"
        md += "| " + " | ".join("---" for _ in header) + " |\n"
        for row in body:
            md += "| " + " | ".join(row) + " |\n"
        
        md_tables.append(md)
    
    return md_tables


def detect_tables(pdfplumber_page: pdfplumber.page.Page) -> Tuple[List[List[List[str]]], List[Dict[str, float]]]:
    """
    pdfplumber를 사용하여 페이지에서 표 감지
    
    Args:
        pdfplumber_page: pdfplumber Page 객체
        
    Returns:
        (tables_data, table_bboxes) 튜플
        - tables_data: extract_tables() 결과 (셀 데이터)
        - table_bboxes: find_tables() 결과의 bbox 리스트
    """
    try:
        # 표 데이터 추출
        tables_data = pdfplumber_page.extract_tables() or []
        
        # 표 bbox 감지
        detected_tables = pdfplumber_page.find_tables() or []
        table_bboxes = []
        
        for table in detected_tables:
            bbox = table.bbox
            # bbox는 (x0, top, x1, bottom) 형식
            table_bboxes.append({
                "x0": bbox[0],
                "y0": bbox[1],
                "x1": bbox[2],
                "y1": bbox[3]
            })
        
        return tables_data, table_bboxes
        
    except Exception as e:
        logger.warning(f"표 감지 중 오류: {e}")
        return [], []


# ========================================
# 이미지 감지 함수
# ========================================

def detect_images(page: fitz.Page) -> List[Dict[str, float]]:
    """
    PyMuPDF를 사용하여 페이지에서 이미지 감지
    
    Args:
        page: PyMuPDF Page 객체
        
    Returns:
        이미지 bbox 리스트
    """
    try:
        image_bboxes = []
        
        # 페이지의 모든 이미지 xref 가져오기
        image_list = page.get_images()
        
        for img_index, img in enumerate(image_list):
            xref = img[0]  # 이미지 xref 번호
            
            # 이미지의 bbox 리스트 가져오기 (같은 이미지가 여러 번 사용될 수 있음)
            try:
                rects = page.get_image_rects(xref)
                for rect in rects:
                    # fitz.Rect를 dict로 변환
                    image_bboxes.append({
                        "x0": rect.x0,
                        "y0": rect.y0,
                        "x1": rect.x1,
                        "y1": rect.y1
                    })
            except Exception as e:
                logger.debug(f"이미지 {img_index} bbox 추출 실패: {e}")
                continue
        
        return image_bboxes
        
    except Exception as e:
        logger.warning(f"이미지 감지 중 오류: {e}")
        return []


# ========================================
# 이미지 렌더링 및 crop 함수
# ========================================

def render_page_to_image(page: fitz.Page, dpi: int = DPI_FOR_VISION) -> Image.Image:
    """
    페이지 전체를 PIL Image로 렌더링
    
    Args:
        page: PyMuPDF Page 객체
        dpi: 렌더링 해상도
        
    Returns:
        PIL Image 객체
    """
    return page_to_pil(page, dpi)


def crop_region(image: Image.Image, bbox: Dict[str, float], page_width: float, page_height: float) -> Optional[Image.Image]:
    """
    이미지에서 특정 영역을 crop
    
    Args:
        image: 전체 페이지 이미지
        bbox: crop할 영역 (x0, y0, x1, y1)
        page_width: 페이지 너비 (PDF 좌표)
        page_height: 페이지 높이 (PDF 좌표)
        
    Returns:
        Crop된 PIL Image 또는 None
    """
    try:
        img_width, img_height = image.size
        
        # PDF 좌표를 이미지 픽셀 좌표로 변환
        x0_px = int((bbox["x0"] / page_width) * img_width)
        y0_px = int((bbox["y0"] / page_height) * img_height)
        x1_px = int((bbox["x1"] / page_width) * img_width)
        y1_px = int((bbox["y1"] / page_height) * img_height)
        
        # 좌표 검증
        x0_px = max(0, min(x0_px, img_width))
        y0_px = max(0, min(y0_px, img_height))
        x1_px = max(x0_px, min(x1_px, img_width))
        y1_px = max(y0_px, min(y1_px, img_height))
        
        if x1_px <= x0_px or y1_px <= y0_px:
            logger.warning(f"잘못된 bbox: {bbox}")
            return None
        
        # Crop
        cropped = image.crop((x0_px, y0_px, x1_px, y1_px))
        return cropped
        
    except Exception as e:
        logger.warning(f"이미지 crop 실패: {e}")
        return None


# ========================================
# Vision API 함수
# ========================================

def vision_ocr(image: Image.Image) -> str:
    """
    Vision API를 사용한 OCR 및 Markdown 변환
    
    Args:
        image: PIL Image 객체
        
    Returns:
        Markdown 형식의 텍스트
    """
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
                    {"type": "image_url", "image_url": {"url": pil_to_data_url(image)}}
                ]
            }]
        )
        result = resp.choices[0].message.content or ""
        logger.debug(f"Vision OCR 완료: {len(result)}자 추출")
        return result
        
    except Exception as e:
        logger.error(f"Vision OCR 중 오류 발생: {e}")
        raise


# ========================================
# 페이지 처리 함수
# ========================================

def process_page(
    page: fitz.Page,
    pdfplumber_page: pdfplumber.page.Page,
    page_num: int,
    pdf_name: str,
    output_image_dir: Path
) -> Dict[str, Any]:
    """
    단일 페이지 처리 (표 감지, 이미지 감지, 모드 결정, 추출)
    
    Args:
        page: PyMuPDF Page 객체
        pdfplumber_page: pdfplumber Page 객체
        page_num: 페이지 번호
        pdf_name: PDF 파일명 (확장자 제외)
        output_image_dir: 이미지 저장 디렉토리
        
    Returns:
        페이지 정보 딕셔너리
    """
    # 1) 텍스트 길이 측정
    try:
        raw_text = page.get_text("text") or ""
        text_length = len(raw_text.strip())
    except Exception as e:
        logger.warning(f"페이지 {page_num} 텍스트 추출 실패: {e}")
        raw_text = ""
        text_length = 0
    
    # 2) 표 감지
    tables_data, table_bboxes = detect_tables(pdfplumber_page)
    tables_md = tables_to_markdown(tables_data) if tables_data else []
    has_tables = len(tables_data) > 0
    
    # 3) 이미지 감지
    image_bboxes = detect_images(page)
    has_images = len(image_bboxes) > 0
    
    # 4) 모드 결정
    # TEXT_MODE: 텍스트 충분 & 표 없음 & 이미지 없음
    # VISION_MODE: 그 외 모든 경우
    # 주의: 텍스트가 비어있거나 공백만 있는 경우는 VISION_MODE로 처리
    if text_length >= MIN_TEXT_CHARS_FOR_TEXT_MODE and not has_tables and not has_images and raw_text.strip():
        mode = "text"
    else:
        mode = "vision"
        if text_length < MIN_TEXT_CHARS_FOR_TEXT_MODE:
            logger.debug(f"페이지 {page_num}: Vision 모드 (텍스트 부족: {text_length}자 < {MIN_TEXT_CHARS_FOR_TEXT_MODE}자)")
        elif has_tables or has_images:
            logger.debug(f"페이지 {page_num}: Vision 모드 (표/이미지 존재: 표={has_tables}, 이미지={has_images})")
        else:
            logger.debug(f"페이지 {page_num}: Vision 모드 (텍스트가 비어있거나 공백만 존재)")
    
    # 5) 페이지 정보 초기화
    page_info: Dict[str, Any] = {
        "page": page_num,
        "mode": mode,
        "text": "",
        "vision_markdown": "",
        "tables_markdown": [],
        "table_bboxes": table_bboxes,
        "image_bboxes": image_bboxes,
        "table_images": [],
        "page_images": []
    }
    
    # 6) 모드별 처리
    if mode == "text":
        # TEXT_MODE: 텍스트 추출 + 표 마크다운
        # 빈 텍스트인 경우도 처리 (이 경우 청크 생성 시 필터링됨)
        page_info["text"] = raw_text if raw_text.strip() else ""
        
        if tables_md:
            page_info["tables_markdown"] = tables_md
            logger.debug(f"페이지 {page_num}: TEXT 모드, 표 {len(tables_md)}개 포함")
        
        # 텍스트가 비어있는 경우 경고
        if not raw_text.strip():
            logger.warning(f"페이지 {page_num}: TEXT 모드이지만 텍스트가 비어있음 (빈 페이지 가능성)")
        
        # 이미지 bbox는 JSON에 기록만 (crop 안 함)
        
    else:
        # VISION_MODE: Vision OCR + 표/이미지 crop 및 저장
        try:
            # 페이지 전체 이미지 렌더링
            page_image = render_page_to_image(page)
            page_rect = page.rect
            page_width = page_rect.width
            page_height = page_rect.height
            
            # Vision API로 전체 페이지 OCR
            vision_text = vision_ocr(page_image)
            page_info["vision_markdown"] = vision_text
            
            # 페이지별 이미지 저장 디렉토리 생성
            page_image_dir = output_image_dir / f"page_{page_num}"
            page_image_dir.mkdir(parents=True, exist_ok=True)
            
            # 표 영역 crop 및 저장
            table_image_paths = []
            for i, table_bbox in enumerate(table_bboxes):
                cropped_table = crop_region(page_image, table_bbox, page_width, page_height)
                if cropped_table:
                    table_image_path = page_image_dir / f"table_{i+1}.png"
                    cropped_table.save(table_image_path, format="PNG")
                    # 상대 경로 저장 (processed/pdf_name/page_x/table_i.png)
                    rel_path = f"{pdf_name}/page_{page_num}/table_{i+1}.png"
                    table_image_paths.append(rel_path)
                    logger.debug(f"페이지 {page_num}: 표 {i+1} 저장: {rel_path}")
            
            page_info["table_images"] = table_image_paths
            
            # 이미지 영역 crop 및 저장
            page_image_paths = []
            for i, image_bbox in enumerate(image_bboxes):
                cropped_img = crop_region(page_image, image_bbox, page_width, page_height)
                if cropped_img:
                    img_image_path = page_image_dir / f"img_{i+1}.png"
                    cropped_img.save(img_image_path, format="PNG")
                    # 상대 경로 저장
                    rel_path = f"{pdf_name}/page_{page_num}/img_{i+1}.png"
                    page_image_paths.append(rel_path)
                    logger.debug(f"페이지 {page_num}: 이미지 {i+1} 저장: {rel_path}")
            
            page_info["page_images"] = page_image_paths
            
            logger.debug(f"페이지 {page_num}: VISION 모드 완료 (표 {len(table_image_paths)}개, 이미지 {len(page_image_paths)}개)")
            
        except Exception as e:
            logger.error(f"페이지 {page_num} VISION 모드 처리 실패: {e}")
            page_info["vision_markdown"] = ""
    
    return page_info


# ========================================
# 메인 Extract 함수 (외부 인터페이스 유지)
# ========================================

def extract_pdf(pdf_path: str) -> Path:
    """
    PDF 파일을 추출하여 JSON 형식으로 저장
    
    외부 인터페이스는 기존과 동일하게 유지:
    - 함수명: extract_pdf(pdf_path: str)
    - 반환: Path (생성된 JSON 파일 경로)
    - JSON 구조: {"file": str, "total_pages": int, "pages": [...]}
    
    Args:
        pdf_path: PDF 파일 경로
        
    Returns:
        Path: 생성된 JSON 파일 경로
    """
    pdf_path = Path(pdf_path)
    
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF 파일을 찾을 수 없습니다: {pdf_path}")
    
    logger.info(f"PDF 추출 시작: {pdf_path.name}")
    
    # 출력 JSON 경로
    out_json_path = insurance_config.PROCESSED_DIR / f"{pdf_path.stem}.json"
    
    # 이미지 저장 디렉토리 (processed/pdf_name/)
    pdf_name = pdf_path.stem
    output_image_dir = insurance_config.PROCESSED_DIR / pdf_name
    
    try:
        # PDF 열기
        doc = fitz.open(pdf_path)
        plumber_pdf = pdfplumber.open(pdf_path)
        
        total_pages = len(doc)
        logger.info(f"총 {total_pages}페이지 처리 시작")
        
        pages_output = []
        
        # 각 페이지 처리
        for i in tqdm(range(total_pages), desc=f"Extracting {pdf_path.name}"):
            page_num = i + 1
            page = doc[i]
            plumber_page = plumber_pdf.pages[i]
            
            # 페이지 처리 (새로운 파이프라인)
            page_info = process_page(
                page=page,
                pdfplumber_page=plumber_page,
                page_num=page_num,
                pdf_name=pdf_name,
                output_image_dir=output_image_dir
            )
            
            pages_output.append(page_info)
        
        # PDF 닫기
        doc.close()
        plumber_pdf.close()
        
        # 결과 JSON 저장
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
