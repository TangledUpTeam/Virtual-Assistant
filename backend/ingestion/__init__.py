"""
Ingestion 모듈

Chroma Cloud에 문서를 임베딩하고 업로드하는 파이프라인
"""
from ingestion.embed import embed_text, embed_texts, get_embedding_service
from ingestion.chroma_client import (
    get_chroma_service,
    get_reports_collection,
    get_kpi_collection
)
from ingestion.ingest_reports import ingest_reports, delete_reports_by_ids, query_reports
from ingestion.ingest_kpi import ingest_kpi, delete_kpi_by_ids, query_kpi

__all__ = [
    # Embedding
    "embed_text",
    "embed_texts",
    "get_embedding_service",
    
    # Chroma Client
    "get_chroma_service",
    "get_reports_collection",
    "get_kpi_collection",
    
    # Reports Ingestion
    "ingest_reports",
    "delete_reports_by_ids",
    "query_reports",
    
    # KPI Ingestion
    "ingest_kpi",
    "delete_kpi_by_ids",
    "query_kpi",
]

