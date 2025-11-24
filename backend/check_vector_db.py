"""
벡터 DB 확인 스크립트

unified_documents 컬렉션에 데이터가 있는지 확인합니다. (로컬 ChromaDB)
"""
import sys
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

from ingestion.chroma_client import get_chroma_service

try:
    print("=" * 60)
    print("📊 벡터 DB 상태 확인 (로컬 ChromaDB)")
    print("=" * 60)
    
    # ChromaDB 클라이언트 가져오기
    chroma = get_chroma_service()
    
    # unified_documents 컬렉션 확인
    collection = chroma.get_or_create_collection('unified_documents')
    count = collection.count()
    
    print(f"\n📦 컬렉션: unified_documents")
    print(f"📝 문서 개수: {count}개")
    
    if count > 0:
        print(f"\n✅ 벡터 DB에 데이터가 있습니다!")
        
        # 샘플 데이터 확인
        try:
            result = collection.peek(limit=5)
            print(f"\n📄 샘플 데이터 (최대 5개):")
            for i, doc in enumerate(result["documents"][:5], 1):
                preview = doc[:80] + "..." if len(doc) > 80 else doc
                metadata = result["metadatas"][i-1] if result.get("metadatas") else {}
                chunk_type = metadata.get("chunk_type", "N/A")
                date = metadata.get("date", "N/A")
                print(f"  {i}. [{chunk_type}] {date}")
                print(f"     {preview}")
        except Exception as e:
            print(f"  샘플 데이터 조회 실패: {e}")
    else:
        print(f"\n⚠️  벡터 DB가 비어있습니다!")
        print(f"\n데이터 추가 방법:")
        print(f"  python -m ingestion.ingest_daily_reports")
    
    print("\n" + "=" * 60)
    
except Exception as e:
    print(f"\n❌ 오류 발생: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

