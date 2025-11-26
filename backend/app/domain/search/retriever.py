"""
Unified Retriever

unified_documents 컬렉션에서 doc_type별로 검색을 수행합니다.

Author: AI Assistant
Created: 2025-11-18
"""
from typing import List, Optional, Dict, Any
from datetime import date
from pydantic import BaseModel, Field
from chromadb import Collection
import openai
import os


class UnifiedSearchResult(BaseModel):
    """통합 검색 결과"""
    chunk_id: str = Field(..., description="청크 ID")
    doc_id: str = Field(..., description="문서 ID")
    doc_type: str = Field(..., description="문서 타입")
    chunk_type: str = Field(..., description="청크 타입")
    text: str = Field(..., description="청크 텍스트")
    score: float = Field(..., description="유사도 점수")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="전체 메타데이터")


class UnifiedRetriever:
    """Unified Documents Retriever"""
    
    def __init__(
        self, 
        collection: Collection,
        openai_api_key: Optional[str] = None,
        embedding_model: str = "text-embedding-3-large"
    ):
        """
        초기화
        
        Args:
            collection: unified_documents Collection 객체
            openai_api_key: OpenAI API 키 (None이면 환경변수에서 가져옴)
            embedding_model: 임베딩 모델명
        """
        self.collection = collection
        self.openai_api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        self.embedding_model = embedding_model
        self.client = openai.OpenAI(api_key=self.openai_api_key)
    
    def search_daily(
        self,
        query: str,
        owner: Optional[str] = None,
        single_date: Optional[str] = None,
        period_start: Optional[str] = None,
        period_end: Optional[str] = None,
        n_results: int = 5,
        chunk_types: Optional[List[str]] = None
    ) -> List[UnifiedSearchResult]:
        """
        일일/주간/월간 보고서 검색
        
        Args:
            query: 검색 쿼리
            owner: 작성자 필터
            single_date: 단일 날짜 (YYYY-MM-DD)
            period_start: 시작 날짜
            period_end: 종료 날짜
            n_results: 결과 개수
            chunk_types: 청크 타입 필터 (예: ["task", "plan"])
            
        Returns:
            검색 결과 리스트
        """
        # Chroma 필터는 $and를 사용해 복잡한 조건 구성
        conditions = []
        
        # doc_type 조건
        conditions.append({
            "doc_type": {"$in": ["daily", "weekly", "monthly", "performance"]}
        })
        
        # chunk_type 필터 (task 타입만 가져오기)
        if chunk_types:
            conditions.append({
                "chunk_type": {"$in": chunk_types}
            })
        
        # owner 필터
        if owner:
            conditions.append({"owner": owner})
        
        # 날짜 필터
        if single_date:
            conditions.append({"date": single_date})
        elif period_start and period_end:
            # 일일보고서는 date 필드를 사용하므로, 기간 내 모든 날짜를 $in으로 검색
            # ChromaDB는 날짜 문자열에 대해 $gte/$lte를 지원하지 않으므로 $in 사용
            from datetime import datetime, timedelta
            start = datetime.strptime(period_start, "%Y-%m-%d")
            end = datetime.strptime(period_end, "%Y-%m-%d")
            date_list = []
            current = start
            while current <= end:
                date_list.append(current.strftime("%Y-%m-%d"))
                current += timedelta(days=1)
            conditions.append({"date": {"$in": date_list}})
        
        # 조건이 하나만 있으면 그대로, 여러개면 $and로 묶기
        if len(conditions) == 1:
            where_filter = conditions[0]
        else:
            where_filter = {"$and": conditions}
        
        return self._execute_search(query, where_filter, n_results)
    
    def search_kpi(
        self,
        query: str,
        category: Optional[str] = None,
        n_results: int = 5
    ) -> List[UnifiedSearchResult]:
        """
        KPI 문서 검색
        
        Args:
            query: 검색 쿼리
            category: KPI 카테고리 필터
            n_results: 결과 개수
            
        Returns:
            검색 결과 리스트
        """
        where_filter = {
            "doc_type": "kpi"
        }
        
        if category:
            where_filter["kpi_category"] = category
        
        return self._execute_search(query, where_filter, n_results)
    
    def search_template(
        self,
        query: str,
        n_results: int = 3
    ) -> List[UnifiedSearchResult]:
        """
        템플릿 문서 검색
        
        Args:
            query: 검색 쿼리
            n_results: 결과 개수
            
        Returns:
            검색 결과 리스트
        """
        where_filter = {
            "doc_type": "template"
        }
        
        return self._execute_search(query, where_filter, n_results)
    
    def search_all(
        self,
        query: str,
        n_results: int = 10
    ) -> List[UnifiedSearchResult]:
        """
        전체 문서 검색 (fallback)
        
        Args:
            query: 검색 쿼리
            n_results: 결과 개수
            
        Returns:
            검색 결과 리스트
        """
        return self._execute_search(query, {}, n_results)
    
    def search_by_doc_type(
        self,
        query: str,
        doc_type: str,
        n_results: int = 5,
        **filters
    ) -> List[UnifiedSearchResult]:
        """
        doc_type 지정 검색 (범용)
        
        Args:
            query: 검색 쿼리
            doc_type: 문서 타입
            n_results: 결과 개수
            **filters: 추가 필터
            
        Returns:
            검색 결과 리스트
        """
        where_filter = {"doc_type": doc_type}
        
        # None이 아닌 필터만 추가
        for key, value in filters.items():
            if value is not None:
                where_filter[key] = value
        
        return self._execute_search(query, where_filter, n_results)
    
    def _get_query_embedding(self, query: str) -> List[float]:
        """
        쿼리를 임베딩으로 변환
        
        Args:
            query: 검색 쿼리
            
        Returns:
            임베딩 벡터
        """
        try:
            response = self.client.embeddings.create(
                input=query,
                model=self.embedding_model
            )
            return response.data[0].embedding
        except Exception as e:
            print(f"[ERROR] Embedding error: {e}")
            raise
    
    def _execute_search(
        self,
        query: str,
        where_filter: Dict[str, Any],
        n_results: int
    ) -> List[UnifiedSearchResult]:
        """
        실제 검색 수행
        
        Args:
            query: 검색 쿼리
            where_filter: Chroma where 필터
            n_results: 결과 개수
            
        Returns:
            검색 결과 리스트
        """
        try:
            # OpenAI로 쿼리 임베딩 생성
            query_embedding = self._get_query_embedding(query)
            
            # Chroma 검색 (임베딩 직접 전달)
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                where=where_filter if where_filter else None
            )
            
            # 결과 변환
            search_results = []
            
            if results and results['ids'] and len(results['ids']) > 0:
                ids = results['ids'][0]
                documents = results['documents'][0]
                metadatas = results['metadatas'][0]
                distances = results['distances'][0]
                
                for i in range(len(ids)):
                    # 거리를 유사도 점수로 변환 (낮을수록 유사 → 높을수록 유사)
                    score = 1.0 / (1.0 + distances[i])
                    
                    search_results.append(
                        UnifiedSearchResult(
                            chunk_id=ids[i],
                            doc_id=metadatas[i].get("doc_id", ""),
                            doc_type=metadatas[i].get("doc_type", ""),
                            chunk_type=metadatas[i].get("chunk_type", ""),
                            text=documents[i],
                            score=score,
                            metadata=metadatas[i]
                        )
                    )
            
            return search_results
        
        except Exception as e:
            print(f"[ERROR] Search error: {e}")
            return []

