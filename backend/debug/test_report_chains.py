"""
보고서 체인 테스트 통합 스크립트

주간/월간/실적 보고서 자동 생성 테스트

사용법:
    python -m debug.test_report_chains --weekly    # 주간
    python -m debug.test_report_chains --monthly   # 월간
    python -m debug.test_report_chains --performance # 실적
    python -m debug.test_report_chains --all       # 모두
"""
import sys
from pathlib import Path
import argparse

# 프로젝트 루트를 Python path에 추가
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from datetime import date
from app.infrastructure.database.session import SessionLocal
from app.domain.weekly.chain import generate_weekly_report
from app.domain.monthly.chain import generate_monthly_report
from app.domain.performance.chain import generate_performance_report
from app.domain.weekly.repository import WeeklyReportRepository
from app.domain.monthly.repository import MonthlyReportRepository
from app.domain.performance.repository import PerformanceReportRepository
from app.domain.weekly.schemas import WeeklyReportCreate
from app.domain.monthly.schemas import MonthlyReportCreate
from app.domain.performance.schemas import PerformanceReportCreate


def test_weekly_chain(owner: str = "김보험", target_date: date = None):
    """주간 보고서 생성 테스트"""
    print("=" * 80)
    print("📊 주간 보고서 Chain 테스트")
    print("=" * 80)
    
    if target_date is None:
        target_date = date.today()
    
    print(f"\n작성자: {owner}, 기준일: {target_date}")
    
    db = SessionLocal()
    
    try:
        # 생성
        print(f"\n⏳ 주간 보고서 생성 중...")
        report = generate_weekly_report(db=db, owner=owner, target_date=target_date)
        
        print(f"✅ 생성 완료!")
        print(f"   기간: {report.period_start} ~ {report.period_end}")
        print(f"   업무: {len(report.tasks)}개, KPI: {len(report.kpis)}개")
        print(f"   이슈: {len(report.issues)}개, 계획: {len(report.plans)}개")
        
        # 저장
        print(f"\n⏳ DB 저장 중...")
        report_dict = report.model_dump(mode='json')
        report_create = WeeklyReportCreate(
            owner=report.owner,
            period_start=report.period_start,
            period_end=report.period_end,
            report_json=report_dict
        )
        db_report, is_created = WeeklyReportRepository.create_or_update(db, report_create)
        action = "생성" if is_created else "업데이트"
        print(f"✅ DB 저장 완료 ({action})")
        
        # PDF 생성
        print(f"\n⏳ PDF 생성 중...")
        from app.reporting.service.report_export_service import ReportExportService
        
        pdf_bytes = ReportExportService.export_weekly_pdf(
            db=db,
            owner=owner,
            period_start=report.period_start,
            period_end=report.period_end
        )
        
        print(f"✅ PDF 생성 완료!")
        print(f"   파일 크기: {len(pdf_bytes):,} bytes")
        print(f"   저장 경로: backend/output/report_result/weekly/")
        
        return True
        
    except Exception as e:
        print(f"❌ 오류: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


def test_monthly_chain(owner: str = "김보험", target_date: date = None):
    """월간 보고서 생성 테스트"""
    print("=" * 80)
    print("📊 월간 보고서 Chain 테스트")
    print("=" * 80)
    
    if target_date is None:
        target_date = date.today()
    
    print(f"\n작성자: {owner}, 기준일: {target_date}")
    
    db = SessionLocal()
    
    try:
        # 생성
        print(f"\n⏳ 월간 보고서 생성 중...")
        report = generate_monthly_report(db=db, owner=owner, target_date=target_date)
        
        print(f"✅ 생성 완료!")
        print(f"   기간: {report.period_start} ~ {report.period_end}")
        print(f"   업무: {len(report.tasks)}개, KPI: {len(report.kpis)}개")
        print(f"   이슈: {len(report.issues)}개, 계획: {len(report.plans)}개")
        
        # 저장
        print(f"\n⏳ DB 저장 중...")
        report_dict = report.model_dump(mode='json')
        report_create = MonthlyReportCreate(
            owner=report.owner,
            period_start=report.period_start,
            period_end=report.period_end,
            report_json=report_dict
        )
        db_report, is_created = MonthlyReportRepository.create_or_update(db, report_create)
        action = "생성" if is_created else "업데이트"
        print(f"✅ DB 저장 완료 ({action})")
        
        # PDF 생성
        print(f"\n⏳ PDF 생성 중...")
        from app.reporting.service.report_export_service import ReportExportService
        
        pdf_bytes = ReportExportService.export_monthly_pdf(
            db=db,
            owner=owner,
            period_start=report.period_start,
            period_end=report.period_end
        )
        
        print(f"✅ PDF 생성 완료!")
        print(f"   파일 크기: {len(pdf_bytes):,} bytes")
        print(f"   저장 경로: backend/output/report_result/monthly/")
        
        return True
        
    except Exception as e:
        print(f"❌ 오류: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


def test_performance_chain(owner: str = "김보험", period_start: date = None, period_end: date = None):
    """실적 보고서 생성 테스트"""
    print("=" * 80)
    print("📊 실적 보고서 Chain 테스트")
    print("=" * 80)
    
    if period_start is None:
        today = date.today()
        period_start = date(today.year, today.month, 1)
        period_end = today
    
    print(f"\n작성자: {owner}")
    print(f"기간: {period_start} ~ {period_end}")
    
    db = SessionLocal()
    
    try:
        # 생성
        print(f"\n⏳ 실적 보고서 생성 중...")
        report = generate_performance_report(
            db=db,
            owner=owner,
            period_start=period_start,
            period_end=period_end
        )
        
        print(f"✅ 생성 완료!")
        print(f"   업무: {len(report.tasks)}개, KPI: {len(report.kpis)}개")
        print(f"   이슈: {len(report.issues)}개, 계획: {len(report.plans)}개")
        
        # KPI 샘플
        if report.kpis:
            print(f"\n📈 KPI 샘플 (최대 3개):")
            for idx, kpi in enumerate(report.kpis[:3], 1):
                print(f"   {idx}. {kpi.kpi_name}: {kpi.value}")
        
        # 저장
        print(f"\n⏳ DB 저장 중...")
        report_dict = report.model_dump(mode='json')
        report_create = PerformanceReportCreate(
            owner=report.owner,
            period_start=report.period_start,
            period_end=report.period_end,
            report_json=report_dict
        )
        db_report, is_created = PerformanceReportRepository.create_or_update(db, report_create)
        action = "생성" if is_created else "업데이트"
        print(f"✅ DB 저장 완료 ({action})")
        
        return True
        
    except Exception as e:
        print(f"❌ 오류: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(description='보고서 체인 테스트')
    parser.add_argument('--weekly', action='store_true', help='주간 보고서 테스트')
    parser.add_argument('--monthly', action='store_true', help='월간 보고서 테스트')
    parser.add_argument('--performance', action='store_true', help='실적 보고서 테스트')
    parser.add_argument('--all', action='store_true', help='모두 테스트')
    parser.add_argument('--owner', default='김보험', help='작성자')
    parser.add_argument('--date', type=str, help='기준 날짜 (YYYY-MM-DD, 예: 2025-11-18)')
    args = parser.parse_args()
    
    # 날짜 파싱
    target_date = None
    if args.date:
        from datetime import datetime
        try:
            target_date = datetime.strptime(args.date, '%Y-%m-%d').date()
            print(f"📅 지정된 날짜: {target_date}")
        except ValueError:
            print(f"❌ 잘못된 날짜 형식: {args.date} (YYYY-MM-DD 형식을 사용하세요)")
            return
    
    print()
    print("=" * 80)
    print("🔬 보고서 체인 테스트")
    print("=" * 80)
    print()
    
    results = []
    
    if args.weekly or args.all:
        results.append(('주간', test_weekly_chain(args.owner, target_date)))
        print()
    
    if args.monthly or args.all:
        results.append(('월간', test_monthly_chain(args.owner, target_date)))
        print()
    
    if args.performance or args.all:
        results.append(('실적', test_performance_chain(args.owner)))
        print()
    
    if not any([args.weekly, args.monthly, args.performance, args.all]):
        print("⚠️  테스트할 보고서 타입을 지정해주세요.")
        print("   예: python -m debug.test_report_chains --all")
        return
    
    # 결과 요약
    print("=" * 80)
    print("📊 테스트 결과 요약")
    print("=" * 80)
    for name, success in results:
        status = "✅ 성공" if success else "❌ 실패"
        print(f"   {name} 보고서: {status}")
    print()


if __name__ == "__main__":
    main()

