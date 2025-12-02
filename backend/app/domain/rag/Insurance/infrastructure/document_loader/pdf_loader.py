"""
PDF document loader with Vision API support
"""
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from threading import Lock

import fitz
import pdfplumber
from openai import OpenAI
from tqdm import tqdm

from .base import BaseDocumentLoader, LoadedDocument, DocumentMetadata
from ...core.config import config
from ...core.exceptions import DocumentProcessingException

# Import from services layer
from ...services.document_processor import PDFExtractor, PageResult


class PDFDocumentLoader(BaseDocumentLoader):
    """
    PDF 문서 로더 (Vision API 지원)
    
    기존 extractor 로직을 래핑하여 BaseDocumentLoader 인터페이스 제공
    """
    
    def __init__(
        self,
        openai_api_key: Optional[str] = None,
        use_vision: bool = True,
        resume: bool = False
    ):
        """
        PDF 로더 초기화
        
        Args:
            openai_api_key: OpenAI API 키 (None이면 config에서 가져옴)
            use_vision: Vision API 사용 여부
            resume: 이전 작업 재개 여부
        """
        self.openai_api_key = openai_api_key or config.openai_api_key
        self.use_vision = use_vision
        self.resume = resume
        self._client: Optional[OpenAI] = None
        self._client_lock = Lock()
        self._extractor: Optional[PDFExtractor] = None
    
    def supports(self, source: str) -> bool:
        """PDF 파일 지원 확인"""
        return str(source).lower().endswith('.pdf')
    
    def get_openai_client(self) -> OpenAI:
        """OpenAI 클라이언트 lazy loading"""
        if self._client is None:
            with self._client_lock:
                if self._client is None:
                    self._client = OpenAI(api_key=self.openai_api_key)
        return self._client
    
    def get_extractor(self) -> PDFExtractor:
        """PDF 추출기 lazy loading"""
        if self._extractor is None:
            self._extractor = PDFExtractor(openai_client=self.get_openai_client())
        return self._extractor
    
    def load(self, source: str, **kwargs) -> List[LoadedDocument]:
        """
        PDF 파일 로드
        
        Args:
            source: PDF 파일 경로
            **kwargs: 추가 옵션
                - max_workers: 사용하지 않음 (순차 처리)
                - resume: 이전 작업 재개 여부 (기본값: self.resume)
                
        Returns:
            로드된 페이지별 문서 리스트
        """
        pdf_path = Path(source)
        
        if not pdf_path.exists():
            raise DocumentProcessingException(
                f"PDF 파일을 찾을 수 없습니다: {pdf_path}",
                details={"source": source}
            )
        
        resume = kwargs.get('resume', self.resume)
        
        # 기존 extractor 로직 사용
        pages_data = self._extract_pdf_pages(pdf_path, resume)
        
        # LoadedDocument 리스트로 변환
        loaded_docs = []
        for page_data in pages_data:
            page_num = page_data.get('page', 0)
            content = page_data.get('content', '')
            mode = page_data.get('mode', 'unknown')
            
            metadata = DocumentMetadata(
                source=str(pdf_path),
                filename=pdf_path.name,
                total_pages=len(pages_data),
                page_number=page_num,
                document_type='pdf',
                extra={
                    'mode': mode,
                    'has_tables': page_data.get('has_tables', False),
                    'has_images': page_data.get('has_images', False),
                }
            )
            
            doc = LoadedDocument(
                content=content,
                metadata=metadata,
                raw_data=page_data
            )
            
            loaded_docs.append(doc)
        
        return loaded_docs
    
    def _extract_pdf_pages(
        self,
        pdf_path: Path,
        resume: bool = False
    ) -> List[Dict[str, Any]]:
        """
        PDF 페이지 추출 (기존 extractor 로직)
        
        Args:
            pdf_path: PDF 파일 경로
            resume: 이전 작업 재개 여부
            
        Returns:
            페이지 데이터 리스트
        """
        # Resume: 기존 JSON 로드
        previous_pages = {}
        out_json_path = config.processed_documents_path / f"{pdf_path.stem}.json"
        
        if resume and out_json_path.exists():
            try:
                with open(out_json_path, "r", encoding="utf-8") as f:
                    previous = json.load(f)
                    previous_pages = {p["page"]: p for p in previous.get("pages", [])}
            except Exception:
                previous_pages = {}
        
        doc = None
        plumber_pdf = None
        
        try:
            # PDF 열기
            doc = fitz.open(pdf_path)
            plumber_pdf = pdfplumber.open(pdf_path)
            
            total_pages = len(doc)
            extractor = self.get_extractor()
            
            # 순차 처리
            pages_output = []
            skipped_count = 0
            
            for i in tqdm(range(total_pages), desc=f"Loading {pdf_path.name}"):
                page = doc[i]
                plumber_page = plumber_pdf.pages[i]
                page_num = i + 1
                
                # Resume: 성공한 페이지 스킵
                if resume and page_num in previous_pages:
                    prev_mode = previous_pages[page_num].get("mode", "")
                    if prev_mode != "error":
                        pages_output.append(previous_pages[page_num])
                        skipped_count += 1
                        continue
                
                try:
                    # 페이지 분석
                    analysis = extractor.analyze_page(page, plumber_page, page_num)
                    
                    # 페이지 처리 (Vision/LLM 적용)
                    if self.use_vision:
                        page_result = extractor.process_page(page, analysis)
                    else:
                        # Text-only mode
                        page_result = PageResult(
                            page=page_num,
                            mode="text",
                            content=analysis.raw_text,
                            has_tables=analysis.has_tables,
                            has_images=analysis.has_images,
                            table_bboxes=analysis.table_bboxes,
                            image_bboxes=analysis.image_bboxes
                        )
                    
                    # PageResult를 dict로 변환
                    pages_output.append(page_result.to_dict())
                    
                except Exception as e:
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
            
            # JSON 저장 (캐싱용)
            result = {
                "file": str(pdf_path),
                "total_pages": len(pages_output),
                "pages": pages_output,
            }
            
            with open(out_json_path, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            
            return pages_output
            
        except Exception as e:
            raise DocumentProcessingException(
                f"PDF 추출 중 오류 발생: {str(e)}",
                details={"pdf_path": str(pdf_path)}
            )
        finally:
            if doc is not None:
                doc.close()
            if plumber_pdf is not None:
                plumber_pdf.close()
