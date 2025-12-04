"""
Plan API 엔드포인트

일정 계획 및 플래닝 API

Author: AI Assistant
Created: 2025-11-18
Updated: 2025-12-03 (Agent 기반으로 변경)
"""
from fastapi import APIRouter, HTTPException, Depends
from datetime import date
from sqlalchemy.orm import Session

from app.domain.report.planner.schemas import TodayPlanRequest, TodayPlanResponse
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
    오늘의 일정 플래닝 (Agent 기반)
    
    전날의 미종결 업무와 익일 계획을 기반으로
    오늘 하루 일정을 AI가 자동 플래닝합니다.
    
    인증된 사용자가 있으면 해당 사용자 이름을 사용하고,
    없으면 request의 owner를 사용합니다.
    
    Args:
        request: 일정 생성 요청 (owner 포함)
        db: 데이터베이스 세션
        current_user: 현재 로그인한 사용자 (선택적)
        
    Returns:
        생성된 일정
    """
    try:
        # owner 결정: 인증된 사용자가 있으면 해당 사용자 이름 사용, 없으면 request의 owner 사용
        if current_user and current_user.name:
            owner = current_user.name
            print(f"✅ 인증된 사용자 이름 사용: {owner}")
        elif request.owner:
            owner = request.owner
            print(f"ℹ️  Request의 owner 사용: {owner}")
        else:
            raise HTTPException(
                status_code=400,
                detail="owner가 필요합니다. (인증되지 않았거나 request에 owner가 없습니다.)"
            )
        
        # ReportPlanningAgent 사용
        from multi_agent.agents.report_tools import get_planning_agent
        
        planning_agent = get_planning_agent()
        
        result_dict = planning_agent.generate_plan_sync(
            owner=owner,  # 로그인한 사용자 이름 사용
            target_date=request.target_date
        )
        
        # TodayPlanResponse 포맷으로 변환
        from app.domain.report.planner.schemas import TaskItem
        
        tasks = [TaskItem(**task) for task in result_dict["tasks"]]
        
        return TodayPlanResponse(
            tasks=tasks,
            summary=result_dict["summary"],
            source_date=result_dict["source_date"],
            owner=result_dict["owner"]
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
    """Health check 엔드포인트"""
    return {"status": "ok", "service": "plan"}
