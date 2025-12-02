"""
Configuration management for Insurance RAG system
"""
import os
from typing import Optional, Literal
from pydantic_settings import BaseSettings, SettingsConfigDict


# Vision OCR 실패 indicators (from legacy constants.py)
OCR_FAILURE_INDICATORS = [
    "i can't read",
    "i cannot read",
    "unable to transcribe",
    "cannot extract",
    "no readable text",
    "the image appears to be blank",
    "provide a different image"
]


class InsuranceRAGConfig(BaseSettings):
    """보험 RAG 시스템 설정"""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="INSURANCE_RAG_",
        case_sensitive=False,
        extra="ignore"
    )
    
    # ========================================
    # Vector Store Configuration
    # ========================================
    vector_store_type: Literal["chroma", "pinecone", "faiss"] = "chroma"
    vector_store_path: str = "backend/data/chroma"
    collection_name: str = "insurance_documents"
    
    # ========================================
    # Retrieval Configuration
    # ========================================
    top_k: int = 5
    similarity_threshold: float = 0.75
    reranking_enabled: bool = False
    reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    hybrid_search_enabled: bool = False
    hybrid_alpha: float = 0.7  # 벡터 검색 가중치
    
    # ========================================
    # Generation Configuration
    # ========================================
    llm_model: str = "gpt-4o-mini"
    llm_temperature: float = 0.1
    llm_max_tokens: int = 1000
    llm_streaming: bool = False
    
    # ========================================
    # Embeddings Configuration
    # ========================================
    embedding_model: str = "text-embedding-3-large"
    embedding_dimensions: int = 3072
    embedding_batch_size: int = 100
    
    # ========================================
    # Document Processing Configuration
    # ========================================
    chunk_size: int = 1000
    chunk_overlap: int = 200
    chunk_separators: list = ["\n\n", "\n", "。", " ", ""]
    
    # ========================================
    # OpenAI API Configuration
    # ========================================
    openai_api_key: Optional[str] = None
    openai_organization: Optional[str] = None
    openai_api_base: Optional[str] = None
    
    # ========================================
    # Evaluation Configuration
    # ========================================
    eval_qa_file: str = "backend/app/domain/rag/Insurance/data/qa_datasets/qa_filtered_50.json"
    eval_output_dir: str = "backend/app/domain/rag/Insurance/evaluation/results"
    eval_visualizations_dir: str = "backend/app/domain/rag/Insurance/evaluation/visualizations"
    
    # ========================================
    # Logging Configuration
    # ========================================
    log_level: str = "INFO"
    log_file: Optional[str] = "backend/app/domain/rag/Insurance/logs/insurance_rag.log"
    
    # ========================================
    # Performance Configuration
    # ========================================
    cache_enabled: bool = True
    cache_ttl: int = 3600  # seconds
    max_concurrent_requests: int = 10
    request_timeout: int = 30  # seconds
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # OpenAI API 키가 설정되지 않으면 환경변수에서 로드
        if not self.openai_api_key:
            self.openai_api_key = os.getenv("OPENAI_API_KEY")
        
        if not self.openai_api_key:
            raise ValueError(
                "OPENAI_API_KEY is not set. "
                "Please set it in .env file or environment variable."
            )
    
    @property
    def vector_store_full_path(self) -> str:
        """벡터 스토어 전체 경로 반환"""
        return os.path.abspath(self.vector_store_path)
    
    @property
    def eval_output_full_path(self) -> str:
        """평가 결과 출력 전체 경로"""
        os.makedirs(self.eval_output_dir, exist_ok=True)
        return os.path.abspath(self.eval_output_dir)
    
    def get_openai_kwargs(self) -> dict:
        """OpenAI 초기화에 필요한 kwargs 반환"""
        kwargs = {"api_key": self.openai_api_key}
        if self.openai_organization:
            kwargs["organization"] = self.openai_organization
        if self.openai_api_base:
            kwargs["base_url"] = self.openai_api_base
        return kwargs


# 전역 설정 인스턴스
config = InsuranceRAGConfig()
