"""
Document processing service
"""
import re
from typing import List, Dict, Any, Optional
from pathlib import Path

from ..core.models import InsuranceDocument, Chunk, DocumentType
from ..core.config import config
from ..core.exceptions import DocumentProcessingException
from ..infrastructure.document_loader import BaseDocumentLoader, LoadedDocument
from ..infrastructure.document_loader.pdf_loader import PDFDocumentLoader
from ..infrastructure.chunking import BaseChunker
from ..infrastructure.chunking.token_chunker import TokenChunker
from ..infrastructure.chunking.semantic_chunker import SemanticChunker


class DocumentProcessor:
    """
    문서 처리 서비스 (리팩토링 버전)
    
    Document Loader + Chunker를 조합하여 문서 처리 파이프라인 제공
    """
    
    def __init__(
        self,
        document_loader: Optional[BaseDocumentLoader] = None,
        chunker: Optional[BaseChunker] = None,
        use_token_chunker: bool = True
    ):
        """
        문서 처리기 초기화
        
        Args:
            document_loader: 문서 로더 (기본값: PDFDocumentLoader)
            chunker: 청커 (기본값: TokenChunker 또는 SemanticChunker)
            use_token_chunker: True면 TokenChunker, False면 SemanticChunker
        """
        self.document_loader = document_loader or PDFDocumentLoader()
        
        if chunker is None:
            if use_token_chunker:
                self.chunker = TokenChunker()
            else:
                self.chunker = SemanticChunker()
        else:
            self.chunker = chunker
    
    def process_pdf(
        self,
        pdf_path: str,
        resume: bool = False
    ) -> List[InsuranceDocument]:
        """
        PDF 파일 전체 처리 (로드 + 청킹)
        
        Args:
            pdf_path: PDF 파일 경로
            resume: 이전 작업 재개 여부
            
        Returns:
            청크된 문서 리스트
        """
        try:
            # 1. PDF 로드
            loaded_docs = self.document_loader.load(pdf_path, resume=resume)
            
            # 2. LoadedDocument -> InsuranceDocument 변환
            insurance_docs = []
            for loaded_doc in loaded_docs:
                doc = InsuranceDocument(
                    id=f"{loaded_doc.metadata.filename}_p{loaded_doc.metadata.page_number}",
                    content=loaded_doc.content,
                    metadata={
                        "source": loaded_doc.metadata.source,
                        "filename": loaded_doc.metadata.filename,
                        "page": loaded_doc.metadata.page_number,
                        "total_pages": loaded_doc.metadata.total_pages,
                        **loaded_doc.metadata.extra
                    }
                )
                insurance_docs.append(doc)
            
            # 3. 청킹
            chunked_docs = self.chunker.chunk_documents(insurance_docs)
            
            return chunked_docs
            
        except Exception as e:
            raise DocumentProcessingException(
                f"Failed to process PDF: {str(e)}",
                details={"pdf_path": pdf_path}
            )
    
    def process_document(
        self,
        content: str,
        metadata: Dict[str, Any] = None,
        doc_id: str = None
    ) -> List[InsuranceDocument]:
        """
        단일 문서 처리 (청킹)
        
        Args:
            content: 문서 내용
            metadata: 메타데이터
            doc_id: 문서 ID
            
        Returns:
            청크된 문서 리스트
        """
        try:
            metadata = metadata or {}
            
            # Chunker로 청킹
            chunks = self.chunker.chunk(content, metadata)
            
            # Chunk -> InsuranceDocument 변환
            documents = []
            for idx, chunk in enumerate(chunks):
                doc = InsuranceDocument(
                    id=f"{doc_id}_chunk_{idx}" if doc_id else chunk.id,
                    content=chunk.content,
                    metadata=chunk.metadata
                )
                documents.append(doc)
            
            return documents
            
        except Exception as e:
            raise DocumentProcessingException(
                f"Failed to process document: {str(e)}",
                details={"content_length": len(content)}
            )
    
    def process_documents_batch(
        self,
        documents: List[Dict[str, Any]]
    ) -> List[InsuranceDocument]:
        """
        여러 문서 배치 처리
        
        Args:
            documents: [{"content": str, "metadata": dict, "id": str}, ...]
            
        Returns:
            청크된 문서 리스트
        """
        all_chunks = []
        
        for doc in documents:
            chunks = self.process_document(
                content=doc.get("content", ""),
                metadata=doc.get("metadata", {}),
                doc_id=doc.get("id")
            )
            all_chunks.extend(chunks)
        
        return all_chunks
    
    def get_info(self) -> Dict[str, Any]:
        """
        현재 프로세서 정보 반환
        
        Returns:
            프로세서 정보
        """
        return {
            "document_loader": self.document_loader.__class__.__name__,
            "chunker": self.chunker.__class__.__name__,
            "chunking_strategy": self.chunker.get_strategy().value,
        }
    
    @staticmethod
    def extract_keywords(text: str, min_length: int = 2) -> List[str]:
        """
        텍스트에서 핵심 키워드 추출
        
        Args:
            text: 텍스트
            min_length: 최소 키워드 길이
            
        Returns:
            키워드 리스트
        """
        # 한글, 영문, 숫자만 남기고 토큰화
        text = re.sub(r'[^\w\s가-힣]', ' ', text)
        tokens = text.split()
        
        # 불용어 제거
        stopwords = {
            '은', '는', '이', '가', '을', '를', '의', '에', '와', '과', '도', 
            '으로', '로', '입니다', '있습니다', '합니다', '한다', '된다', '이다', 
            '것', '수', '등', 'the', 'a', 'an', 'and', 'or', 'but', 'in', 
            'on', 'at', 'to', 'for', 'of', 'with'
        }
        
        keywords = [
            token for token in tokens 
            if len(token) >= min_length and token.lower() not in stopwords
        ]
        
        return list(set(keywords))  # 중복 제거
