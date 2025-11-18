"""
RAG 전용 설정 파일

기존 core/config.py의 설정을 재사용하고 RAG 전용 설정만 추가합니다.
"""

from pathlib import Path
from typing import Optional
from app.core.config import settings


class RAGConfig:
    """RAG 시스템 설정 (기존 설정 재사용)"""
    
    def __init__(self):
        # 기존 core/config.py의 settings 재사용
        self._settings = settings
        
        # 디렉토리 생성
        self.ensure_directories()
    
    # ========================================
    # 기존 설정 재사용 (core/config.py)
    # ========================================
    
    @property
    def OPENAI_API_KEY(self) -> str:
        """OpenAI API Key (기존 설정 사용)"""
        return self._settings.OPENAI_API_KEY
    
    @property
    def OPENAI_MODEL(self) -> str:
        """OpenAI LLM 모델 (기존 설정 사용)"""
        return self._settings.LLM_MODEL
    
    @property
    def OPENAI_VISION_MODEL(self) -> str:
        """OpenAI Vision 모델"""
        return "gpt-4o"  # Vision은 gpt-4o 사용
    
    @property
    def OPENAI_TEMPERATURE(self) -> float:
        """LLM Temperature (기존 설정 사용)"""
        return self._settings.LLM_TEMPERATURE
    
    @property
    def OPENAI_MAX_TOKENS(self) -> int:
        """LLM Max Tokens (기존 설정 사용)"""
        return self._settings.LLM_MAX_TOKENS
    
    @property
    def CHROMA_PERSIST_DIRECTORY(self) -> str:
        """ChromaDB 저장 경로 (기존 설정 사용)"""
        return self._settings.CHROMA_PERSIST_DIRECTORY
    
    @property
    def CHROMA_COLLECTION_NAME(self) -> str:
        """ChromaDB 컬렉션명 (RAG 전용)"""
        return "rag_documents"
    
    @property
    def UPLOAD_DIR(self) -> Path:
        """업로드 디렉토리 (기존 설정 사용)"""
        return Path(self._settings.UPLOAD_DIR)
    
    @property
    def DATA_DIR(self) -> Path:
        """데이터 디렉토리"""
        return Path("./internal_docs")
    
    @property
    def PROCESSED_DIR(self) -> Path:
        """처리된 파일 디렉토리"""
        return Path("./internal_docs/processed")
    
    # ========================================
    # RAG 전용 설정
    # ========================================
    
    # 한국어 임베딩 모델
    KOREAN_EMBEDDING_MODEL: str = "jhgan/ko-sroberta-multitask"
    EMBEDDING_DIMENSION: int = 768
    
    # 청크 설정
    RAG_CHUNK_SIZE: int = 400
    RAG_CHUNK_OVERLAP: int = 50
    RAG_MIN_CHUNK_SIZE: int = 300
    RAG_MAX_CHUNK_SIZE: int = 500
    
    # 검색 설정
    RAG_TOP_K: int = 3
    RAG_MAX_TOP_K: int = 4
    RAG_SIMILARITY_THRESHOLD: float = 0.25  # 거리도 threshold (0.0 ~ 1.0, 높을수록 유사도 높음)
    # Cosine distance (0~2)를 similarity (0~1)로 변환: similarity = 1 - distance/2
    # threshold 0.35 = distance 1.3 이하 (낮은 threshold로 더 많은 결과 포함)
    
    # LangSmith 설정
    @property
    def LANGSMITH_API_KEY(self) -> Optional[str]:
        """LangSmith API Key (core settings에서 읽기)"""
        return self._settings.LANGSMITH_API_KEY if self._settings.LANGSMITH_API_KEY else None
    
    @property
    def LANGSMITH_PROJECT(self) -> str:
        """LangSmith 프로젝트명"""
        return self._settings.LANGSMITH_PROJECT
    
    @property
    def LANGSMITH_TRACING(self) -> bool:
        """LangSmith 추적 활성화 여부"""
        return self._settings.LANGSMITH_TRACING.lower() == "true"
    
    # PDF 처리 설정
    MAX_IMAGE_SIZE: tuple = (1024, 1024)
    IMAGE_DPI: int = 150
    
    # 표 감지 설정
    TABLE_MIN_ROWS: int = 2
    TABLE_MIN_COLS: int = 2
    
    def ensure_directories(self):
        """필요한 디렉토리 생성"""
        self.DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        self.PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
        Path(self.CHROMA_PERSIST_DIRECTORY).mkdir(parents=True, exist_ok=True)


# 싱글톤 인스턴스
rag_config = RAGConfig()

