"""
Insurance RAG 검색 모듈 (LangChain 기반)

HR RAG와 완전히 분리된 독립적인 retriever입니다.
"""

from typing import List, Optional, Dict, Any
import time
import os

# LangChain imports
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough, RunnableLambda
from langchain_openai import ChatOpenAI

# LangSmith 설정
from langsmith import traceable

from .config import insurance_config
from .vector_store import VectorStore
from .schemas import QueryRequest, QueryResponse, RetrievedChunk
from .utils import get_logger

logger = get_logger(__name__)


class InsuranceRetriever:
    """Insurance RAG 기반 검색 및 답변 생성 (LangChain 체인 사용, HR과 분리)"""
    
    def __init__(self, collection_name: Optional[str] = None):
        self.config = insurance_config
        self.vector_store = VectorStore(collection_name)
        
        # LangSmith 설정
        if self.config.LANGSMITH_TRACING and self.config.LANGSMITH_API_KEY:
            os.environ["LANGCHAIN_TRACING_V2"] = "true"
            os.environ["LANGCHAIN_API_KEY"] = self.config.LANGSMITH_API_KEY
            os.environ["LANGCHAIN_PROJECT"] = self.config.LANGSMITH_PROJECT
            logger.info(f"LangSmith 추적 활성화: {self.config.LANGSMITH_PROJECT}")
        
        # Lazy loading: LLM을 실제 사용 시에만 로드
        self._llm = None
        self._rag_chain = None
        self._smalltalk_chain = None
        
        logger.info("Insurance RAGRetriever 초기화 완료 (LLM lazy loading)")
    
    @property
    def llm(self):
        """LLM lazy loading"""
        if self._llm is None:
            self._llm = ChatOpenAI(
                model=self.config.OPENAI_MODEL,
                temperature=self.config.OPENAI_TEMPERATURE,
                max_tokens=self.config.OPENAI_MAX_TOKENS,
                api_key=self.config.OPENAI_API_KEY
            )
            logger.info(f"Insurance LLM 로드 완료: {self.config.OPENAI_MODEL}")
        return self._llm
    
    @property
    def prompt_template(self):
        """프롬프트 템플릿 (Insurance 전용)"""
        return ChatPromptTemplate.from_messages([
            ("system", """당신은 보험 관련 문서 내용을 기반으로 정확하게 답변하는 AI 어시스턴트입니다.

다음 규칙을 따라주세요:
1. 제공된 문서 내용만을 기반으로 답변하세요.
2. 문서에 없는 내용은 추측하지 마세요.
3. 답변 먼저 한 후 마지막에 출처를 제공하세요 (예시: 출처: 보험약관.pdf)
4. 명확하고 구조화된 답변을 제공하세요.
5. 한국어로 답변하세요."""),
            ("user", """다음 문서들을 참고하여 질문에 답변해주세요.

{context}

질문: {query}

답변:""")
        ])
    
    @property
    def smalltalk_prompt(self):
        """Small talk 프롬프트 템플릿"""
        return ChatPromptTemplate.from_messages([
            ("system", """당신은 친근하고 도움이 되는 AI 어시스턴트입니다.
일상적인 대화를 자연스럽게 나누고, 사용자에게 친절하게 응답하세요.
한국어로 답변하세요."""),
            ("user", "{query}")
        ])
    
    @property
    def rag_chain(self):
        """RAG 체인 lazy loading"""
        if self._rag_chain is None:
            self._rag_chain = self._build_rag_chain()
            logger.info("Insurance RAG 체인 구성 완료")
        return self._rag_chain
    
    @property
    def smalltalk_chain(self):
        """Small talk 체인 lazy loading"""
        if self._smalltalk_chain is None:
            self._smalltalk_chain = (
                self.smalltalk_prompt
                | self.llm
                | StrOutputParser()
            )
            logger.info("Insurance Small talk 체인 구성 완료")
        return self._smalltalk_chain
    
    def _build_rag_chain(self):
        """LangChain 파이프 연산자(|)를 사용하여 RAG 체인 구성"""
        
        # 1. 컨텍스트 검색 및 동적 threshold 필터링
        @traceable(name="insurance_retrieve_and_filter")
        def retrieve_and_filter(inputs: Dict[str, Any]) -> Dict[str, Any]:
            """문서 검색 및 동적 threshold 기반 필터링"""
            query = inputs["query"]
            top_k = inputs.get("top_k", self.config.RAG_TOP_K)
            
            logger.info(f"Insurance 문서 검색 중: '{query}' (Top-{top_k})")
            
            # 벡터 검색 (더 많이 검색하여 동적 threshold 적용)
            results = self.vector_store.search(query, top_k * 3)
            
            # 결과 변환 및 동적 threshold 필터링
            retrieved_chunks = []
            all_similarities = []
            
            # 검색 결과 확인
            if not results:
                logger.warning("검색 결과가 없습니다.")
            elif not results.get('documents') or not results['documents']:
                logger.warning("검색 결과 문서가 없습니다.")
            elif not results['documents'][0]:
                logger.warning("검색 결과 문서 리스트가 비어있습니다.")
            else:
                doc_list = results['documents'][0]
                similarity_list = results.get('distances', [[]])[0] if results.get('distances') else []
                meta_list = results.get('metadatas', [[]])[0] if results.get('metadatas') else []
                
                logger.info(f"검색 결과: {len(doc_list)}개 문서, {len(similarity_list)}개 유사도 점수")
                
                # 모든 유사도를 수집
                for i in range(len(doc_list)):
                    if i < len(similarity_list):
                        similarity_score = float(similarity_list[i])
                    else:
                        similarity_score = 0.0
                    
                    all_similarities.append(similarity_score)
                    
                    metadata = meta_list[i] if i < len(meta_list) else {}
                    chunk = RetrievedChunk(
                        text=doc_list[i],
                        metadata=metadata,
                        score=similarity_score
                    )
                    retrieved_chunks.append(chunk)
            
            # 동적 threshold 계산
            if all_similarities:
                # 최고 점수와 평균 점수 계산
                max_similarity = max(all_similarities)
                avg_similarity = sum(all_similarities) / len(all_similarities)
                
                # 동적 threshold: 최고 점수와 평균의 중간값, min~max 범위 내로 제한
                dynamic_threshold = (max_similarity + avg_similarity) / 2
                dynamic_threshold = max(
                    self.config.RAG_MIN_SIMILARITY_THRESHOLD,
                    min(dynamic_threshold, self.config.RAG_MAX_SIMILARITY_THRESHOLD)
                )
                
                logger.info(f"동적 threshold 계산: max={max_similarity:.4f}, avg={avg_similarity:.4f}, "
                           f"threshold={dynamic_threshold:.4f} (범위: {self.config.RAG_MIN_SIMILARITY_THRESHOLD}~{self.config.RAG_MAX_SIMILARITY_THRESHOLD})")
            else:
                dynamic_threshold = self.config.RAG_MIN_SIMILARITY_THRESHOLD
                logger.warning(f"유사도 없음, 기본 threshold 사용: {dynamic_threshold}")
            
            # 동적 threshold 기반 필터링
            filtered_chunks = []
            for chunk in retrieved_chunks:
                filename = chunk.metadata.get('filename', chunk.metadata.get('source', 'Unknown'))
                page_num = chunk.metadata.get('page_number', chunk.metadata.get('page', '?'))
                
                if chunk.score >= dynamic_threshold:
                    filtered_chunks.append(chunk)
                    logger.info(f"  ✓ 파일: {filename}, 페이지: {page_num}, 유사도: {chunk.score:.4f} >= {dynamic_threshold:.4f}")
                else:
                    logger.info(f"  ✗ 필터링: {filename}, 페이지: {page_num}, 유사도: {chunk.score:.4f} < {dynamic_threshold:.4f}")
            
            # 상위 k개만 선택
            retrieved_chunks = filtered_chunks[:top_k]
            
            logger.info(f"{len(retrieved_chunks)}개 청크 최종 선택 (동적 threshold: {dynamic_threshold:.4f})")
            
            # 컨텍스트 구성
            context_parts = []
            for i, chunk in enumerate(retrieved_chunks, 1):
                context_parts.append(f"[문서 {i}]")
                filename = chunk.metadata.get('filename', chunk.metadata.get('source', 'Unknown'))
                page_num = chunk.metadata.get('page_number', chunk.metadata.get('page', 'Unknown'))
                context_parts.append(f"파일: {filename}")
                context_parts.append(f"페이지: {page_num}")
                context_parts.append(f"내용:\n{chunk.text}")
                context_parts.append("")
            
            context = "\n".join(context_parts) if context_parts else "관련 문서를 찾을 수 없습니다."
            
            return {
                "query": query,
                "context": context,
                "retrieved_chunks": retrieved_chunks,
                "top_k": top_k,
                "dynamic_threshold": dynamic_threshold
            }
        
        # 2. 답변 생성
        @traceable(name="insurance_generate_answer")
        def generate_answer(inputs: Dict[str, Any]) -> Dict[str, Any]:
            """LLM을 사용하여 답변 생성"""
            query = inputs["query"]
            context = inputs["context"]
            retrieved_chunks = inputs["retrieved_chunks"]
            
            if not retrieved_chunks:
                logger.warning("검색된 청크가 없음 - 기본 메시지 반환")
                return {
                    **inputs,
                    "answer": "죄송합니다. 관련된 정보를 찾을 수 없습니다."
                }
            
            # LangChain 체인 실행: prompt | llm | parser
            answer = (
                self.prompt_template 
                | self.llm 
                | StrOutputParser()
            ).invoke({
                "query": query,
                "context": context
            })
            
            return {
                **inputs,
                "answer": answer
            }
        
        # LangChain 체인 구성 (파이프 연산자 사용)
        chain = (
            RunnablePassthrough()
            | RunnableLambda(retrieve_and_filter)
            | RunnableLambda(generate_answer)
        )
        
        return chain
    
    @traceable(
        name="insurance_rag_query_full",
        metadata={
            "component": "Insurance RAG System",
            "version": "1.0"
        }
    )
    def query(self, request: QueryRequest) -> QueryResponse:
        """
        질의응답 전체 프로세스 (동적 threshold 자동 적용)
        
        Args:
            request: 질의응답 요청
            
        Returns:
            QueryResponse: 질의응답 응답
        """
        start_time = time.time()
        
        try:
            # RAG 실행
            logger.info(f"Insurance 질의응답 시작: '{request.query}'")
            
            # LangChain 체인 실행 (동적 threshold는 자동 계산)
            result = self.rag_chain.invoke({
                "query": request.query,
                "top_k": request.top_k or self.config.RAG_TOP_K
            })
            
            answer = result["answer"]
            retrieved_chunks = result["retrieved_chunks"]
            
            # 검색 결과가 없을 때
            if not retrieved_chunks:
                logger.warning(f"검색 결과 없음: '{request.query}'")
                answer = "죄송합니다. 질문하신 내용과 관련된 보험 문서를 찾을 수 없습니다. 다른 질문을 해주시거나, 더 구체적으로 질문해주세요."
            
            # 처리 시간 계산
            processing_time = time.time() - start_time
            
            response = QueryResponse(
                query=request.query,
                answer=answer,
                retrieved_chunks=retrieved_chunks,
                processing_time=processing_time,
                model_used=self.config.OPENAI_MODEL
            )
            
            logger.info(f"Insurance 질의응답 완료: {processing_time:.2f}초, {len(retrieved_chunks)}개 청크")
            
            return response
            
        except Exception as e:
            logger.exception("Insurance 질의응답 처리 중 오류")
            processing_time = time.time() - start_time
            
            return QueryResponse(
                query=request.query,
                answer=f"질의응답 처리 중 오류가 발생했습니다: {str(e)}",
                retrieved_chunks=[],
                processing_time=processing_time,
                model_used=self.config.OPENAI_MODEL
            )
