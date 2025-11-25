"""
자동 Ingestion 유틸리티

일일보고서 완료 시 자동으로 벡터DB에 저장하는 함수들
"""
import os
from typing import Dict, Any
from datetime import date

from app.domain.report.schemas import CanonicalReport
from app.domain.report.chunker import chunk_report
from ingestion.embed import embed_texts
from ingestion.chroma_client import get_chroma_service


COLLECTION_NAME = "unified_documents"
BATCH_SIZE = 50


def ingest_single_report(
    report: CanonicalReport,
    api_key: str = None
) -> Dict[str, Any]:
    """
    단일 보고서를 벡터DB에 자동 저장
    
    Args:
        report: CanonicalReport 객체
        api_key: OpenAI API 키 (None이면 환경변수에서 읽음)
        
    Returns:
        업로드 결과 딕셔너리
    """
    try:
        print(f"\n📤 [자동 Ingestion] 시작: {report.owner} - {report.period_start}")
        
        # 1. 청킹
        print("  ⏳ 청킹 중...")
        chunks = chunk_report(report)
        
        if not chunks:
            print("  ⚠️  생성된 청크가 없습니다.")
            return {"success": False, "message": "No chunks generated"}
        
        print(f"  ✅ {len(chunks)}개 청크 생성 완료")
        
        # 2. 데이터 추출
        ids = [chunk["id"] for chunk in chunks]
        texts = [chunk["text"] for chunk in chunks]  # 🔥 "text" 키 사용
        metadatas = [chunk["metadata"] for chunk in chunks]
        
        # 메타데이터 정리 (ChromaDB는 None 값 불허)
        for metadata in metadatas:
            # None 값 제거
            metadata_cleaned = {k: v for k, v in metadata.items() if v is not None}
            metadata.clear()
            metadata.update(metadata_cleaned)
        
        # 3. 임베딩 생성
        print("  ⏳ 임베딩 생성 중...")
        
        if api_key is None:
            api_key = os.getenv("OPENAI_API_KEY")
        
        embeddings = embed_texts(texts, api_key=api_key, batch_size=BATCH_SIZE)
        print(f"  ✅ {len(embeddings)}개 임베딩 생성 완료")
        
        # 4. Chroma 업로드
        print("  ⏳ 벡터DB 업로드 중...")
        chroma_service = get_chroma_service()
        collection = chroma_service.get_or_create_collection(name=COLLECTION_NAME)
        
        # 배치 업로드
        total = len(chunks)
        for i in range(0, total, BATCH_SIZE):
            batch_end = min(i + BATCH_SIZE, total)
            
            batch_ids = ids[i:batch_end]
            batch_embeddings = embeddings[i:batch_end]
            batch_documents = texts[i:batch_end]
            batch_metadatas = metadatas[i:batch_end]
            
            collection.upsert(
                ids=batch_ids,
                embeddings=batch_embeddings,
                documents=batch_documents,
                metadatas=batch_metadatas
            )
        
        print(f"  ✅ 벡터DB 업로드 완료: {total}개 청크")
        print(f"  📦 컬렉션 총 문서 수: {collection.count()}개\n")
        
        return {
            "success": True,
            "collection": COLLECTION_NAME,
            "uploaded_chunks": total,
            "total_documents": collection.count()
        }
        
    except Exception as e:
        print(f"  ❌ 자동 Ingestion 실패: {e}\n")
        return {
            "success": False,
            "message": f"Ingestion failed: {str(e)}",
            "error": str(e)
        }


def ingest_single_report_silent(
    report: CanonicalReport,
    api_key: str = None
) -> bool:
    """
    단일 보고서를 벡터DB에 저장 (로그 최소화 버전)
    
    Args:
        report: CanonicalReport 객체
        api_key: OpenAI API 키
        
    Returns:
        성공 여부 (True/False)
    """
    try:
        # 청킹
        chunks = chunk_report(report)
        
        if not chunks:
            return False
        
        # 데이터 추출
        ids = [chunk["id"] for chunk in chunks]
        texts = [chunk["text"] for chunk in chunks]  # 🔥 "text" 키 사용
        metadatas = [chunk["metadata"] for chunk in chunks]
        
        # 메타데이터 정리 (ChromaDB는 None 값 불허)
        for metadata in metadatas:
            metadata_cleaned = {k: v for k, v in metadata.items() if v is not None}
            metadata.clear()
            metadata.update(metadata_cleaned)
        
        # 임베딩 생성
        if api_key is None:
            api_key = os.getenv("OPENAI_API_KEY")
        
        embeddings = embed_texts(texts, api_key=api_key, batch_size=BATCH_SIZE)
        
        # Chroma 업로드
        chroma_service = get_chroma_service()
        collection = chroma_service.get_or_create_collection(name=COLLECTION_NAME)
        
        # 배치 업로드
        total = len(chunks)
        for i in range(0, total, BATCH_SIZE):
            batch_end = min(i + BATCH_SIZE, total)
            
            collection.upsert(
                ids=ids[i:batch_end],
                embeddings=embeddings[i:batch_end],
                documents=texts[i:batch_end],
                metadatas=metadatas[i:batch_end]
            )
        
        return True
        
    except Exception as e:
        print(f"❌ 벡터DB 자동 저장 실패: {e}")
        return False

