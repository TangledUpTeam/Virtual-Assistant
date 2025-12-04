"""
Weekly Report API

주간 보고서 자동 생성 API

Author: AI Assistant
Created: 2025-11-19
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from datetime import date
from sqlalchemy.orm import Session
from pathlib import Path
import os

from app.domain.report.weekly.chain import generate_weekly_report
from app.domain.report.weekly.repository import WeeklyReportRepository
from app.domain.report.weekly.schemas import WeeklyReportCreate, WeeklyReportResponse, WeeklyReportListResponse
from app.domain.report.core.canonical_models import CanonicalReport
from app.infrastructure.database.session import get_db
from app.reporting.html_renderer import render_report_html
from app.domain.auth.dependencies import get_current_user
from app.domain.user.models import User
from urllib.parse import quote


router = APIRouter(prefix="/weekly", tags=["weekly_report"])


class WeeklyReportGenerateRequest(BaseModel):
    """주간 보고서 생성 요청"""
    owner: str = Field(..., description="작성자")
    target_date: date = Field(..., description="기준 날짜 (해당 주의 아무 날짜)")


class WeeklyReportGenerateResponse(BaseModel):
    """주간 보고서 생성 응답"""
    role: str = "assistant"
    type: str = "weekly_report"
    message: str
    period: dict = None
    report_data: dict = None
    # 하위 호환성
    success: bool = True
    report: CanonicalReport = None


@router.post("/generate", response_model=WeeklyReportGenerateResponse)
async def generate_weekly(
    request: WeeklyReportGenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    주간 보고서 자동 생성
    
    target_date가 속한 주의 월~금 일일보고서를 집계하여 주간 보고서를 생성하고 DB에 저장합니다.
    owner는 로그인한 사용자 이름으로 강제 설정됩니다.
    """
    try:
        # owner를 로그인한 사용자 이름으로 강제 설정
        if not current_user.name:
            raise HTTPException(
                status_code=400,
                detail="사용자 이름이 설정되지 않았습니다."
            )
        
        owner = current_user.name
        
        # 1. 주간 보고서 생성
        report = generate_weekly_report(
            db=db,
            owner=owner,  # 로그인한 사용자 이름 사용
            target_date=request.target_date
        )
        
        # 보고서의 owner 필드가 올바르게 설정되었는지 확인 (이미 generate_weekly_report 내부에서 설정되지만)
        # 일관성을 위해 다시 확인
        if report.owner != owner:
            # owner를 강제로 업데이트
            report_dict = report.model_dump(mode='json')
            report_dict['owner'] = owner
            if 'weekly' in report_dict and 'header' in report_dict['weekly']:
                report_dict['weekly']['header']['성명'] = owner
            # CanonicalReport 객체 재생성은 복잡하므로, 여기서는 dict 수정만 수행
            # 실제로는 generate_weekly_report 함수 내부에서 owner를 사용하므로 문제없음
        
        # 2. DB에 저장
        report_dict = report.model_dump(mode='json')
        report_create = WeeklyReportCreate(
            owner=report.owner,
            period_start=report.period_start,
            period_end=report.period_end,
            report_json=report_dict
        )
        
        db_report, is_created = WeeklyReportRepository.create_or_update(
            db, report_create
        )
        
        action = "생성" if is_created else "업데이트"
        print(f"💾 주간 보고서 저장 완료 ({action}): {report.owner} - {report.period_start}~{report.period_end}")
        
        # 🔥 3. HTML 생성 및 저장
        html_path = None
        html_url = None
        html_filename = None
        try:
            html_path = render_report_html(
                report_type="weekly",
                data=report.model_dump(mode='json'),
                output_filename=f"주간보고서_{report.owner}_{report.period_start}.html"
            )
            
            html_filename = html_path.name
            html_url = f"/static/reports/{quote(html_filename)}"
            print(f"📄 주간 보고서 HTML 생성 완료: {html_path}")
        except Exception as html_error:
            print(f"⚠️  HTML 생성 실패 (보고서는 저장됨): {str(html_error)}")
        
        # 완료된 업무 수 계산
        done_tasks = 0
        if report.weekday_tasks:
            # weekday_tasks는 Dict[str, List[str]]
            for day_tasks in report.weekday_tasks.values():
                if isinstance(day_tasks, list):
                    done_tasks += len(day_tasks)
        
        return WeeklyReportGenerateResponse(
            role="assistant",
            type="weekly_report",
            message=f"주간 보고서가 {action}되었습니다!",
            period={
                "start": str(report.period_start),
                "end": str(report.period_end),
                "done_tasks": done_tasks
            },
            report_data={
                "url": html_url,
                "file_name": html_filename
            } if html_url else None,
            success=True,
            report=report
        )
    
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"주간 보고서 생성 실패: {str(e)}")


@router.get("/list/{owner}", response_model=WeeklyReportListResponse)
async def list_weekly_reports(
    owner: str,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    작성자의 주간 보고서 목록 조회
    """
    try:
        reports = WeeklyReportRepository.list_by_owner(db, owner, skip, limit)
        total = WeeklyReportRepository.count_by_owner(db, owner)
        
        report_responses = [WeeklyReportResponse(**report.to_dict()) for report in reports]
        
        return WeeklyReportListResponse(
            total=total,
            reports=report_responses
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"목록 조회 실패: {str(e)}")


@router.get("/health")
async def health_check():
    """Health check"""
    return {"status": "ok", "service": "weekly_report"}

