"""
Insurance RAG PDF 추출 모듈 - 메인 오케스트레이터

PDF 파일을 열고, 각 페이지를 분석 및 처리하여 JSON으로 저장하는 메인 함수
"""

import json
from pathlib import Path
from threading import Lock

import fitz
import pdfplumber
from tqdm import tqdm
from openai import OpenAI

from ..config import insurance_config
from ..utils import get_logger
from ..performance import get_performance_monitor
from .page_analysis import analyze_page
from .page_processor import process_page
from .models import PageResult

logger = get_logger(__name__)

# OpenAI 클라이언트 lazy loading
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


def extract_pdf(pdf_path: str, max_workers: int = 4, resume: bool = False) -> Path:
    """
    PDF 파일 추출 (순차 처리 + Resume 기능)
    
    [처리 프로세스]
    1. PDF 열기 (PyMuPDF + pdfplumber)
    2. 각 페이지에 대해:
       - analyze_page()로 페이지 분석
       - process_page()로 Vision/LLM 처리
    3. 결과를 JSON으로 저장
    
    Args:
        pdf_path: PDF 파일 경로
        max_workers: 사용하지 않음 (순차 처리)
        resume: True이면 기존 JSON에서 성공한 페이지 스킵
        
    Returns:
        Path: 생성된 JSON 파일 경로
    """
    pdf_path = Path(pdf_path)
    
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF 파일을 찾을 수 없습니다: {pdf_path}")
    
    logger.info(f"PDF 추출 시작: {pdf_path.name} (resume={resume})")
    
    out_json_path = insurance_config.PROCESSED_DIR / f"{pdf_path.stem}.json"
    
    # Resume: 기존 JSON 로드
    previous_pages = {}
    if resume and out_json_path.exists():
        try:
            with open(out_json_path, "r", encoding="utf-8") as f:
                previous = json.load(f)
                previous_pages = {p["page"]: p for p in previous.get("pages", [])}
            logger.info(f"Resume: 기존 {len(previous_pages)}개 페이지 로드")
        except Exception as e:
            logger.warning(f"Resume: 기존 JSON 로드 실패: {e}")
            previous_pages = {}
    
    doc = None
    plumber_pdf = None
    
    try:
        # PDF 열기
        doc = fitz.open(pdf_path)
        plumber_pdf = pdfplumber.open(pdf_path)
        
        total_pages = len(doc)
        logger.info(f"총 {total_pages}페이지 처리 시작")
        
        # OpenAI 클라이언트 초기화
        client = get_openai_client()
        
        # 순차 처리
        pages_output = []
        monitor = get_performance_monitor()
        skipped_count = 0
        
        for i in tqdm(range(total_pages), desc=f"Extracting {pdf_path.name}"):
            page = doc[i]
            plumber_page = plumber_pdf.pages[i]
            page_num = i + 1
            
            # Resume: 성공한 페이지 스킵
            if resume and page_num in previous_pages:
                prev_mode = previous_pages[page_num].get("mode", "")
                if prev_mode != "error":
                    pages_output.append(previous_pages[page_num])
                    skipped_count += 1
                    logger.debug(f"Resume: 페이지 {page_num} 스킵 (mode={prev_mode})")
                    continue
            
            try:
                # 1) 페이지 분석 (Vision/LLM 호출 없음)
                with monitor.measure(f"페이지 분석 (p{page_num})"):
                    analysis = analyze_page(page, plumber_page, page_num)
                
                # 2) 페이지 처리 (Vision/LLM 적용)
                with monitor.measure(f"페이지 처리 (p{page_num})"):
                    page_result = process_page(page, analysis, client)
                
                # 3) PageResult를 dict로 변환하여 저장
                pages_output.append(page_result.to_dict())
                
            except Exception as e:
                logger.error(f"페이지 {page_num} 처리 중 오류: {e}")
                # 오류 발생 시 빈 페이지 정보 저장
                error_result = PageResult(
                    page=page_num,
                    mode="error",
                    content="",
                    has_tables=False,
                    has_images=False,
                    table_bboxes=[],
                    image_bboxes=[]
                )
                pages_output.append(error_result.to_dict())
        
        if resume and skipped_count > 0:
            logger.info(f"Resume: {skipped_count}개 페이지 스킵됨")
        
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
    finally:
        # PDF 닫기 (예외 발생 시에도 리소스 정리)
        if doc is not None:
            doc.close()
        if plumber_pdf is not None:
            plumber_pdf.close()
