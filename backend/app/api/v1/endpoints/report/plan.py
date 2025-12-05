"""
Plan API Endpoint

Generates today's plan based on recent reports and recommendations.
"""
from fastapi import APIRouter, HTTPException, Depends
from datetime import date
from sqlalchemy.orm import Session

from app.domain.report.planner.schemas import TodayPlanRequest, TodayPlanResponse, TaskItem, TaskSource
from app.infrastructure.database.session import get_db
from app.domain.auth.dependencies import get_current_user_optional
from app.domain.user.models import User


router = APIRouter(prefix="/plan", tags=["plan"])


@router.post("/today", response_model=TodayPlanResponse)
async def generate_today_plan(
    request: TodayPlanRequest,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional)
) -> TodayPlanResponse:
    """
    Generate today's plan (agent powered).

    Owner resolution rule:
    - Authenticated user: use current_user.name
    - Unauthenticated: fall back to request.owner
    """
    try:
        resolved_owner: str | None = None
        if current_user and current_user.name:
            resolved_owner = current_user.name
            print(f"✅ 인증된 사용자 이름 사용: {resolved_owner}")
        elif request.owner:
            resolved_owner = request.owner
            print(f"👤 Request의 owner 사용: {resolved_owner}")

        if not resolved_owner:
            raise HTTPException(
                status_code=400,
                detail="owner가 필요합니다. (로그인 사용자 또는 request.owner 중 하나가 필요합니다.)"
            )

        target_date = request.target_date or date.today()

        # ReportPlanningAgent 사용
        from multi_agent.agents.report_tools import get_planning_agent

        planning_agent = get_planning_agent()

        result_dict = planning_agent.generate_plan_sync(
            owner=resolved_owner,
            target_date=target_date
        )

        tasks = [TaskItem(**task) for task in result_dict["tasks"]]
        task_sources = [TaskSource(**source) for source in result_dict.get("task_sources", [])]

        return TodayPlanResponse(
            tasks=tasks,
            summary=result_dict["summary"],
            source_date=result_dict["source_date"],
            owner=result_dict["owner"],
            target_date=result_dict["target_date"],
            task_sources=task_sources
        )

    except Exception as e:
        print(f"[ERROR] Today plan generation failed: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"일정 생성 실패: {str(e)}"
        )


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok", "service": "plan"}
