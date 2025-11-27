"""
Performance Report API

실적 보고서 자동 생성 API

Author: AI Assistant
Created: 2025-11-19
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from datetime import date
from sqlalchemy.orm import Session
from pathlib import Path
import os

from app.domain.performance.chain import generate_performance_report
from app.domain.performance.repository import PerformanceReportRepository
from app.domain.performance.schemas import PerformanceReportCreate, PerformanceReportResponse, PerformanceReportListResponse
from app.domain.report.schemas import CanonicalReport
from app.infrastructure.database.session import get_db
from app.reporting.pdf_generator.performance_report_pdf import PerformanceReportPDFGenerator


router = APIRouter(prefix="/performance", tags=["performance_report"])


class PerformanceReportGenerateRequest(BaseModel):
    """실적 보고서 생성 요청"""
    owner: str = Field(..., description="작성자")
    year: int = Field(..., description="연도")


class PerformanceReportGenerateResponse(BaseModel):
    """실적 보고서 생성 응답"""
    success: bool
    message: str
    report: CanonicalReport


@router.post("/generate", response_model=PerformanceReportGenerateResponse)
async def generate_performance(
    request: PerformanceReportGenerateRequest,
    db: Session = Depends(get_db)
):
    """
    실적 보고서 자동 생성
    
    지정된 기간의 일일보고서를 집계하여 KPI 중심의 실적 보고서를 생성하고 DB에 저장합니다.
    """
    try:
        # 해당 연도의 마지막 날짜를 target_date로 사용 (매년 마지막 주에 작성)
        target_date = date(request.year, 12, 31)
        
        # 1. 실적 보고서 생성 (target_date가 속한 연도의 1월 1일~12월 31일 데이터 자동 수집)
        report = generate_performance_report(
            db=db,
            owner=request.owner,
            target_date=target_date
        )
        
        # 2. DB에 저장
        report_dict = report.model_dump(mode='json')
        report_create = PerformanceReportCreate(
            owner=report.owner,
            period_start=report.period_start,
            period_end=report.period_end,
            report_json=report_dict
        )
        
        db_report, is_created = PerformanceReportRepository.create_or_update(
            db, report_create
        )
        
        action = "생성" if is_created else "업데이트"
        print(f"💾 실적 보고서 저장 완료 ({action}): {report.owner} - {report.period_start}~{report.period_end}")
        
        # 🔥 3. PDF 자동 생성 및 저장
        try:
            # PDF 생성 (파일명만 지정, 경로는 Generator가 처리)
            pdf_filename = f"{report.owner}_{report.period_start}_{report.period_end}_실적보고서.pdf"
            
            pdf_generator = PerformanceReportPDFGenerator()
            pdf_bytes = pdf_generator.generate(report, pdf_filename)
            
            print(f"📄 실적 보고서 PDF 생성 완료: backend/output/report_result/performance/{pdf_filename}")
        except Exception as pdf_error:
            print(f"⚠️  PDF 생성 실패 (보고서는 저장됨): {str(pdf_error)}")
        
        return PerformanceReportGenerateResponse(
            success=True,
            message=f"실적 보고서가 {action}되었습니다.",
            report=report
        )
    
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"실적 보고서 생성 실패: {str(e)}")


@router.get("/list/{owner}", response_model=PerformanceReportListResponse)
async def list_performance_reports(
    owner: str,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    작성자의 실적 보고서 목록 조회
    """
    try:
        reports = PerformanceReportRepository.list_by_owner(db, owner, skip, limit)
        total = PerformanceReportRepository.count_by_owner(db, owner)
        
        report_responses = [PerformanceReportResponse(**report.to_dict()) for report in reports]
        
        return PerformanceReportListResponse(
            total=total,
            reports=report_responses
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"목록 조회 실패: {str(e)}")


@router.get("/health")
async def health_check():
    """Health check"""
    return {"status": "ok", "service": "performance_report"}

