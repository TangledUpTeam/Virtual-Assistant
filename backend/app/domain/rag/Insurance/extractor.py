"""
Insurance RAG PDF 추출 모듈

Hybrid extractor: PyMuPDF + pdfplumber + Vision OCR fallback
"""

import os
import io
import json
import base64
from pathlib import Path

import fitz
import pdfplumber
from PIL import Image
from tqdm import tqdm
from openai import OpenAI

from .config import insurance_config
from .utils import get_logger

logger = get_logger(__name__)


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


# -----------------------------------------
# 테이블 → Markdown
# -----------------------------------------
def tables_to_markdown(tables):
    md_tables = []
    for table in tables:
        if not table:
            continue
        table = [[cell if cell is not None else "" for cell in row] for row in table]
        header = table[0]
        body = table[1:] if len(table) > 1 else []

        md = ""
        md += "| " + " | ".join(header) + " |\n"
        md += "| " + " | ".join("---" for _ in header) + " |\n"
        for row in body:
            md += "| " + " | ".join(row) + " |\n"

        md_tables.append(md)
    return md_tables


def page_to_pil(page, dpi=DPI_FOR_VISION) -> Image.Image:
    zoom = dpi / 72.0
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat)
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    return img


def pil_to_data_url(image: Image.Image) -> str:
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    img_bytes = buf.getvalue()
    b64 = base64.b64encode(img_bytes).decode("utf-8")
    return f"data:image/png;base64,{b64}"


def vision_ocr_markdown(image: Image.Image) -> str:
    """
    Vision API를 사용한 OCR 및 Markdown 변환
    
    Args:
        image: PIL Image 객체
        
    Returns:
        str: Markdown 형식의 텍스트
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


# -----------------------------------------
# 메인 Extract 함수
# -----------------------------------------
def extract_pdf(pdf_path: str) -> Path:
    """
    PDF 파일을 추출하여 JSON 형식으로 저장
    
    Args:
        pdf_path: PDF 파일 경로
        
    Returns:
        Path: 생성된 JSON 파일 경로
    """
    pdf_path = Path(pdf_path)
    
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF 파일을 찾을 수 없습니다: {pdf_path}")
    
    logger.info(f"PDF 추출 시작: {pdf_path.name}")
    
    out_json_path = insurance_config.PROCESSED_DIR / f"{pdf_path.stem}.json"

    try:
        doc = fitz.open(pdf_path)
        plumber_pdf = pdfplumber.open(pdf_path)
        
        total_pages = len(doc)
        logger.info(f"총 {total_pages}페이지 처리 시작")

        pages_output = []

        for i in tqdm(range(total_pages), desc=f"Extracting {pdf_path.name}"):
            page_num = i + 1
            page = doc[i]

            # 1) 텍스트 추출
            try:
                raw_text = page.get_text("text") or ""
            except Exception as e:
                logger.warning(f"페이지 {page_num} 텍스트 추출 실패: {e}")
                raw_text = ""

            text_len = len(raw_text.strip())

            # 2) 표 추출
            try:
                pl_page = plumber_pdf.pages[i]
                tables_raw = pl_page.extract_tables() or []
                tables_md = tables_to_markdown(tables_raw)
                if tables_md:
                    logger.debug(f"페이지 {page_num}: {len(tables_md)}개 표 발견")
            except Exception as e:
                logger.warning(f"페이지 {page_num} 표 추출 실패: {e}")
                tables_raw = []
                tables_md = []

            # 3) 모드 결정 (텍스트가 충분하거나 표가 있으면 text, 아니면 vision)
            if text_len >= MIN_TEXT_CHARS_FOR_TEXT_MODE or len(tables_raw) > 0:
                mode = "text"
            else:
                mode = "vision"
                logger.debug(f"페이지 {page_num}: Vision OCR 모드 사용 (텍스트 부족)")

            page_info = {
                "page": page_num,
                "mode": mode,
                "text": raw_text if mode == "text" else "",
                "tables_markdown": tables_md,
                "vision_markdown": "",
            }

            if mode == "vision":
                try:
                    pil_img = page_to_pil(page)
                    page_info["vision_markdown"] = vision_ocr_markdown(pil_img)
                except Exception as e:
                    logger.error(f"페이지 {page_num} Vision OCR 실패: {e}")
                    page_info["vision_markdown"] = ""

            pages_output.append(page_info)

        doc.close()
        plumber_pdf.close()

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
