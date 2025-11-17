"""
RAG 검색 모듈

ChromaDB에서 관련 문서를 검색하고 OpenAI API로 답변을 생성합니다.
"""

from typing import List, Optional
import time
from openai import OpenAI

from .config import rag_config
from .vector_store import VectorStore
from .schemas import QueryRequest, QueryResponse, RetrievedChunk
from .utils import get_logger

logger = get_logger(__name__)


class RAGRetriever:
    """RAG 기반 검색 및 답변 생성"""
    
    def __init__(self, collection_name: Optional[str] = None):
        self.config = rag_config
        self.vector_store = VectorStore(collection_name)
        self.openai_client = OpenAI(api_key=self.config.OPENAI_API_KEY)
    
    def retrieve(self, query: str, top_k: Optional[int] = None) -> List[RetrievedChunk]:
        """
        쿼리로 관련 문서 청크 검색
        
        Args:
            query: 검색 쿼리
            top_k: 반환할 결과 수
            
        Returns:
            List[RetrievedChunk]: 검색된 청크 리스트
        """
        if top_k is None:
            top_k = self.config.RAG_TOP_K
        
        logger.info(f"문서 검색 중: '{query}' (Top-{top_k})")
        
        # 벡터 검색
        results = self.vector_store.search(query, top_k)
        
        # 결과 변환
        retrieved_chunks = []
        
        if results and results['documents'] and results['documents'][0]:
            for i in range(len(results['documents'][0])):
                chunk = RetrievedChunk(
                    text=results['documents'][0][i],
                    metadata=results['metadatas'][0][i],
                    score=1.0 - results['distances'][0][i]  # 거리를 유사도로 변환
                )
                retrieved_chunks.append(chunk)
        
        logger.info(f"{len(retrieved_chunks)}개 청크 검색 완료")
        return retrieved_chunks
    
    def generate_answer(
        self, 
        query: str, 
        retrieved_chunks: List[RetrievedChunk]
    ) -> str:
        """
        검색된 청크를 기반으로 답변 생성
        
        Args:
            query: 사용자 질문
            retrieved_chunks: 검색된 청크
            
        Returns:
            str: 생성된 답변
        """
        if not retrieved_chunks:
            return "죄송합니다. 관련된 정보를 찾을 수 없습니다."
        
        # 컨텍스트 구성
        context_parts = []
        for i, chunk in enumerate(retrieved_chunks, 1):
            context_parts.append(f"[문서 {i}]")
            context_parts.append(f"파일: {chunk.metadata.get('filename', 'Unknown')}")
            context_parts.append(f"페이지: {chunk.metadata.get('page_number', 'Unknown')}")
            context_parts.append(f"내용:\n{chunk.text}")
            context_parts.append("")
        
        context = "\n".join(context_parts)
        
        # 프롬프트 구성
        system_prompt = """당신은 문서 내용을 기반으로 정확하게 답변하는 AI 어시스턴트입니다.

다음 규칙을 따라주세요:
1. 제공된 문서 내용만을 기반으로 답변하세요.
2. 문서에 없는 내용은 추측하지 마세요.
3. 답변 시 관련된 문서 번호를 언급하세요. (예: [문서 1]에 따르면...)
4. 명확하고 구조화된 답변을 제공하세요.
5. 한국어로 답변하세요."""

        user_prompt = f"""다음 문서들을 참고하여 질문에 답변해주세요.

{context}

질문: {query}

답변:"""

        try:
            # OpenAI API 호출
            response = self.openai_client.chat.completions.create(
                model=self.config.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=self.config.OPENAI_TEMPERATURE,
                max_tokens=self.config.OPENAI_MAX_TOKENS
            )
            
            answer = response.choices[0].message.content
            return answer
            
        except Exception as e:
            logger.error(f"답변 생성 중 오류: {e}")
            return f"답변 생성 중 오류가 발생했습니다: {str(e)}"
    
    def query(self, request: QueryRequest) -> QueryResponse:
        """
        질의응답 전체 프로세스
        
        Args:
            request: 질의응답 요청
            
        Returns:
            QueryResponse: 질의응답 응답
        """
        start_time = time.time()
        
        # 1. 문서 검색
        retrieved_chunks = self.retrieve(request.query, request.top_k)
        
        # 2. 답변 생성
        answer = self.generate_answer(request.query, retrieved_chunks)
        
        # 3. 처리 시간 계산
        processing_time = time.time() - start_time
        
        response = QueryResponse(
            query=request.query,
            answer=answer,
            retrieved_chunks=retrieved_chunks,
            processing_time=processing_time,
            model_used=self.config.OPENAI_MODEL
        )
        
        return response
    
    def query_simple(self, query: str, top_k: Optional[int] = None) -> str:
        """
        간단한 질의응답 (답변만 반환)
        
        Args:
            query: 질문
            top_k: 검색할 문서 수
            
        Returns:
            str: 답변
        """
        request = QueryRequest(query=query, top_k=top_k or self.config.RAG_TOP_K)
        response = self.query(request)
        return response.answer

