"""
Base document loader interface
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from pathlib import Path
from dataclasses import dataclass, field

from ...core.models import InsuranceDocument


@dataclass
class DocumentMetadata:
    """문서 메타데이터"""
    source: str  # 파일 경로 또는 URL
    filename: str
    total_pages: Optional[int] = None
    page_number: Optional[int] = None
    document_type: Optional[str] = None  # pdf, docx, html 등
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LoadedDocument:
    """로드된 문서 (청킹 이전)"""
    content: str
    metadata: DocumentMetadata
    raw_data: Optional[Dict[str, Any]] = None  # 원본 데이터 보존


class BaseDocumentLoader(ABC):
    """문서 로더 추상 인터페이스"""
    
    @abstractmethod
    def load(self, source: str, **kwargs) -> List[LoadedDocument]:
        """
        문서 로드 (청킹하지 않음)
        
        Args:
            source: 문서 소스 (파일 경로, URL 등)
            **kwargs: 추가 옵션
            
        Returns:
            로드된 문서 리스트 (페이지별 또는 섹션별)
        """
        pass
    
    @abstractmethod
    def supports(self, source: str) -> bool:
        """
        이 로더가 해당 소스를 지원하는지 확인
        
        Args:
            source: 문서 소스
            
        Returns:
            지원 여부
        """
        pass
    
    def get_metadata(self, source: str) -> Optional[DocumentMetadata]:
        """
        문서 메타데이터만 추출 (옵션)
        
        Args:
            source: 문서 소스
            
        Returns:
            메타데이터 (없으면 None)
        """
        return None
