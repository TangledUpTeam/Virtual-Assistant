"""
Insurance RAG Agent - 간단한 구현

보험 관련 질문 → ChromaDB 검색 → LLM으로 답변
"""

from typing import Dict, Any, Optional
import chromadb
import os
from openai import OpenAI
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction
from .base_agent import BaseAgent


class InsuranceRAGAgent(BaseAgent):
    """보험 RAG 에이전트"""

    def __init__(self):
        super().__init__(
            name="insurance",
            description="보험 상품, 청구 절차, 규정, 특약 등 보험 관련 질문에 답변합니다."
        )
        
        # ChromaDB 절대 경로
        chroma_path = "/Users/doyeonkim/Documents/GitHub/Virtual-Assistant/backend/app/domain/rag/Insurance/chroma_db"
        
        # ChromaDB 초기화 (Lazy)
        self._chroma_client = None
        self._collection = None
        self._llm_client = None
        self._chroma_path = chroma_path

    @property
    def chroma_client(self):
        if self._chroma_client is None:
            self._chroma_client = chromadb.PersistentClient(path=self._chroma_path)
        return self._chroma_client

    @property
    def collection(self):
        if self._collection is None:
            # 임베딩 함수 설정 (text-embedding-3-small 사용)
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                # .env에서 읽기
                env_paths = [
                    "/Users/doyeonkim/Documents/GitHub/Virtual-Assistant/.env",
                    "/Users/doyeonkim/Documents/GitHub/Virtual-Assistant/backend/.env",
                ]
                for env_file in env_paths:
                    if os.path.exists(env_file):
                        try:
                            with open(env_file) as f:
                                for line in f:
                                    if line.startswith("OPENAI_API_KEY="):
                                        api_key = line.split("=", 1)[1].strip().strip('"').strip("'")
                                        break
                            if api_key:
                                break
                        except:
                            pass
            
            # ChromaDB OpenAI 임베딩 함수 사용
            try:
                from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction
                ef = OpenAIEmbeddingFunction(
                    api_key=api_key,
                    model_name="text-embedding-3-small"
                )
                self._collection = self.chroma_client.get_collection(
                    name="insurance_manual",
                    embedding_function=ef
                )
            except:
                # 임베딩 함수 설정 안 되면 그냥 가져오기
                self._collection = self.chroma_client.get_collection(
                    name="insurance_manual"
                )
        return self._collection

    @property
    def llm_client(self):
        if self._llm_client is None:
            api_key = os.getenv("OPENAI_API_KEY")
            
            # 환경변수에 없으면 .env 파일에서 읽기
            if not api_key:
                # 상위 디렉토리의 .env 찾기
                env_paths = [
                    "/Users/doyeonkim/Documents/GitHub/Virtual-Assistant/.env",  # 프로젝트 루트
                    "/Users/doyeonkim/Documents/GitHub/Virtual-Assistant/backend/.env",
                ]
                
                for env_file in env_paths:
                    if os.path.exists(env_file):
                        try:
                            with open(env_file) as f:
                                for line in f:
                                    if line.startswith("OPENAI_API_KEY="):
                                        api_key = line.split("=", 1)[1].strip().strip('"').strip("'")
                                        break
                            if api_key:
                                break
                        except:
                            pass
            
            self._llm_client = OpenAI(api_key=api_key)
        return self._llm_client

    async def process(self, query: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        질문 처리
        
        Args:
            query: 사용자 질문
            context: 추가 컨텍스트
            
        Returns:
            답변
        """
        try:
            top_k = context.get("top_k", 5) if context else 5
            
            # 1. ChromaDB에서 검색
            results = self.collection.query(
                query_texts=[query],
                n_results=top_k,
                include=["documents", "distances", "metadatas"]
            )

            # 검색 결과 포맷팅
            documents = []
            if results["documents"] and len(results["documents"]) > 0:
                for i, doc in enumerate(results["documents"][0]):
                    distance = results["distances"][0][i]
                    similarity = max(0, 1 - distance) if distance else 0
                    documents.append({
                        "content": doc,
                        "similarity": similarity
                    })

            # 검색 결과가 없으면
            if not documents:
                return "죄송합니다. 관련된 정보를 찾을 수 없습니다."

            # 2. LLM으로 답변 생성
            context_text = ""
            for i, doc in enumerate(documents, 1):
                similarity_percent = int(doc["similarity"] * 100)
                context_text += f"\n[문서 {i}] (관련도: {similarity_percent}%)\n{doc['content']}"

            system_prompt = """당신은 보험 전문가입니다. 
제공된 문서들을 바탕으로 사용자의 질문에 정확하고 도움이 되는 답변을 해주세요.

- 제공된 문서에 없는 정보는 명확히 말하세요.
- 구체적인 숫자나 조건이 있으면 모두 포함하세요.
- 한국어로 친절하게 답변하세요."""

            user_message = f"""【제공된 문서】
{context_text}

【사용자 질문】
{query}

【답변】"""

            response = self.llm_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.3,
                max_tokens=1024
            )

            return response.choices[0].message.content

        except Exception as e:
            return f"보험 문서 검색 중 오류가 발생했습니다: {str(e)}"

    def get_capabilities(self) -> list:
        return [
            "보험 상품 조회",
            "청구 절차 안내",
            "보험 규정 설명",
            "특약 정보",
            "보험금 보장 범위",
        ]
