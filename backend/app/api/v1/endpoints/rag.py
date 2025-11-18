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

# 전역 인스턴스 (재사용)
pdf_processor = PDFProcessor()
document_converter = DocumentConverter()
vector_store = VectorStore()
retriever = RAGRetriever()


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
        
        # PDF 처리 (동기)
        processed_doc = pdf_processor.process_pdf(str(upload_path))
        
        # 청킹
        chunks = document_converter.create_chunks(processed_doc)
        
        # 벡터 저장
        added_count = vector_store.add_document(processed_doc, chunks)
        
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
    
    Args:
        request: 질의응답 요청
        
    Returns:
        QueryResponse: 질의응답 결과
    """
    try:
        logger.info(f"질의응답 요청: {request.query}")
        
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
        doc_count = vector_store.count_documents()
        
        stats = {
            "total_chunks": doc_count,
            "collection_name": rag_config.CHROMA_COLLECTION_NAME,
            "embedding_model": rag_config.KOREAN_EMBEDDING_MODEL,
            "llm_model": rag_config.OPENAI_MODEL,
            "top_k": rag_config.RAG_TOP_K,
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

