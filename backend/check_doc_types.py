"""
unified_documents 컬렉션의 doc_type 별 문서 개수 확인
"""
import sys
from pathlib import Path
from collections import Counter

project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

from ingestion.chroma_client import get_chroma_service

try:
    chroma = get_chroma_service()
    collection = chroma.get_or_create_collection('unified_documents')

    print("=" * 70)
    print(f"📊 unified_documents 컬렉션 분석")
    print("=" * 70)
    print(f"총 문서 수: {collection.count()}개\n")

    # 모든 메타데이터 가져오기
    print("⏳ 메타데이터 분석 중...")
    results = collection.get(limit=10000, include=["metadatas"])

    # doc_type별 카운트
    doc_types = Counter()
    for metadata in results['metadatas']:
        doc_type = metadata.get('doc_type', 'unknown')
        doc_types[doc_type] += 1

    print("\n📦 doc_type 별 문서 개수:")
    for doc_type, count in sorted(doc_types.items()):
        print(f"  - {doc_type}: {count}개")

    print("\n" + "=" * 70)

    # KPI 샘플 데이터 확인
    print("\n🔍 KPI 샘플 데이터 확인:")
    kpi_results = collection.get(
        where={"doc_type": "kpi"},
        limit=3,
        include=["documents", "metadatas"]
    )

    if kpi_results['documents']:
        print(f"✅ KPI 데이터 발견: {len(kpi_results['documents'])}개 샘플\n")
        for i, (doc, meta) in enumerate(zip(kpi_results['documents'][:3], kpi_results['metadatas'][:3]), 1):
            kpi_name = meta.get('kpi_name', 'N/A')
            category = meta.get('category', 'N/A')
            print(f"  [{i}] {kpi_name} (카테고리: {category})")
            print(f"      text: {doc[:80]}...")
            print()
    else:
        print("❌ KPI 데이터가 없습니다!")

    print("=" * 70)

except Exception as e:
    print(f"❌ 오류 발생: {e}")
    import traceback
    traceback.print_exc()

