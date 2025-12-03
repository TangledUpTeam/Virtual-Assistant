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


router = APIRouter(prefix="/plan", tags=["plan"])


@router.post("/today", response_model=TodayPlanResponse)
async def generate_today_plan(
    request: TodayPlanRequest,
    db: Session = Depends(get_db)
) -> TodayPlanResponse:
    """
    오늘의 일정 플래닝 (Agent 기반)
    
    전날의 미종결 업무와 익일 계획을 기반으로
    오늘 하루 일정을 AI가 자동 플래닝합니다.
    
    Args:
        request: 일정 생성 요청
        db: 데이터베이스 세션
        
    Returns:
        생성된 일정
    """
    try:
        # ReportPlanningAgent 사용
        from multi_agent.agents.report_tools import get_planning_agent
        
        planning_agent = get_planning_agent()
        
        result_dict = planning_agent.generate_plan_sync(
            owner=request.owner,
            target_date=request.target_date
        )
        
        # TodayPlanResponse 포맷으로 변환
        from app.domain.report.planner.schemas import PlanTask
        
        tasks = [PlanTask(**task) for task in result_dict["tasks"]]
        
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
