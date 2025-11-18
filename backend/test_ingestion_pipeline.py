"""
Ingestion 파이프라인 전체 테스트

1. JSON 청크 파일 로드
2. Chroma Cloud 연결
3. Reports 업로드
4. KPI 업로드
5. 검색 테스트
"""
import os
import sys
import json
import codecs
from pathlib import Path
from dotenv import load_dotenv

# Windows CMD에서 UTF-8 출력 설정
if sys.platform == "win32":
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.buffer, "strict")

# 프로젝트 루트를 Python Path에 추가
sys.path.insert(0, str(Path(__file__).parent))

from ingestion.ingest_reports import ingest_reports, query_reports
from ingestion.ingest_kpi import ingest_kpi, query_kpi
from ingestion.chroma_client import get_chroma_service


def load_chunks_from_json(json_path: str) -> list:
    """JSON 파일에서 청크 데이터 로드"""
    print(f"📂 파일 로드 중: {json_path}")
    
    if not Path(json_path).exists():
        print(f"❌ 파일을 찾을 수 없습니다: {json_path}")
        return []
    
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    # 청크 구조 변환
    chunks = []
    
    if isinstance(data, list):
        for item in data:
            chunk = {
                "id": item.get("chunk_id", item.get("id", "")),
                "chunk_text": item.get("text", item.get("chunk_text", "")),
                "metadata": item.get("metadata", {})
            }
            chunks.append(chunk)
    
    print(f"✅ 로드 완료: {len(chunks)}개 청크")
    return chunks


def test_reports_ingestion(api_key: str):
    """보고서 ingestion 테스트"""
    print("\n" + "=" * 70)
    print("📄 보고서 Ingestion 테스트")
    print("=" * 70)
    
    # 청크 파일 로드
    chunks_path = "output/실적 보고서 양식_performance_chunks.json"
    chunks = load_chunks_from_json(chunks_path)
    
    if not chunks:
        print("⚠️  청크가 없어 테스트를 건너뜁니다.")
        return None
    
    # Ingestion 실행
    result = ingest_reports(chunks, api_key=api_key, batch_size=50)
    
    if result["success"]:
        print(f"✅ 업로드 성공: {result['uploaded']}개 청크")
        print(f"📊 컬렉션 총 문서 수: {result['total_documents']}개")
    else:
        print(f"❌ 업로드 실패: {result.get('message', 'Unknown error')}")
    
    return result


def test_kpi_ingestion(api_key: str):
    """KPI ingestion 테스트"""
    print("\n" + "=" * 70)
    print("📊 KPI Ingestion 테스트")
    print("=" * 70)
    
    # 청크 파일 로드
    chunks_path = "output/KPI 자료_kpi_chunks.json"
    chunks = load_chunks_from_json(chunks_path)
    
    if not chunks:
        print("⚠️  청크가 없어 테스트를 건너뜁니다.")
        return None
    
    # Ingestion 실행
    result = ingest_kpi(chunks, api_key=api_key, batch_size=50)
    
    if result["success"]:
        print(f"✅ 업로드 성공: {result['uploaded']}개 청크")
        print(f"📊 컬렉션 총 문서 수: {result['total_documents']}개")
    else:
        print(f"❌ 업로드 실패: {result.get('message', 'Unknown error')}")
    
    return result


def test_search():
    """검색 테스트"""
    print("\n" + "=" * 70)
    print("🔍 검색 테스트")
    print("=" * 70)
    
    # 보고서 검색 테스트
    print("\n[보고서 검색]")
    print("-" * 70)
    
    query = "주요 업무 성과"
    print(f"쿼리: '{query}'")
    
    try:
        results = query_reports(query_text=query, n_results=3)
        
        if results and results.get("documents") and results["documents"][0]:
            docs = results["documents"][0]
            metadatas = results["metadatas"][0]
            distances = results["distances"][0]
            
            print(f"✅ 검색 결과: {len(docs)}개")
            
            for i, (doc, meta, dist) in enumerate(zip(docs, metadatas, distances), 1):
                print(f"\n  [{i}] 거리: {dist:.4f}")
                print(f"  메타데이터: {meta}")
                print(f"  내용: {doc[:150]}...")
        else:
            print("⚠️  검색 결과가 없습니다.")
    
    except Exception as e:
        print(f"❌ 검색 오류: {e}")
    
    # KPI 검색 테스트
    print("\n[KPI 검색]")
    print("-" * 70)
    
    query = "손해율"
    print(f"쿼리: '{query}'")
    
    try:
        results = query_kpi(query_text=query, n_results=3)
        
        if results and results.get("documents") and results["documents"][0]:
            docs = results["documents"][0]
            metadatas = results["metadatas"][0]
            distances = results["distances"][0]
            
            print(f"✅ 검색 결과: {len(docs)}개")
            
            for i, (doc, meta, dist) in enumerate(zip(docs, metadatas, distances), 1):
                print(f"\n  [{i}] 거리: {dist:.4f}")
                print(f"  메타데이터: {meta}")
                print(f"  내용: {doc[:150]}...")
        else:
            print("⚠️  검색 결과가 없습니다.")
    
    except Exception as e:
        print(f"❌ 검색 오류: {e}")


def main():
    """전체 파이프라인 테스트"""
    print("=" * 70)
    print("🚀 Ingestion 파이프라인 통합 테스트 시작")
    print("=" * 70)
    print()
    
    # .env 파일 로드
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    
    if not api_key:
        print("❌ OPENAI_API_KEY 환경변수가 설정되지 않았습니다.")
        print("💡 .env 파일에 OPENAI_API_KEY를 추가하세요.")
        sys.exit(1)
    
    print(f"✅ OpenAI API 키 확인됨: {api_key[:20]}...")
    
    # Chroma Cloud 연결 확인
    print("\n🔗 Chroma Cloud 연결 확인 중...")
    try:
        chroma_service = get_chroma_service()
        print("✅ Chroma Cloud 연결 성공")
    except Exception as e:
        print(f"❌ Chroma Cloud 연결 실패: {e}")
        sys.exit(1)
    
    # 1. 보고서 ingestion
    reports_result = test_reports_ingestion(api_key)
    
    # 2. KPI ingestion
    kpi_result = test_kpi_ingestion(api_key)
    
    # 3. 검색 테스트
    test_search()
    
    # 최종 요약
    print("\n" + "=" * 70)
    print("✅ 전체 테스트 완료")
    print("=" * 70)
    
    # 컬렉션 현황
    print("\n📊 최종 컬렉션 현황:")
    
    try:
        reports_collection = chroma_service.get_reports_collection()
        kpi_collection = chroma_service.get_kpi_collection()
        
        reports_info = chroma_service.get_collection_info(reports_collection)
        kpi_info = chroma_service.get_collection_info(kpi_collection)
        
        print(f"  - Reports: {reports_info['count']}개 문서")
        print(f"  - KPI: {kpi_info['count']}개 문서")
    except Exception as e:
        print(f"❌ 컬렉션 정보 조회 실패: {e}")
    
    print()
    print("💡 다음 단계:")
    print("  1. 추가 데이터 업로드: python -m ingestion.init_ingest")
    print("  2. 검색 테스트: python -m ingestion.test_query")
    print()


if __name__ == "__main__":
    main()

