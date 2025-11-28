"""
고급 검색 Retriever (Threshold 기반)
"""
import os
from typing import List, Dict, Any, Optional
from app.infrastructure.vector_store_advanced import get_vector_store
from ingestion.embed_flexible import get_embedding_service


SIMILARITY_THRESHOLD = float(os.getenv("SIMILARITY_THRESHOLD", "0.78"))


class AdvancedRetriever:
    def __init__(self, model_type: Optional[str] = None, api_key: Optional[str] = None):
        self.embedding_service = get_embedding_service(model_type, api_key)
        self.vector_store = get_vector_store()
        self.threshold = SIMILARITY_THRESHOLD
    
    def search(
        self,
        query: str,
        n_results: int = 5,
        filters: Optional[Dict[str, Any]] = None,
        threshold: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        query_embedding = self.embedding_service.embed_text(query)
        threshold = threshold or self.threshold
        
        results = self.vector_store.search(
            query_embedding=query_embedding,
            n_results=n_results,
            filters=filters,
            threshold=threshold
        )
        
        return results
    
    def search_by_date(
        self,
        query: str,
        date: str,
        n_results: int = 5
    ) -> List[Dict[str, Any]]:
        return self.search(query, n_results, filters={"date": date})
    
    def search_by_chunk_type(
        self,
        query: str,
        chunk_type: str,
        n_results: int = 5
    ) -> List[Dict[str, Any]]:
        return self.search(query, n_results, filters={"chunk_type": chunk_type})
    
    def search_by_customer(
        self,
        query: str,
        customer: str,
        n_results: int = 5
    ) -> List[Dict[str, Any]]:
        results = self.search(query, n_results * 2)
        filtered = [
            r for r in results
            if customer in r["metadata"].get("customers", [])
        ]
        return filtered[:n_results]

