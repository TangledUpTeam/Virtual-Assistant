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

from app.domain.performance.chain import generate_performance_report
from app.domain.performance.repository import PerformanceReportRepository
from app.domain.performance.schemas import PerformanceReportCreate, PerformanceReportResponse, PerformanceReportListResponse
from app.domain.report.schemas import CanonicalReport
from app.infrastructure.database.session import get_db


router = APIRouter(prefix="/performance", tags=["performance_report"])


class PerformanceReportGenerateRequest(BaseModel):
    """실적 보고서 생성 요청"""
    owner: str = Field(..., description="작성자")
    period_start: date = Field(..., description="시작일")
    period_end: date = Field(..., description="종료일")


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
        # 1. 실적 보고서 생성
        report = generate_performance_report(
            db=db,
            owner=request.owner,
            period_start=request.period_start,
            period_end=request.period_end
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

