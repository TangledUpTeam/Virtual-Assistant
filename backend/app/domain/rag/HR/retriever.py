"""
RAG 검색 모듈 (LangChain 기반)

LangChain 체인과 LangSmith를 사용하여 RAG 시스템을 구현합니다.
"""

from typing import List, Optional, Dict, Any
import time
import os
import json
import datetime

# LangChain imports
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough, RunnableLambda
from langchain_openai import ChatOpenAI

# LangSmith 설정
from langsmith import traceable

from .config import rag_config
from .vector_store import VectorStore
from .schemas import QueryRequest, QueryResponse, RetrievedChunk
from .utils import get_logger
from .evaluator import RAGEvaluator

logger = get_logger(__name__)


class RAGRetriever:
    """RAG 기반 검색 및 답변 생성 (LangChain 체인 사용)"""
    
    def __init__(self, collection_name: Optional[str] = None):
        self.config = rag_config
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
        self._rag_chain = None
        self._smalltalk_chain = None
        self._evaluator = None
        
        logger.info("RAGRetriever 초기화 완료 (LLM lazy loading)")

    @property
    def evaluator(self):
        """Evaluator lazy loading"""
        if self._evaluator is None:
            self._evaluator = RAGEvaluator()
        return self._evaluator
    
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
            logger.info(f"LLM 로드 완료: {self.config.OPENAI_MODEL}")
        return self._llm
    
    @property
    def prompt_template(self):
        """프롬프트 템플릿"""
        return ChatPromptTemplate.from_messages([
            ("system", """당신은 문서 내용을 기반으로 정확하게 답변하는 AI 어시스턴트입니다.

다음 규칙을 엄격히 준수하여 답변하세요:

1. **내용 기반**: 오직 제공된 문서 내용에 근거하여 답변하며, 추측하지 마십시오.
2. **Markdown 필수**: 가독성을 위해 Markdown을 적극 활용하세요.
   - **모든 목록(글머리 기호)과 소제목(`###`) 앞뒤에는 반드시 줄바꿈 문자(\\n)를 두 번 사용하여 빈 줄을 만드세요.** (매우 중요)
   - 핵심 내용은 **볼드체**로 강조합니다.
3. **간결성**:
   - 불필요한 빈 줄(3줄 이상 연속)은 피하되, **가독성과 마크다운 렌더링을 위해 필요한 줄바꿈은 아끼지 마십시오.**
   - 답변은 명확하고 간결하게 작성하세요.
4. **언어**: 한국어로 답변하세요."""),
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
            logger.info("RAG 체인 구성 완료")
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
            logger.info("Small talk 체인 구성 완료")
        return self._smalltalk_chain
    
    def _build_rag_chain(self):
        """LangChain 파이프 연산자(|)를 사용하여 RAG 체인 구성"""
        
        # 1. 컨텍스트 검색 및 동적 threshold 필터링
        @traceable(name="retrieve_and_filter")
        def retrieve_and_filter(inputs: Dict[str, Any]) -> Dict[str, Any]:
            """문서 검색 및 동적 threshold 기반 필터링"""
            query = inputs["query"]
            top_k = inputs.get("top_k", self.config.RAG_TOP_K)
            
            logger.info(f"문서 검색 중: '{query}' (Top-{top_k})")
            
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
                filename = chunk.metadata.get('filename', 'Unknown')
                page_num = chunk.metadata.get('page_number', '?')
                
                if chunk.score >= dynamic_threshold:
                    filtered_chunks.append(chunk)
                    logger.info(f"  ✓ 파일: {filename}, 페이지: {page_num}, 유사도: {chunk.score:.4f} >= {dynamic_threshold:.4f}")
                else:
                    # logger.info(f"  ✗ 필터링: {filename}, 페이지: {page_num}, 유사도: {chunk.score:.4f} < {dynamic_threshold:.4f}")
                    pass
            
            # 상위 k개만 선택
            retrieved_chunks = filtered_chunks[:top_k]
            
            logger.info(f"{len(retrieved_chunks)}개 청크 최종 선택 (동적 threshold: {dynamic_threshold:.4f})")
            
            # 컨텍스트 구성
            context_parts = []
            for i, chunk in enumerate(retrieved_chunks, 1):
                context_parts.append(f"[문서 {i}]")
                context_parts.append(f"파일: {chunk.metadata.get('filename', 'Unknown')}")
                context_parts.append(f"페이지: {chunk.metadata.get('page_number', 'Unknown')}")
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
        @traceable(name="generate_answer")
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
    
    def needs_search(self, query: str) -> bool:
        """
        질문이 문서 검색이 필요한지 판단
        
        Args:
            query: 사용자 질문
            
        Returns:
            bool: 검색이 필요하면 True, Small talk이면 False
        """
        # Small talk 키워드 (검색 불필요)
        smalltalk_keywords = [
            "안녕", "하이", "헬로", "반가워", "고마워", "감사", "고마",
            "날씨", "오늘", "내일", "어제", "시간", "몇 시",
            "기분", "좋아", "싫어", "행복", "슬퍼", "화나",
            "잘 지내", "어떻게 지내", "뭐해", "뭐하니",
            "놀자", "재미", "즐거", "즐거워",
            "고마워", "감사", "미안", "죄송",
            "좋은 하루", "좋은 밤", "잘 자", "안녕히",
            "뭐야", "그게 뭐야", "무엇", "뭔가",
            "재밌", "웃겨", "하하", "헤헤"
        ]
        
        # 문서 검색이 필요한 키워드
        search_keywords = [
            "규정", "정책", "규칙", "규칙", "가이드", "매뉴얼", "매뉴얼",
            "연차", "휴가", "급여", "복지", "혜택", "지원",
            "절차", "프로세스", "방법", "어떻게", "무엇",
            "회사", "사내", "내부", "문서", "자료",
            "찾아", "검색", "알려줘", "알려", "말해줘", "말해",
            "확인", "조회", "조회해", "보여줘", "보여",
            "설명", "설명해", "이해", "이해해"
        ]
        
        query_lower = query.lower()
        
        # Small talk 키워드가 포함되어 있고 검색 키워드가 없으면 Small talk
        has_smalltalk = any(keyword in query_lower for keyword in smalltalk_keywords)
        has_search = any(keyword in query_lower for keyword in search_keywords)
        
        # 검색 키워드가 있으면 무조건 검색 필요
        if has_search:
            return True
        
        # 검색 키워드가 없고 Small talk 키워드가 있으면 Small talk
        if has_smalltalk and not has_search:
            return False
        
        # LLM으로 더 정확하게 판단
        try:
            from langchain_core.messages import SystemMessage, HumanMessage
            
            classification_prompt = f"""다음 질문이 회사 문서나 규정을 검색해야 하는 질문인지, 아니면 일상적인 대화(Small talk)인지 판단해주세요.

질문: {query}

회사 문서/규정 검색이 필요한 경우: "SEARCH"
일상적인 대화인 경우: "SMALLTALK"

답변 (SEARCH 또는 SMALLTALK만):"""
            
            messages = [
                SystemMessage(content="당신은 질문을 분류하는 AI입니다. SEARCH 또는 SMALLTALK만 반환하세요."),
                HumanMessage(content=classification_prompt)
            ]
            
            response = self.llm.invoke(messages)
            result = response.content.strip().upper()
            needs_search = result == "SEARCH"
            
            logger.info(f"질문 분류: '{query}' -> {'RAG 검색' if needs_search else 'Small talk'}")
            return needs_search
            
        except Exception as e:
            logger.warning(f"질문 분류 중 오류: {e}, 기본값으로 RAG 검색 사용")
            # 오류 발생 시 안전하게 RAG 검색 사용
            return True
    
    @traceable(name="smalltalk_query")  # LangSmith 추적
    def query_smalltalk(self, query: str) -> str:
        """
        Small talk 질문에 대한 답변 생성 (LLM만 사용)
        
        Args:
            query: 사용자 질문
            
        Returns:
            str: 생성된 답변
        """
        try:
            answer = self.smalltalk_chain.invoke({"query": query})
            return answer
        except Exception as e:
            logger.error(f"Small talk 답변 생성 중 오류: {e}")
            return "죄송합니다. 일시적인 오류가 발생했습니다."
    
    @traceable(
        name="rag_query_full",
        metadata={
            "component": "RAG System",
            "version": "1.0"
        }
    )
    def query(self, request: QueryRequest) -> QueryResponse:
        """
        질의응답 전체 프로세스 (검색 필요 여부에 따라 RAG 또는 LLM 단독 사용)
        
        Args:
            request: 질의응답 요청
            
        Returns:
            QueryResponse: 질의응답 응답
        """
        start_time = time.time()
        
        try:
            # 문서 검색 필요: RAG 실행
            logger.info(f"문서 검색 필요: '{request.query}' -> RAG 실행")
            
            # LangChain 체인 실행 (동적 threshold는 자동 계산)
            result = self.rag_chain.invoke({
                "query": request.query,
                "top_k": request.top_k or self.config.RAG_TOP_K
            })
            
            answer = result["answer"]
            retrieved_chunks = result["retrieved_chunks"]
            
            # 검색 결과가 없을 때: Small talk 사용하지 않고 "정보 없음" 메시지
            if not retrieved_chunks:
                logger.warning(f"검색 결과 없음: '{request.query}' -> 정보 부족 메시지 반환")
                answer = "죄송합니다. 질문하신 내용과 관련된 문서를 찾을 수 없습니다. 다른 질문을 해주시거나, 더 구체적으로 질문해주세요."
            
            # 처리 시간 계산
            processing_time = time.time() - start_time
            
            # LangSmith에 메타데이터 전달을 위해 dict로 변환
            response = QueryResponse(
                query=request.query,
                answer=answer,
                retrieved_chunks=retrieved_chunks,
                processing_time=processing_time,
                model_used=self.config.OPENAI_MODEL
            )
            
            # 실시간 평가 수행 (터미널 출력용)
            # 실시간 평가 수행 (터미널 출력용) - 비활성화 (속도 개선 및 토큰 절약)
            # try:
            #     print("\n" + "="*50)
            #     print("🔍 실시간 RAG 답변 평가 수행 중...")
            #     # Ground Truth 조회 (평가용으로만 사용)
            #     ground_truth = self.evaluator.lookup_ground_truth(request.query)
                
            #     eval_result = self.evaluator.evaluate_single(
            #         question=request.query,
            #         answer=answer,
            #         context="\n".join([chunk.text for chunk in retrieved_chunks]),
            #         ground_truth=ground_truth
            #     )
            #     print(f"  - 정확성 (Faithfulness): {eval_result.get('faithfulness_score')}점")
            #     print(f"  - 완전성 (Completeness): {eval_result.get('completeness_score')}점")
            #     print(f"  - 연관성 (Answer Relevancy): {eval_result.get('answer_relevancy_score')}점")
            #     print(f"  - 정밀도 (Context Precision): {eval_result.get('context_precision_score')}점")
            #     print(f"  - 일치도 (Answer Correctness): {eval_result.get('answer_correctness_score')}점")
                
            #     # 결과 JSON 저장
            #     try:
            #         timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                    
            #         # 절대 경로 계산: backend/data/HR_RAG/HR_RAG_result
            #         current_dir = os.path.dirname(os.path.abspath(__file__))
            #         # backend/app/domain/rag/HR -> ... -> backend
            #         backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_dir))))
            #         result_dir = os.path.join(backend_dir, "data", "HR_RAG", "HR_RAG_result")
                    
            #         os.makedirs(result_dir, exist_ok=True)
                    
            #         result_file = os.path.join(result_dir, f"evaluation_{timestamp}.json")
                    
            #         # 저장할 데이터 구성
            #         save_data = {
            #             "timestamp": timestamp,
            #             "query": request.query,
            #             "answer": answer,
            #             "retrieved_chunks": [
            #                 {
            #                     "filename": chunk.metadata.get("filename", "Unknown"),
            #                     "page": chunk.metadata.get("page_number", "?"),
            #                     "score": chunk.score,
            #                     "text": chunk.text
            #                 } for chunk in retrieved_chunks
            #             ],
            #             "ground_truth": ground_truth,
            #             "evaluation": eval_result
            #         }
                    
            #         with open(result_file, 'w', encoding='utf-8') as f:
            #             json.dump(save_data, f, ensure_ascii=False, indent=4)
                        
            #         logger.info(f"평가 결과 저장 완료: {result_file}")
            #         print(f"  - 결과 파일 저장: {result_file}")
                    
            #     except Exception as save_e:
            #         logger.error(f"평가 결과 저장 실패: {save_e}")
            #         print(f"  - 결과 파일 저장 실패: {save_e}")

            #     print("="*50 + "\n")
                    
            # except Exception as eval_e:
            #     logger.warning(f"실시간 평가 중 오류 발생: {eval_e}")
            #     print(f"❌ 실시간 평가 중 오류 발생: {eval_e}")
            #     print("="*50 + "\n")
            
            # LangSmith 메타데이터 로깅
            from langsmith import traceable
            from langsmith.run_helpers import get_current_run_tree
            
            try:
                run_tree = get_current_run_tree()
                if run_tree:
                    run_tree.extra = {
                        "retrieved_chunks_count": len(retrieved_chunks),
                        "chunks": [
                            {
                                "filename": chunk.metadata.get("filename", "Unknown"),
                                "page_number": chunk.metadata.get("page_number", 0),
                                "score": chunk.score
                            }
                            for chunk in retrieved_chunks
                        ],
                        "processing_time": processing_time,
                        "model": self.config.OPENAI_MODEL
                    }
            except Exception as e:
                logger.warning(f"LangSmith 메타데이터 추가 실패: {e}")
            
            return response
            
        except Exception as e:
            logger.exception("질의응답 처리 중 오류")
            processing_time = time.time() - start_time
            
            return QueryResponse(
                query=request.query,
                answer=f"질의응답 처리 중 오류가 발생했습니다: {str(e)}",
                retrieved_chunks=[],
                processing_time=processing_time,
                model_used=self.config.OPENAI_MODEL
            )
    
