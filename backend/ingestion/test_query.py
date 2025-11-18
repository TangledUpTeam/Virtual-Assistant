"""
Chroma Cloud 검색 테스트 스크립트

업로드된 문서를 쿼리하여 검색 결과 확인
"""
import os
import sys
import codecs
from pathlib import Path
from dotenv import load_dotenv

# Windows CMD에서 UTF-8 출력 설정
if sys.platform == "win32":
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.buffer, "strict")

# 프로젝트 루트를 Python Path에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from ingestion.ingest_reports import query_reports
from ingestion.ingest_kpi import query_kpi


def test_reports_query():
    """보고서 컬렉션 검색 테스트"""
    print("=" * 70)
    print("📄 보고서 컬렉션 검색 테스트")
    print("=" * 70)
    print()
    
    # 테스트 쿼리들
    queries = [
        "주요 업무 성과는?",
        "영업 실적 목표",
        "해결이 필요한 문제점"
    ]
    
    for i, query in enumerate(queries, 1):
        print(f"[쿼리 {i}] {query}")
        print("-" * 70)
        
        results = query_reports(query_text=query, n_results=3)
        
        if results and results.get("documents"):
            docs = results["documents"][0]
            metadatas = results["metadatas"][0]
            distances = results["distances"][0]
            
            for j, (doc, meta, dist) in enumerate(zip(docs, metadatas, distances), 1):
                print(f"\n  결과 {j} (거리: {dist:.4f}):")
                print(f"  메타데이터: {meta}")
                print(f"  내용: {doc[:200]}...")
        else:
            print("  검색 결과가 없습니다.")
        
        print()
    
    print()


def test_kpi_query():
    """KPI 컬렉션 검색 테스트"""
    print("=" * 70)
    print("📊 KPI 컬렉션 검색 테스트")
    print("=" * 70)
    print()
    
    # 테스트 쿼리들
    queries = [
        "손해율 지표",
        "보험료 수입",
        "고객 만족도"
    ]
    
    for i, query in enumerate(queries, 1):
        print(f"[쿼리 {i}] {query}")
        print("-" * 70)
        
        results = query_kpi(query_text=query, n_results=3)
        
        if results and results.get("documents"):
            docs = results["documents"][0]
            metadatas = results["metadatas"][0]
            distances = results["distances"][0]
            
            for j, (doc, meta, dist) in enumerate(zip(docs, metadatas, distances), 1):
                print(f"\n  결과 {j} (거리: {dist:.4f}):")
                print(f"  메타데이터: {meta}")
                print(f"  내용: {doc[:200]}...")
        else:
            print("  검색 결과가 없습니다.")
        
        print()
    
    print()


def main():
    """검색 테스트 실행"""
    # .env 파일 로드
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    
    if not api_key:
        print("❌ OPENAI_API_KEY 환경변수가 설정되지 않았습니다.")
        sys.exit(1)
    
    # 보고서 검색 테스트
    test_reports_query()
    
    # KPI 검색 테스트
    test_kpi_query()
    
    print("=" * 70)
    print("✅ 검색 테스트 완료")
    print("=" * 70)


if __name__ == "__main__":
    main()

