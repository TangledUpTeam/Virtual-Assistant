"""
Plan API Endpoint

Generates today's plan based on recent reports and recommendations.
"""
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.v1.endpoints.report.utils import resolve_owner_name
from app.domain.auth.dependencies import get_current_user_optional
from app.domain.report.planner.schemas import (
    TaskItem,
    TaskSource,
    TodayPlanRequest,
    TodayPlanResponse,
)
from app.domain.user.models import User
from app.infrastructure.database.session import get_db


router = APIRouter(prefix="/plan", tags=["plan"])


@router.post("/today", response_model=TodayPlanResponse)
async def generate_today_plan(
    request: TodayPlanRequest,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
) -> TodayPlanResponse:
    """
    Generate today's plan (agent powered).

    Owner resolution rule:
    - Authenticated user: use current_user.name
    - Else resolve by owner_id
    - Else request.owner
    """
    try:
        # 디버깅: 전달된 값 확인
        print(f"[DEBUG] Plan API - current_user: {current_user.name if current_user else None}")
        print(f"[DEBUG] Plan API - request.owner: {request.owner}")
        print(f"[DEBUG] Plan API - request.owner_id: {request.owner_id}")
        
        resolved_owner = resolve_owner_name(
            db=db,
            current_user=current_user,
            owner=request.owner,
            owner_id=request.owner_id,
        )
        
        print(f"[DEBUG] Plan API - resolved_owner: {resolved_owner}")

        target_date = request.target_date or date.today()

        # ReportPlanningAgent 사용
        from multi_agent.agents.report_tools import get_planning_agent

        planning_agent = get_planning_agent()

        result_dict = planning_agent.generate_plan_sync(
            owner=resolved_owner,
            target_date=target_date,
        )

        tasks = [TaskItem(**task) for task in result_dict["tasks"]]
        task_sources = [
            TaskSource(**source) for source in result_dict.get("task_sources", [])
        ]

        return TodayPlanResponse(
            tasks=tasks,
            summary=result_dict["summary"],
            source_date=result_dict["source_date"],
            owner=result_dict["owner"],
            target_date=result_dict["target_date"],
            task_sources=task_sources,
        )

    except Exception as e:
        import traceback

        print(f"[ERROR] Today plan generation failed: {e}")
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Plan generation failed: {str(e)}",
        )


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok", "service": "plan"}
