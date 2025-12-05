"""
Monthly Report API

Generates monthly reports from aggregated daily/weekly data.
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from datetime import date
from sqlalchemy.orm import Session

from app.domain.report.monthly.chain import generate_monthly_report
from app.domain.report.monthly.repository import MonthlyReportRepository
from app.domain.report.monthly.schemas import MonthlyReportCreate, MonthlyReportResponse, MonthlyReportListResponse
from app.domain.report.core.canonical_models import CanonicalReport
from app.domain.report.common.schemas import ReportMeta, ReportPeriod, ReportEnvelope
from app.infrastructure.database.session import get_db
from app.reporting.html_renderer import render_report_html
from app.domain.auth.dependencies import get_current_user_optional
from app.domain.user.models import User
from urllib.parse import quote


router = APIRouter(prefix="/monthly", tags=["monthly_report"])


class MonthlyReportGenerateRequest(BaseModel):
    """Request body for monthly report generation."""
    owner: str | None = Field(None, description="Owner name (used only when unauthenticated)")
    year: int = Field(..., description="Year")
    month: int = Field(..., description="Month (1~12)")


class MonthlyReportGenerateResponse(BaseModel):
    """Response body for monthly report generation."""
    role: str = "assistant"
    type: str = "monthly_report"
    message: str
    period: dict | None = None
    report_data: dict | None = None
    owner: str | None = None
    success: bool = True
    report: CanonicalReport | None = None
    envelope: ReportEnvelope


@router.post("/generate", response_model=MonthlyReportGenerateResponse)
async def generate_monthly(
    request: MonthlyReportGenerateRequest,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional)
):
    """
    Generate a monthly report and store it.
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

        target_date = date(request.year, request.month, 1)

        report = generate_monthly_report(
            db=db,
            owner=resolved_owner,
            target_date=target_date
        )

        report_dict = report.model_dump(mode="json")
        report_create = MonthlyReportCreate(
            owner=report.owner,
            period_start=report.period_start,
            period_end=report.period_end,
            report_json=report_dict
        )

        db_report, is_created = MonthlyReportRepository.create_or_update(
            db, report_create
        )

        action = "생성" if is_created else "업데이트"
        print(f"Monthly report saved ({action}): {report.owner} - {report.period_start}~{report.period_end}")

        html_path = None
        html_url = None
        html_filename = None
        try:
            html_path = render_report_html(
                report_type="monthly",
                data=report.model_dump(mode="json"),
                output_filename=f"monthly_report_{report.owner}_{report.period_start}.html"
            )

            html_filename = html_path.name
            html_url = f"/static/reports/{quote(html_filename)}"
            print(f"Monthly report HTML generated: {html_path}")
        except Exception as html_error:
            print(f"HTML generation failed (report saved): {str(html_error)}")

        done_tasks = 0
        if report.weekly_summaries:
            for week_summary in report.weekly_summaries:
                if week_summary.get("tasks"):
                    done_tasks += len(week_summary["tasks"])

        return MonthlyReportGenerateResponse(
            role="assistant",
            type="monthly_report",
            message=f"월간 보고서가 {action}되었습니다.",
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
                    report_type="monthly",
                    report_id=str(report.report_id) if getattr(report, "report_id", None) else None,
                ),
                data=report.model_dump(mode="json"),
                html={"url": html_url, "file_name": html_filename} if html_url else None,
            ),
        )

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"월간 보고서 생성 실패: {str(e)}")


@router.get("/list/{owner}", response_model=MonthlyReportListResponse)
async def list_monthly_reports(
    owner: str,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    List monthly reports for an owner.
    """
    try:
        reports = MonthlyReportRepository.list_by_owner(db, owner, skip, limit)
        total = MonthlyReportRepository.count_by_owner(db, owner)

        report_responses = [MonthlyReportResponse(**report.to_dict()) for report in reports]

        return MonthlyReportListResponse(
            total=total,
            reports=report_responses
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"목록 조회 실패: {str(e)}")


@router.get("/health")
async def health_check():
    """Health check"""
    return {"status": "ok", "service": "monthly_report"}
