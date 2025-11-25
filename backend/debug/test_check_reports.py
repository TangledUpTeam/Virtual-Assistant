"""
보고서 데이터 확인 통합 스크립트

PostgreSQL과 VectorDB의 보고서 데이터를 확인합니다.

사용법:
    python -m debug.test_check_reports
    python -m debug.test_check_reports --daily    # 일일보고서만
    python -m debug.test_check_reports --vector   # 벡터DB만
"""
import sys
import os
from pathlib import Path
from datetime import date, timedelta
import argparse

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

# .env 로드
from dotenv import load_dotenv
load_dotenv()

from app.infrastructure.database.session import SessionLocal
from app.domain.daily.repository import DailyReportRepository
from ingestion.chroma_client import get_chroma_service


def check_postgres_reports(owner: str = "김보험"):
    """PostgreSQL 보고서 확인"""
    print("=" * 80)
    print("📊 PostgreSQL 보고서 확인")
    print("=" * 80)
    print()
    
    db = SessionLocal()
    
    try:
        today = date.today()
        yesterday = today - timedelta(days=1)
        
        print(f"🔍 검색 조건:")
        print(f"   Owner: {owner}")
        print(f"   오늘: {today}")
        print(f"   전날: {yesterday}")
        print()
        
        # 1. 전날 데이터 확인
        yesterday_report = DailyReportRepository.get_by_owner_and_date(db, owner, yesterday)
        
        if yesterday_report:
            print(f"✅ 전날({yesterday}) 데이터 발견!")
            report_json = yesterday_report.report_json
            issues = report_json.get("issues", [])
            tasks = report_json.get("tasks", [])
            plans = report_json.get("plans", [])
            metadata = report_json.get("metadata", {})
            
            print(f"   - 업무: {len(tasks)}개")
            print(f"   - 예정 업무: {len(plans)}개")
            print(f"   - 미종결: {len(issues)}개")
            if issues:
                for i, issue in enumerate(issues[:3], 1):
                    print(f"     {i}. {issue}")
            print()
        else:
            print(f"❌ 전날({yesterday}) 데이터 없음\n")
        
        # 2. 최근 10개 확인
        print(f"📋 최근 보고서 10개:")
        recent_reports = DailyReportRepository.list_by_owner(db, owner, skip=0, limit=10)
        
        if recent_reports:
            for report in recent_reports:
                days_ago = (today - report.date).days
                status = "🔵" if days_ago == 0 else "🟢" if days_ago <= 7 else "⚪"
                print(f"   {status} {report.date} ({days_ago}일 전)")
            print()
        else:
            print(f"   ⚠️  {owner}의 보고서 없음\n")
        
        # 3. 전체 개수
        total_count = DailyReportRepository.count_by_owner(db, owner)
        print(f"📊 전체 보고서: {total_count}개")
        print()
        
    except Exception as e:
        print(f"❌ 오류: {e}\n")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


def check_vector_db():
    """VectorDB 보고서 확인"""
    print("=" * 80)
    print("📊 VectorDB 보고서 확인")
    print("=" * 80)
    print()
    
    try:
        chroma = get_chroma_service()
        collection = chroma.get_or_create_collection('unified_documents')
        total_count = collection.count()
        
        print(f"📦 unified_documents 컬렉션:")
        print(f"   총 문서 수: {total_count}개")
        print()
        
        if total_count == 0:
            print("⚠️  벡터DB에 문서가 없습니다.")
            print("   일일보고서를 작성하면 자동으로 저장됩니다.\n")
            return
        
        # 타입별 확인
        print("📋 문서 타입별 분포:")
        doc_types = ['daily', 'weekly', 'monthly', 'performance']
        
        for doc_type in doc_types:
            try:
                results = collection.get(
                    where={"doc_type": doc_type},
                    limit=1
                )
                if results and results['ids']:
                    # 전체 개수는 정확히 알 수 없으므로 "1개 이상" 표시
                    print(f"   ✅ {doc_type}: 있음")
                else:
                    print(f"   ⚪ {doc_type}: 없음")
            except:
                print(f"   ❓ {doc_type}: 확인 실패")
        print()
        
        # 최근 문서 샘플 (5개)
        print("📄 최근 문서 샘플:")
        results = collection.get(limit=5, include=["metadatas", "documents"])
        
        for i, (doc_id, meta, doc) in enumerate(zip(
            results['ids'],
            results['metadatas'],
            results['documents']
        ), 1):
            print(f"   [{i}] {meta.get('chunk_type', 'N/A')} - {meta.get('owner', 'N/A')}")
            print(f"       날짜: {meta.get('period_start', 'N/A')}")
            print(f"       미리보기: {doc[:80]}...")
        print()
        
    except Exception as e:
        print(f"❌ 오류: {e}\n")
        import traceback
        traceback.print_exc()


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(description='보고서 데이터 확인')
    parser.add_argument('--daily', action='store_true', help='PostgreSQL만 확인')
    parser.add_argument('--vector', action='store_true', help='VectorDB만 확인')
    parser.add_argument('--owner', default='김보험', help='Owner 이름')
    args = parser.parse_args()
    
    print()
    print("=" * 80)
    print("🔍 보고서 데이터 확인")
    print("=" * 80)
    print()
    
    if args.daily:
        check_postgres_reports(args.owner)
    elif args.vector:
        check_vector_db()
    else:
        # 둘 다 확인
        check_postgres_reports(args.owner)
        check_vector_db()
    
    print("=" * 80)
    print("✅ 확인 완료")
    print("=" * 80)
    print()


if __name__ == "__main__":
    main()

