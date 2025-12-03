"""
PDF Export 테스트 스크립트

일일/주간/월간/실적 보고서 PDF 생성 smoke-test
"""
import sys
from pathlib import Path

# 프로젝트 루트를 Python path에 추가
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from datetime import date
from app.infrastructure.database.session import SessionLocal
from app.reporting.service.report_export_service import ReportExportService


def test_daily_pdf():
    """일일보고서 PDF 생성 테스트"""
    print("=" * 70)
    print("📄 일일보고서 PDF 테스트")
    print("=" * 70)
    
    db = SessionLocal()
    
    try:
        # 테스트 파라미터
        owner = "김보험"
        report_date = date(2025, 1, 20)
        
        print(f"\n🔍 테스트 파라미터:")
        print(f"  - 작성자: {owner}")
        print(f"  - 날짜: {report_date}")
        
        # PDF 생성
        print(f"\n📝 PDF 생성 중...")
        pdf_bytes = ReportExportService.export_daily_pdf(
            db=db,
            owner=owner,
            report_date=report_date
        )
        
        print(f"✅ PDF 생성 완료!")
        print(f"  - 파일 크기: {len(pdf_bytes):,} bytes")
        
    except ValueError as e:
        print(f"❌ 보고서를 찾을 수 없습니다: {e}")
        print(f"💡 먼저 일일보고서를 생성해주세요 (Daily FSM 사용)")
    
    except Exception as e:
        print(f"❌ PDF 생성 실패: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        db.close()


def test_weekly_pdf():
    """주간보고서 PDF 생성 테스트"""
    print("\n" + "=" * 70)
    print("📄 주간보고서 PDF 테스트")
    print("=" * 70)
    
    db = SessionLocal()
    
    try:
        owner = "김보험"
        period_start = date(2025, 1, 20)  # 월요일
        period_end = date(2025, 1, 24)    # 금요일
        
        print(f"\n🔍 테스트 파라미터:")
        print(f"  - 작성자: {owner}")
        print(f"  - 기간: {period_start} ~ {period_end}")
        
        print(f"\n📝 PDF 생성 중...")
        pdf_bytes = ReportExportService.export_weekly_pdf(
            db=db,
            owner=owner,
            period_start=period_start,
            period_end=period_end
        )
        
        print(f"✅ PDF 생성 완료!")
        print(f"  - 파일 크기: {len(pdf_bytes):,} bytes")
        
    except ValueError as e:
        print(f"❌ 보고서를 찾을 수 없습니다: {e}")
        print(f"💡 먼저 주간보고서를 생성해주세요: python backend/debug/test_weekly_chain.py")
    
    except Exception as e:
        print(f"❌ PDF 생성 실패: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        db.close()


def test_monthly_pdf():
    """월간보고서 PDF 생성 테스트"""
    print("\n" + "=" * 70)
    print("📄 월간보고서 PDF 테스트")
    print("=" * 70)
    
    db = SessionLocal()
    
    try:
        owner = "김보험"
        period_start = date(2025, 1, 1)
        period_end = date(2025, 1, 31)
        
        print(f"\n🔍 테스트 파라미터:")
        print(f"  - 작성자: {owner}")
        print(f"  - 기간: {period_start} ~ {period_end}")
        
        print(f"\n📝 PDF 생성 중...")
        pdf_bytes = ReportExportService.export_monthly_pdf(
            db=db,
            owner=owner,
            period_start=period_start,
            period_end=period_end
        )
        
        print(f"✅ PDF 생성 완료!")
        print(f"  - 파일 크기: {len(pdf_bytes):,} bytes")
        
    except ValueError as e:
        print(f"❌ 보고서를 찾을 수 없습니다: {e}")
        print(f"💡 먼저 월간보고서를 생성해주세요: python backend/debug/test_monthly_chain.py")
    
    except Exception as e:
        print(f"❌ PDF 생성 실패: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        db.close()


def test_performance_pdf():
    """실적보고서 PDF 생성 테스트"""
    print("\n" + "=" * 70)
    print("📄 실적보고서 PDF 테스트")
    print("=" * 70)
    
    db = SessionLocal()
    
    try:
        owner = "김보험"
        period_start = date(2025, 1, 1)
        period_end = date(2025, 1, 31)
        
        print(f"\n🔍 테스트 파라미터:")
        print(f"  - 작성자: {owner}")
        print(f"  - 기간: {period_start} ~ {period_end}")
        
        print(f"\n📝 PDF 생성 중...")
        pdf_bytes = ReportExportService.export_performance_pdf(
            db=db,
            owner=owner,
            period_start=period_start,
            period_end=period_end
        )
        
        print(f"✅ PDF 생성 완료!")
        print(f"  - 파일 크기: {len(pdf_bytes):,} bytes")
        
    except ValueError as e:
        print(f"❌ 보고서를 찾을 수 없습니다: {e}")
        print(f"💡 먼저 실적보고서를 생성해주세요: python backend/debug/test_performance_chain.py")
    
    except Exception as e:
        print(f"❌ PDF 생성 실패: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        db.close()


def main():
    """모든 PDF 테스트 실행"""
    print("🚀 PDF Export 테스트 시작\n")
    
    # 1. 일일보고서
    test_daily_pdf()
    
    # 2. 주간보고서
    test_weekly_pdf()
    
    # 3. 월간보고서
    test_monthly_pdf()
    
    # 4. 실적보고서
    test_performance_pdf()
    
    print("\n" + "=" * 70)
    print("✅ 모든 PDF 테스트 완료!")
    print("=" * 70)
    print("\n💡 생성된 PDF 파일 위치: backend/output_reports/")


if __name__ == "__main__":
    main()

