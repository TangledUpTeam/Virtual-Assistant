"""
RAG API 엔드포인트

PDF 업로드, 문서 처리, 질의응답 API를 제공합니다.
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from pathlib import Path
import shutil
from typing import Optional

from app.domain.rag.config import rag_config
from app.domain.rag.pdf_processor import PDFProcessor
from app.domain.rag.document_converter import DocumentConverter
from app.domain.rag.vector_store import VectorStore
from app.domain.rag.retriever import RAGRetriever
from app.domain.rag.schemas import (
    QueryRequest,
    QueryResponse,
    UploadResponse
)
from app.domain.rag.utils import get_logger

logger = get_logger(__name__)

router = APIRouter()

# 전역 인스턴스 (lazy loading)
_pdf_processor = None
_document_converter = None
_vector_store = None
_retriever = None

def get_pdf_processor():
    """PDF 프로세서 lazy loading"""
    global _pdf_processor
    if _pdf_processor is None:
        _pdf_processor = PDFProcessor()
        logger.info("PDFProcessor 인스턴스 생성")
    return _pdf_processor

def get_document_converter():
    """문서 변환기 lazy loading"""
    global _document_converter
    if _document_converter is None:
        _document_converter = DocumentConverter()
        logger.info("DocumentConverter 인스턴스 생성")
    return _document_converter

def get_vector_store():
    """벡터 저장소 lazy loading"""
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore()
        logger.info("VectorStore 인스턴스 생성")
    return _vector_store

def get_retriever():
    """RAG 검색기 lazy loading"""
    global _retriever
    if _retriever is None:
        _retriever = RAGRetriever()
        logger.info("RAGRetriever 인스턴스 생성")
    return _retriever


@router.post("/upload", response_model=UploadResponse)
async def upload_pdf(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...)
):
    """
    PDF 파일 업로드 및 처리
    
    Args:
        file: 업로드할 PDF 파일
        
    Returns:
        UploadResponse: 업로드 결과
    """
    # 파일 확장자 확인
    if not file.filename.endswith('.pdf'):
        raise HTTPException(
            status_code=400,
            detail="PDF 파일만 업로드 가능합니다."
        )
    
    try:
        # 파일 저장
        upload_path = rag_config.UPLOAD_DIR / file.filename
        
        with upload_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        logger.info(f"파일 업로드 완료: {file.filename}")
        
        # 인스턴스 lazy loading
        pdf_processor = get_pdf_processor()
        document_converter = get_document_converter()
        vector_store = get_vector_store()
        
        # PDF 처리 (동기)
        processed_doc = pdf_processor.process_pdf(str(upload_path))
        
        # 청킹
        chunks = document_converter.create_chunks(processed_doc)
        
        # 벡터 저장 (임베딩 재사용 가능)
        added_count = vector_store.add_document(processed_doc, chunks)
        
        # 임베딩과 함께 JSON 저장
        pdf_processor.save_chunks_with_embeddings(processed_doc, chunks)
        
        # 처리된 파일 경로
        processed_file_path = str(
            rag_config.PROCESSED_DIR / f"{Path(file.filename).stem}.json"
        )
        
        response = UploadResponse(
            success=True,
            message="PDF 처리 완료",
            filename=file.filename,
            total_pages=processed_doc.total_pages,
            total_chunks=added_count,
            processed_file_path=processed_file_path
        )
        
        return response
        
    except Exception as e:
        logger.exception("PDF 업로드 중 오류")
        raise HTTPException(
            status_code=500,
            detail=f"PDF 처리 중 오류가 발생했습니다: {str(e)}"
        )


@router.post("/query", response_model=QueryResponse)
async def query_rag(request: QueryRequest):
    """
    RAG 기반 질의응답
    
    동적 threshold가 항상 활성화되어 검색 결과에 따라 자동으로 조정됩니다.
    
    Args:
        request: 질의응답 요청
        
    Returns:
        QueryResponse: 질의응답 결과
    """
    try:
        logger.info(f"질의응답 요청: {request.query} (동적 threshold 자동 적용)")
        
        # 인스턴스 lazy loading
        retriever = get_retriever()
        
        response = retriever.query(request)
        
        return response
        
    except Exception as e:
        logger.exception("질의응답 중 오류")
        raise HTTPException(
            status_code=500,
            detail=f"질의응답 처리 중 오류가 발생했습니다: {str(e)}"
        )


@router.get("/stats")
async def get_stats():
    """
    RAG 시스템 통계
    
    Returns:
        dict: 시스템 통계
    """
    try:
        # 인스턴스 lazy loading
        vector_store = get_vector_store()
        
        doc_count = vector_store.count_documents()
        
        stats = {
            "total_chunks": doc_count,
            "collection_name": rag_config.CHROMA_COLLECTION_NAME,
            "embedding_model": rag_config.EMBEDDING_MODEL,
            "translation_model": rag_config.TRANSLATION_MODEL,
            "llm_model": rag_config.OPENAI_MODEL,
            "top_k": rag_config.RAG_TOP_K,
            "dynamic_threshold_range": f"{rag_config.RAG_MIN_SIMILARITY_THRESHOLD} ~ {rag_config.RAG_MAX_SIMILARITY_THRESHOLD}",
            "chunk_size": rag_config.RAG_CHUNK_SIZE,
            "chunk_overlap": rag_config.RAG_CHUNK_OVERLAP
        }
        
        return stats
        
    except Exception as e:
        logger.exception("통계 조회 중 오류")
        raise HTTPException(
            status_code=500,
            detail=f"통계 조회 중 오류가 발생했습니다: {str(e)}"
        )


@router.delete("/document/{document_id}")
async def delete_document(document_id: str):
    """
    문서 삭제
    
    Args:
        document_id: 문서 ID
        
    Returns:
        dict: 삭제 결과
    """
    try:
        # 인스턴스 lazy loading
        vector_store = get_vector_store()
        
        success = vector_store.delete_document(document_id)
        
        if success:
            return {
                "success": True,
                "message": f"문서 '{document_id}'가 삭제되었습니다."
            }
        else:
            raise HTTPException(
                status_code=404,
                detail=f"문서를 찾을 수 없습니다: {document_id}"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("문서 삭제 중 오류")
        raise HTTPException(
            status_code=500,
            detail=f"문서 삭제 중 오류가 발생했습니다: {str(e)}"
        )


@router.post("/reset")
async def reset_collection():
    """
    컬렉션 초기화 (모든 문서 삭제)
    
    주의: 이 작업은 되돌릴 수 없습니다!
    
    Returns:
        dict: 초기화 결과
    """
    try:
        # 인스턴스 lazy loading
        vector_store = get_vector_store()
        
        vector_store.reset_collection()
        
        return {
            "success": True,
            "message": "컬렉션이 초기화되었습니다."
        }
        
    except Exception as e:
        logger.exception("컬렉션 초기화 중 오류")
        raise HTTPException(
            status_code=500,
            detail=f"컬렉션 초기화 중 오류가 발생했습니다: {str(e)}"
        )

