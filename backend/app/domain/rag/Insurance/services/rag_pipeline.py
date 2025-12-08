"""
RAG Pipeline - Orchestrator
"""
import time
from typing import Optional, Dict, Any

from ..core.models import Query, GenerationResult
from ..core.config import config
from ..core.exceptions import InsuranceRAGException

from ..infrastructure.vectorstore.base import BaseVectorStore
from ..infrastructure.vectorstore.chroma import ChromaVectorStore
from ..infrastructure.embeddings.base import BaseEmbeddingProvider
from ..infrastructure.embeddings.openai import OpenAIEmbeddingProvider
from ..infrastructure.llm.base import BaseLLMProvider
from ..infrastructure.llm.openai import OpenAILLMProvider

from .document_processor import DocumentProcessor
from .retriever import Retriever
from .generator import Generator


class RAGPipeline:
    """RAG 전체 파이프라인 오케스트레이터"""
    
    def __init__(
        self,
        vector_store: Optional[BaseVectorStore] = None,
        embedding_provider: Optional[BaseEmbeddingProvider] = None,
        llm_provider: Optional[BaseLLMProvider] = None,
        document_processor: Optional[DocumentProcessor] = None,
        retriever: Optional[Retriever] = None,
        generator: Optional[Generator] = None
    ):
        """
        RAG 파이프라인 초기화
        
        Args:
            vector_store: 벡터 스토어 (None이면 기본 ChromaDB 사용)
            embedding_provider: 임베딩 제공자 (None이면 기본 OpenAI 사용)
            llm_provider: LLM 제공자 (None이면 기본 OpenAI 사용)
            document_processor: 문서 처리기
            retriever: 검색기
            generator: 답변 생성기
        """
        # Infrastructure 레이어 초기화
        self.embedding_provider = embedding_provider or self._create_default_embedding_provider()
        self.vector_store = vector_store or self._create_default_vector_store()
        self.llm_provider = llm_provider or self._create_default_llm_provider()
        
        # Service 레이어 초기화
        self.document_processor = document_processor or DocumentProcessor()
        self.retriever = retriever or Retriever(
            vector_store=self.vector_store,
            embedding_provider=self.embedding_provider
        )
        self.generator = generator or Generator(
            llm_provider=self.llm_provider
        )
    
    def run(
        self,
        question: str,
        top_k: Optional[int] = None,
        validate_answer: bool = False,
        user_id: Optional[str] = None
    ) -> GenerationResult:
        """
        전체 RAG 파이프라인 실행
        
        Args:
            question: 사용자 질문
            top_k: 검색할 문서 개수
            validate_answer: 답변 검증 수행 여부
            user_id: 사용자 ID
            
        Returns:
            답변 생성 결과
        """
        try:
            # 1. 쿼리 객체 생성
            query = Query(question=question, user_id=user_id)
            
            # 2. 검색 (Retrieval)
            retrieval_result = self.retriever.retrieve(query=query, top_k=top_k)
            
            if not retrieval_result.documents:
                # 검색 결과가 없는 경우
                return GenerationResult(
                    answer="죄송합니다. 관련된 정보를 찾을 수 없습니다.",
                    query=query,
                    source_documents=[],
                    confidence_score=0.0,
                    generation_time_ms=0.0,
                    metadata={"error": "no_documents_found"}
                )
            
            # 3. 답변 생성 (Generation)
            generation_result = self.generator.generate(
                query=query,
                context_documents=retrieval_result.documents
            )
            
            # 4. 답변 검증 (선택사항)
            if validate_answer:
                context = self.retriever.get_relevant_context(query)
                is_valid, validated_answer = self.generator.validate_answer(
                    question=question,
                    context=context,
                    generated_answer=generation_result.answer
                )
                
                if not is_valid:
                    generation_result.answer = validated_answer
                    generation_result.confidence_score = 0.1
                    generation_result.metadata["validated"] = False
                else:
                    generation_result.metadata["validated"] = True
            
            # 메타데이터에 검색 정보 추가
            generation_result.metadata.update({
                "retrieval_time_ms": retrieval_result.retrieval_time_ms,
                "num_retrieved_docs": len(retrieval_result.documents),
                "retrieval_scores": retrieval_result.scores
            })
            
            return generation_result
            
        except Exception as e:
            raise InsuranceRAGException(
                f"RAG pipeline failed: {str(e)}",
                details={"question": question}
            )
    
    def run_simple(self, question: str) -> str:
        """
        간단한 질의응답 (답변 문자열만 반환)
        
        Args:
            question: 질문
            
        Returns:
            답변 문자열
        """
        result = self.run(question=question)
        return result.answer
    
    def get_pipeline_info(self) -> Dict[str, Any]:
        """
        파이프라인 정보 반환
        
        Returns:
            파이프라인 구성 정보
        """
        return {
            "vector_store": self.vector_store.__class__.__name__,
            "vector_store_info": self.vector_store.get_collection_info(),
            "embedding_model": self.embedding_provider.get_model_name(),
            "embedding_dimension": self.embedding_provider.get_embedding_dimension(),
            "llm_model": self.llm_provider.get_model_name(),
            "config": {
                "top_k": config.top_k,
                "similarity_threshold": config.similarity_threshold,
                "chunk_size": config.chunk_size,
                "chunk_overlap": config.chunk_overlap
            }
        }
    
    def _create_default_vector_store(self) -> BaseVectorStore:
        """기본 벡터 스토어 생성 (ChromaDB)"""
        from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction
        
        embedding_function = OpenAIEmbeddingFunction(
            api_key=config.openai_api_key,
            model_name=config.embedding_model
        )
        
        return ChromaVectorStore(
            collection_name=config.collection_name,
            persist_directory=config.vector_store_path,
            embedding_function=embedding_function
        )
    
    def _create_default_embedding_provider(self) -> BaseEmbeddingProvider:
        """기본 임베딩 제공자 생성 (OpenAI)"""
        return OpenAIEmbeddingProvider(
            model=config.embedding_model,
            dimensions=config.embedding_dimensions
        )
    
    def _create_default_llm_provider(self) -> BaseLLMProvider:
        """기본 LLM 제공자 생성 (OpenAI)"""
        return OpenAILLMProvider(
            model=config.llm_model,
            temperature=config.llm_temperature,
            max_tokens=config.llm_max_tokens
        )


# 편의 함수: 즉시 사용 가능한 파이프라인 생성
def create_insurance_rag_pipeline() -> RAGPipeline:
    """
    기본 설정으로 RAG 파이프라인 생성
    
    Returns:
        RAGPipeline 인스턴스
    """
    return RAGPipeline()
