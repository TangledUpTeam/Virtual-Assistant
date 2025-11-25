"""
일일보고서 PDF 생성 테스트

PostgreSQL에서 최근 보고서를 가져와 PDF로 생성합니다.

실행 방법:
    python -m debug.test_daily_pdf
    python -m debug.test_daily_pdf --owner 김보험 --date 2025-11-25
"""
import sys
from pathlib import Path
import argparse
from datetime import date, timedelta

# 프로젝트 루트
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv()

from app.infrastructure.database.session import SessionLocal
from app.domain.daily.repository import DailyReportRepository
from app.reporting.service.report_export_service import ReportExportService


def test_daily_pdf(owner: str = "김보험", report_date: date = None):
    """일일보고서 PDF 생성 테스트"""
    print("=" * 80)
    print("📄 일일보고서 PDF 생성 테스트")
    print("=" * 80)
    print()
    
    if report_date is None:
        report_date = date.today()
    
    print(f"🔍 검색 조건:")
    print(f"   Owner: {owner}")
    print(f"   Date: {report_date}")
    print()
    
    db = SessionLocal()
    
    try:
        # 보고서 확인
        report = DailyReportRepository.get_by_owner_and_date(db, owner, report_date)
        
        if not report:
            print(f"❌ 보고서를 찾을 수 없습니다.")
            print(f"\n📋 최근 보고서 확인:")
            recent_reports = DailyReportRepository.list_by_owner(db, owner, skip=0, limit=5)
            
            if recent_reports:
                print(f"   최근 {len(recent_reports)}개 보고서:")
                for r in recent_reports:
                    print(f"   - {r.date}")
                
                # 가장 최근 보고서 사용
                report_date = recent_reports[0].date
                print(f"\n✅ 가장 최근 보고서({report_date})로 테스트합니다.")
            else:
                print(f"   ⚠️  {owner}의 보고서가 없습니다.")
                return False
        
        # PDF 생성
        print(f"\n⏳ PDF 생성 중...")
        print("-" * 80)
        
        pdf_bytes = ReportExportService.export_daily_pdf(
            db=db,
            owner=owner,
            report_date=report_date
        )
        
        print("-" * 80)
        print(f"\n✅ PDF 생성 완료!")
        print(f"   파일 크기: {len(pdf_bytes):,} bytes")
        print(f"   저장 경로: backend/output/report_result/daily/")
        print()
        
        return True
        
    except FileNotFoundError as e:
        print(f"\n❌ 템플릿 파일 오류:")
        print(f"   {e}")
        print(f"\n📁 필요한 템플릿: backend/Data/reports/일일 업무 보고서.pdf")
        return False
        
    except Exception as e:
        print(f"\n❌ PDF 생성 실패:")
        print(f"   {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        db.close()


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(description='일일보고서 PDF 테스트')
    parser.add_argument('--owner', default='김보험', help='작성자')
    parser.add_argument('--date', type=str, help='날짜 (YYYY-MM-DD)')
    args = parser.parse_args()
    
    # 날짜 파싱
    if args.date:
        try:
            report_date = date.fromisoformat(args.date)
        except ValueError:
            print(f"❌ 잘못된 날짜 형식: {args.date} (YYYY-MM-DD 형식 사용)")
            return
    else:
        report_date = None
    
    print()
    test_daily_pdf(args.owner, report_date)
    print("=" * 80)
    print()


if __name__ == "__main__":
    main()

