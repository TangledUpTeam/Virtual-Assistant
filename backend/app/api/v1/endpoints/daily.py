"""
Daily Report API

시간대별 일일보고서 입력 API

Author: AI Assistant
Created: 2025-11-18
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import date
from sqlalchemy.orm import Session

from app.domain.daily.fsm_state import DailyFSMContext
from app.domain.daily.time_slots import generate_time_slots
from app.domain.daily.task_parser import TaskParser
from app.domain.daily.daily_fsm import DailyReportFSM
from app.domain.daily.daily_builder import build_daily_report
from app.domain.daily.session_manager import get_session_manager
from app.domain.daily.main_tasks_store import get_main_tasks_store
from app.domain.daily.repository import DailyReportRepository
from app.domain.daily.schemas import DailyReportCreate
from app.llm.client import get_llm
from app.domain.report.schemas import CanonicalReport
from app.infrastructure.database.session import get_db


router = APIRouter(prefix="/daily", tags=["daily"])


# 요청/응답 스키마
class DailyStartRequest(BaseModel):
    """일일보고서 작성 시작 요청"""
    owner: str = Field(..., description="작성자")
    target_date: date = Field(..., description="보고서 날짜")
    time_ranges: List[str] = Field(
        default_factory=list,
        description="시간대 목록 (비어있으면 자동 생성)"
    )


class DailyStartResponse(BaseModel):
    """일일보고서 작성 시작 응답"""
    status: str = Field(default="in_progress", description="항상 in_progress")
    session_id: str
    question: str
    meta: Dict[str, Any] = Field(default_factory=dict, description="메타 정보")


class DailyAnswerRequest(BaseModel):
    """답변 입력 요청"""
    session_id: str = Field(..., description="세션 ID")
    answer: str = Field(..., description="사용자 답변")


class DailyAnswerResponse(BaseModel):
    """답변 입력 응답"""
    status: str = Field(..., description="in_progress 또는 finished")
    session_id: str
    question: Optional[str] = Field(None, description="다음 질문 (finished 시 None)")
    message: Optional[str] = Field(None, description="완료 메시지 (finished 시)")
    meta: Optional[Dict[str, Any]] = Field(None, description="메타 정보")
    report: Optional[CanonicalReport] = Field(None, description="완료 시 보고서")


@router.post("/start", response_model=DailyStartResponse)
async def start_daily_report(request: DailyStartRequest):
    """
    일일보고서 작성 시작
    
    저장소에서 금일 진행 업무(main_tasks)를 자동으로 불러와서
    FSM 세션을 시작하고, 첫 번째 시간대 질문을 반환합니다.
    
    main_tasks는 /select_main_tasks로 미리 저장되어 있어야 합니다.
    """
    try:
        # 시간대 생성 (제공되지 않으면 기본값: 09:00~18:00, 60분 간격)
        time_ranges = request.time_ranges
        if not time_ranges:
            time_ranges = generate_time_slots()  # 기본값 사용
        
        # 저장소에서 main_tasks 불러오기
        store = get_main_tasks_store()
        main_tasks = store.get(
            owner=request.owner,
            target_date=request.target_date
        )
        
        # main_tasks가 없으면 빈 리스트로 설정 (경고 메시지 출력)
        if main_tasks is None:
            print(f"[WARNING] main_tasks가 저장되지 않음: {request.owner}, {request.target_date}")
            main_tasks = []
        
        # FSM 컨텍스트 생성
        context = DailyFSMContext(
            owner=request.owner,
            target_date=request.target_date,
            time_ranges=time_ranges,
            today_main_tasks=main_tasks,
            current_index=0,
            finished=False
        )
        
        # 세션 생성
        session_manager = get_session_manager()
        session_id = session_manager.create_session(context)
        
        # FSM 초기화
        llm_client = get_llm()
        task_parser = TaskParser(llm_client)
        fsm = DailyReportFSM(task_parser)
        
        # 첫 질문 가져오기
        result = fsm.start_session(context)
        
        # 세션 업데이트
        session_manager.update_session(session_id, result["state"])
        
        # 현재 시간대 가져오기
        current_time_range = time_ranges[result["current_index"]] if result["current_index"] < len(time_ranges) else ""
        
        return DailyStartResponse(
            status="in_progress",
            session_id=session_id,
            question=result["question"],
            meta={
                "owner": request.owner,
                "date": request.target_date.isoformat(),
                "time_range": current_time_range,
                "current_index": result["current_index"],
                "total_ranges": result["total_ranges"]
            }
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"세션 시작 실패: {str(e)}")


@router.post("/answer", response_model=DailyAnswerResponse)
async def answer_daily_question(
    request: DailyAnswerRequest,
    db: Session = Depends(get_db)
):
    """
    시간대 질문에 답변
    
    사용자의 답변을 받아서 다음 질문을 반환하거나,
    모든 시간대가 완료되면 최종 보고서를 반환합니다.
    """
    try:
        # 세션 조회
        session_manager = get_session_manager()
        context = session_manager.get_session(request.session_id)
        
        if not context:
            raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다")
        
        # FSM 실행
        llm_client = get_llm()
        task_parser = TaskParser(llm_client)
        fsm = DailyReportFSM(task_parser)
        
        # 답변 처리
        result = fsm.process_answer(context, request.answer)
        
        # 세션 업데이트
        updated_context = result["state"]
        session_manager.update_session(request.session_id, updated_context)
        
        # 완료 여부 확인
        if result["finished"]:
            # 보고서 생성
            report = build_daily_report(
                owner=updated_context.owner,
                target_date=updated_context.target_date,
                main_tasks=updated_context.today_main_tasks,
                time_tasks=updated_context.time_tasks
            )
            
            # 🔥 운영 DB에 저장 (PostgreSQL)
            try:
                report_dict = report.model_dump(mode='json')
                report_create = DailyReportCreate(
                    owner=report.owner,
                    report_date=report.period_start,
                    report_json=report_dict
                )
                db_report, is_created = DailyReportRepository.create_or_update(
                    db, report_create
                )
                action = "생성" if is_created else "업데이트"
                print(f"💾 운영 DB 저장 완료 ({action}): {report.owner} - {report.period_start}")
            except Exception as db_error:
                print(f"⚠️  운영 DB 저장 실패 (계속 진행): {str(db_error)}")
                # DB 저장 실패해도 보고서는 반환 (사용자에게는 성공으로 표시)
            
            # 세션 삭제
            session_manager.delete_session(request.session_id)
            
            return DailyAnswerResponse(
                status="finished",
                session_id=request.session_id,
                message="모든 시간대 입력이 완료되었습니다. 오늘 일일보고서를 정리했어요.",
                report=report
            )
        else:
            # 다음 질문 반환
            current_time_range = updated_context.time_ranges[result["current_index"]] if result["current_index"] < len(updated_context.time_ranges) else ""
            
            return DailyAnswerResponse(
                status="in_progress",
                session_id=request.session_id,
                question=result["question"],
                meta={
                    "time_range": current_time_range,
                    "current_index": result["current_index"],
                    "total_ranges": result["total_ranges"],
                    "tasks_collected": result["tasks_collected"]
                }
            )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"답변 처리 실패: {str(e)}")


class SelectMainTasksRequest(BaseModel):
    """금일 진행 업무 선택 요청"""
    owner: str = Field(..., description="작성자")
    target_date: date = Field(..., description="보고서 날짜")
    main_tasks: List[Dict[str, Any]] = Field(
        ...,
        description="선택된 금일 진행 업무 리스트"
    )


class SelectMainTasksResponse(BaseModel):
    """금일 진행 업무 선택 응답"""
    success: bool
    message: str
    saved_count: int


@router.post("/select_main_tasks", response_model=SelectMainTasksResponse)
async def select_main_tasks(request: SelectMainTasksRequest):
    """
    금일 진행 업무 선택 및 저장
    
    사용자가 TodayPlan Chain에서 추천받은 업무 중 
    실제로 수행할 업무를 선택하여 저장합니다.
    
    저장된 업무는 /daily/start 호출 시 자동으로 불러옵니다.
    """
    try:
        if not request.main_tasks:
            raise HTTPException(
                status_code=400,
                detail="최소 1개 이상의 업무를 선택해주세요."
            )
        
        # 저장소에 저장
        store = get_main_tasks_store()
        store.save(
            owner=request.owner,
            target_date=request.target_date,
            main_tasks=request.main_tasks
        )
        
        return SelectMainTasksResponse(
            success=True,
            message="금일 진행 업무가 저장되었습니다.",
            saved_count=len(request.main_tasks)
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"업무 저장 실패: {str(e)}"
        )


@router.get("/health")
async def health_check():
    """Health check"""
    return {"status": "ok", "service": "daily"}

