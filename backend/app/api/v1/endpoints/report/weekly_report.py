"""
Weekly Report API

Generates weekly reports from daily data.
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from datetime import date
from sqlalchemy.orm import Session

from app.domain.report.weekly.chain import generate_weekly_report
from app.domain.report.weekly.repository import WeeklyReportRepository
from app.domain.report.weekly.schemas import WeeklyReportCreate, WeeklyReportResponse, WeeklyReportListResponse
from app.domain.report.core.canonical_models import CanonicalReport
from app.domain.report.common.schemas import ReportMeta, ReportPeriod, ReportEnvelope
from app.infrastructure.database.session import get_db
from app.reporting.html_renderer import render_report_html
from app.domain.auth.dependencies import get_current_user_optional
from app.domain.user.models import User
from urllib.parse import quote


router = APIRouter(prefix="/weekly", tags=["weekly_report"])


class WeeklyReportGenerateRequest(BaseModel):
    """Request body for weekly report generation."""
    owner: str | None = Field(None, description="Owner name (used only when unauthenticated)")
    target_date: date = Field(..., description="Any date within the target week")


class WeeklyReportGenerateResponse(BaseModel):
    """Response body for weekly report generation."""
    role: str = "assistant"
    type: str = "weekly_report"
    message: str
    period: dict | None = None
    report_data: dict | None = None
    owner: str | None = None
    success: bool = True
    report: CanonicalReport | None = None
    envelope: ReportEnvelope


@router.post("/generate", response_model=WeeklyReportGenerateResponse)
async def generate_weekly(
    request: WeeklyReportGenerateRequest,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional)
):
    """
    Generate a weekly report and store it.
    """
    try:
        resolved_owner: str | None = None
        if current_user and current_user.name:
            resolved_owner = current_user.name
            print(f"Authenticated owner resolved: {resolved_owner}")
        elif request.owner:
            resolved_owner = request.owner
            print(f"Request owner used: {resolved_owner}")

        if not resolved_owner:
            raise HTTPException(
                status_code=400,
                detail="owner가 필요합니다. (로그인 사용자 또는 request.owner 중 하나가 필요합니다.)"
            )

        report = generate_weekly_report(
            db=db,
            owner=resolved_owner,
            target_date=request.target_date
        )

        if report.owner != resolved_owner:
            report_dict = report.model_dump(mode="json")
            report_dict["owner"] = resolved_owner
            if "weekly" in report_dict and "header" in report_dict["weekly"]:
                report_dict["weekly"]["header"]["성명"] = resolved_owner

        report_dict = report.model_dump(mode="json")
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
        print(f"Weekly report saved ({action}): {report.owner} - {report.period_start}~{report.period_end}")

        html_path = None
        html_url = None
        html_filename = None
        try:
            html_path = render_report_html(
                report_type="weekly",
                data=report.model_dump(mode="json"),
                output_filename=f"weekly_report_{report.owner}_{report.period_start}.html"
            )

            html_filename = html_path.name
            html_url = f"/static/reports/{quote(html_filename)}"
            print(f"Weekly report HTML generated: {html_path}")
        except Exception as html_error:
            print(f"HTML generation failed (report saved): {str(html_error)}")

        done_tasks = 0
        if report.weekday_tasks:
            for day_tasks in report.weekday_tasks.values():
                if isinstance(day_tasks, list):
                    done_tasks += len(day_tasks)

        return WeeklyReportGenerateResponse(
            role="assistant",
            type="weekly_report",
            message=f"주간 보고서가 {action}되었습니다.",
            period={
                "start": str(report.period_start),
                "end": str(report.period_end),
                "done_tasks": done_tasks
            },
            report_data={
                "url": html_url,
                "file_name": html_filename
            } if html_url else None,
            owner=report.owner,
            success=True,
            report=report,
            envelope=ReportEnvelope(
                meta=ReportMeta(
                    owner=report.owner,
                    period=ReportPeriod(start=str(report.period_start), end=str(report.period_end)),
                    report_type="weekly",
                    report_id=str(report.report_id) if getattr(report, "report_id", None) else None,
                ),
                data=report.model_dump(mode="json"),
                html={"url": html_url, "file_name": html_filename} if html_url else None,
            ),
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
    List weekly reports for an owner.
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
