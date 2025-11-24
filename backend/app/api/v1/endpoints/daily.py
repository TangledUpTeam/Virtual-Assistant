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
from pathlib import Path
import os

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
from app.reporting.pdf_generator.daily_report_pdf import DailyReportPDFGenerator


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
                time_tasks=updated_context.time_tasks,
                issues=updated_context.issues,
                plans=updated_context.plans
            )
            
            # 🔥 운영 DB에 저장 (PostgreSQL) - 기존 데이터 병합
            try:
                # 기존 보고서 확인 (금일 진행 업무가 이미 저장되어 있을 수 있음)
                existing_report = DailyReportRepository.get_by_owner_and_date(
                    db, report.owner, report.period_start
                )
                
                if existing_report:
                    # 기존 보고서가 있으면 병합
                    print(f"📝 기존 보고서 발견 - 병합 모드")
                    
                    existing_json = existing_report.report_json.copy()
                    report_dict = report.model_dump(mode='json')
                    
                    # 기존 금일 진행 업무 + FSM 시간대별 업무 병합
                    existing_tasks = existing_json.get("tasks", [])
                    new_tasks = report_dict.get("tasks", [])
                    
                    # 중복 제거: task_id 기준
                    merged_tasks = existing_tasks.copy()
                    existing_ids = {t.get("task_id") for t in existing_tasks if t.get("task_id")}
                    
                    for task in new_tasks:
                        if task.get("task_id") not in existing_ids:
                            merged_tasks.append(task)
                    
                    # 병합된 데이터 생성
                    merged_json = {
                        **report_dict,
                        "tasks": merged_tasks,
                        "metadata": {
                            **report_dict.get("metadata", {}),
                            "status": "completed",
                            "merged": True
                        }
                    }
                    
                    from app.domain.daily.schemas import DailyReportUpdate
                    db_report = DailyReportRepository.update(
                        db,
                        existing_report,
                        DailyReportUpdate(report_json=merged_json)
                    )
                    
                    print(f"💾 운영 DB 병합 완료: {report.owner} - {report.period_start} (tasks: {len(merged_tasks)}개)")
                    is_created = False
                else:
                    # 기존 보고서가 없으면 새로 생성
                    report_dict = report.model_dump(mode='json')
                    report_dict["metadata"] = {
                        **report_dict.get("metadata", {}),
                        "status": "completed"
                    }
                    
                    report_create = DailyReportCreate(
                        owner=report.owner,
                        report_date=report.period_start,
                        report_json=report_dict
                    )
                    db_report = DailyReportRepository.create(db, report_create)
                    
                    print(f"💾 운영 DB 생성 완료: {report.owner} - {report.period_start}")
                    is_created = True
                
                # 🔥 PDF 자동 생성 및 저장
                try:
                    # PDF 저장 디렉토리 생성
                    pdf_dir = Path("output/report_result/daily")
                    pdf_dir.mkdir(parents=True, exist_ok=True)
                    
                    # PDF 파일명 생성
                    pdf_filename = f"{report.owner}_{report.period_start}_일일보고서.pdf"
                    pdf_path = pdf_dir / pdf_filename
                    
                    # PDF 생성
                    pdf_generator = DailyReportPDFGenerator()
                    pdf_generator.generate(report, str(pdf_path))
                    
                    print(f"📄 일일 보고서 PDF 생성 완료: {pdf_path}")
                except Exception as pdf_error:
                    print(f"⚠️  PDF 생성 실패 (보고서는 저장됨): {str(pdf_error)}")
                
                # 🔥 벡터 DB 자동 저장 (비동기 작업, 실패해도 계속 진행)
                try:
                    from app.domain.report.chunker import chunk_report
                    from ingestion.embed import embed_texts
                    from ingestion.chroma_client import get_chroma_service
                    
                    print(f"⏳ 벡터 DB 저장 시작...")
                    
                    # 1. 청킹
                    chunks = chunk_report(report, include_summary=True)
                    
                    if chunks:
                        # 2. 임베딩 생성
                        texts = [chunk["text"] for chunk in chunks]
                        chunk_ids = [chunk["id"] for chunk in chunks]
                        metadatas = [chunk["metadata"] for chunk in chunks]
                        
                        # 각 청크에 chunk_text 키 추가 (Chroma용)
                        for chunk in chunks:
                            chunk["chunk_text"] = chunk.pop("text")
                        
                        # 메타데이터에 날짜 정보 추가
                        for metadata in metadatas:
                            metadata["doc_type"] = "daily"  # ✅ 검색 필터용
                            metadata["date"] = report.period_start.isoformat()
                            metadata["month"] = report.period_start.strftime("%Y-%m")
                            metadata["owner"] = report.owner
                            
                            # None 값 제거 (ChromaDB는 None을 허용하지 않음)
                            metadata_cleaned = {k: v for k, v in metadata.items() if v is not None}
                            metadata.clear()
                            metadata.update(metadata_cleaned)
                        
                        embeddings = embed_texts(texts, api_key=os.getenv("OPENAI_API_KEY"))
                        
                        # 3. ChromaDB 저장
                        chroma_service = get_chroma_service()
                        collection = chroma_service.get_or_create_collection(name="unified_documents")
                        
                        collection.upsert(
                            ids=chunk_ids,
                            embeddings=embeddings,
                            documents=texts,
                            metadatas=metadatas
                        )
                        
                        print(f"✅ 벡터 DB 저장 완료: {len(chunks)}개 청크 (collection: daily_reports)")
                    else:
                        print(f"⚠️  청크가 생성되지 않음 (벡터 DB 저장 건너뜀)")
                
                except Exception as vector_error:
                    print(f"⚠️  벡터 DB 저장 실패 (보고서는 저장됨): {str(vector_error)}")
                    
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
    append: bool = Field(
        default=False,
        description="True면 기존 업무에 추가, False면 덮어쓰기"
    )


class SelectMainTasksResponse(BaseModel):
    """금일 진행 업무 선택 응답"""
    success: bool
    message: str
    saved_count: int


@router.post("/select_main_tasks", response_model=SelectMainTasksResponse)
async def select_main_tasks(
    request: SelectMainTasksRequest,
    db: Session = Depends(get_db)
):
    """
    금일 진행 업무 선택 및 저장
    
    사용자가 TodayPlan Chain에서 추천받은 업무 중 
    실제로 수행할 업무를 선택하여 저장합니다.
    
    저장된 업무는:
    1. 메모리에 임시 저장 (FSM 시작 시 사용)
    2. PostgreSQL에 부분 저장 (금일 진행 업무만, status="in_progress")
    """
    try:
        if not request.main_tasks:
            raise HTTPException(
                status_code=400,
                detail="최소 1개 이상의 업무를 선택해주세요."
            )
        
        # 1. 메모리 저장 (FSM용)
        store = get_main_tasks_store()
        store.save(
            owner=request.owner,
            target_date=request.target_date,
            main_tasks=request.main_tasks,
            append=request.append
        )
        
        # 2. PostgreSQL에 부분 저장 (금일 진행 업무만)
        try:
            # 기존 보고서 확인
            existing_report = DailyReportRepository.get_by_owner_and_date(
                db, request.owner, request.target_date
            )
            
            if existing_report:
                # 기존 보고서가 있으면 tasks만 업데이트 (append 모드 고려)
                report_json = existing_report.report_json.copy()
                
                if request.append and "tasks" in report_json:
                    # 기존 tasks에 추가
                    existing_tasks = report_json.get("tasks", [])
                    report_json["tasks"] = existing_tasks + request.main_tasks
                else:
                    # 덮어쓰기
                    report_json["tasks"] = request.main_tasks
                
                report_json["metadata"] = report_json.get("metadata", {})
                report_json["metadata"]["status"] = "in_progress"
                
                from app.domain.daily.schemas import DailyReportUpdate
                DailyReportRepository.update(
                    db,
                    existing_report,
                    DailyReportUpdate(report_json=report_json)
                )
                print(f"💾 금일 진행 업무 업데이트 완료: {request.owner} - {request.target_date}")
            else:
                # 새로운 부분 보고서 생성
                partial_report = {
                    "report_type": "daily",
                    "owner": request.owner,
                    "period_start": request.target_date.isoformat(),
                    "period_end": request.target_date.isoformat(),
                    "tasks": request.main_tasks,
                    "kpis": [],
                    "issues": [],
                    "plans": [],
                    "metadata": {"status": "in_progress", "main_tasks_only": True}
                }
                
                DailyReportRepository.create(
                    db,
                    DailyReportCreate(
                        owner=request.owner,
                        report_date=request.target_date,
                        report_json=partial_report
                    )
                )
                print(f"💾 금일 진행 업무 생성 완료: {request.owner} - {request.target_date}")
        
        except Exception as db_error:
            print(f"⚠️  PostgreSQL 저장 실패 (메모리 저장은 성공): {str(db_error)}")
            # DB 저장 실패해도 메모리 저장은 성공했으므로 계속 진행
        
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


class GetMainTasksRequest(BaseModel):
    """금일 진행 업무 조회 요청"""
    owner: str = Field(..., description="작성자")
    target_date: date = Field(..., description="보고서 날짜")


class GetMainTasksResponse(BaseModel):
    """금일 진행 업무 조회 응답"""
    success: bool
    main_tasks: List[Dict[str, Any]]
    count: int


@router.post("/get_main_tasks", response_model=GetMainTasksResponse)
async def get_main_tasks(request: GetMainTasksRequest):
    """
    저장된 금일 진행 업무 조회
    """
    try:
        store = get_main_tasks_store()
        main_tasks = store.get(
            owner=request.owner,
            target_date=request.target_date
        )
        
        if main_tasks is None:
            main_tasks = []
        
        return GetMainTasksResponse(
            success=True,
            main_tasks=main_tasks,
            count=len(main_tasks)
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"업무 조회 실패: {str(e)}"
        )


class UpdateMainTasksRequest(BaseModel):
    """금일 진행 업무 수정 요청"""
    owner: str = Field(..., description="작성자")
    target_date: date = Field(..., description="보고서 날짜")
    main_tasks: List[Dict[str, Any]] = Field(
        ...,
        description="수정된 금일 진행 업무 리스트"
    )


class UpdateMainTasksResponse(BaseModel):
    """금일 진행 업무 수정 응답"""
    success: bool
    message: str
    updated_count: int


@router.put("/update_main_tasks", response_model=UpdateMainTasksResponse)
async def update_main_tasks(
    request: UpdateMainTasksRequest,
    db: Session = Depends(get_db)
):
    """
    금일 진행 업무 수정
    
    저장된 금일 진행 업무를 수정합니다.
    - 메모리 (MainTasksStore) 업데이트
    - PostgreSQL 업데이트 (tasks 필드만)
    """
    try:
        if not request.main_tasks:
            raise HTTPException(
                status_code=400,
                detail="최소 1개 이상의 업무가 필요합니다."
            )
        
        # 1. 메모리 업데이트
        store = get_main_tasks_store()
        store.save(
            owner=request.owner,
            target_date=request.target_date,
            main_tasks=request.main_tasks,
            append=False  # 덮어쓰기
        )
        
        # 2. PostgreSQL 업데이트
        try:
            existing_report = DailyReportRepository.get_by_owner_and_date(
                db, request.owner, request.target_date
            )
            
            if existing_report:
                # tasks 필드만 업데이트
                report_json = existing_report.report_json.copy()
                report_json["tasks"] = request.main_tasks
                
                # status는 유지 (in_progress 또는 completed)
                if "metadata" not in report_json:
                    report_json["metadata"] = {}
                
                from app.domain.daily.schemas import DailyReportUpdate
                DailyReportRepository.update(
                    db,
                    existing_report,
                    DailyReportUpdate(report_json=report_json)
                )
                print(f"💾 금일 진행 업무 수정 완료 (DB): {request.owner} - {request.target_date}")
            else:
                # 보고서가 없으면 새로 생성
                partial_report = {
                    "report_type": "daily",
                    "owner": request.owner,
                    "period_start": request.target_date.isoformat(),
                    "period_end": request.target_date.isoformat(),
                    "tasks": request.main_tasks,
                    "kpis": [],
                    "issues": [],
                    "plans": [],
                    "metadata": {"status": "in_progress", "main_tasks_only": True}
                }
                
                DailyReportRepository.create(
                    db,
                    DailyReportCreate(
                        owner=request.owner,
                        report_date=request.target_date,
                        report_json=partial_report
                    )
                )
                print(f"💾 금일 진행 업무 생성 완료 (DB): {request.owner} - {request.target_date}")
        
        except Exception as db_error:
            print(f"⚠️  PostgreSQL 업데이트 실패 (메모리는 성공): {str(db_error)}")
            # DB 실패해도 메모리는 성공했으므로 계속 진행
        
        return UpdateMainTasksResponse(
            success=True,
            message="금일 진행 업무가 수정되었습니다.",
            updated_count=len(request.main_tasks)
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"업무 수정 실패: {str(e)}"
        )


@router.get("/health")
async def health_check():
    """Health check"""
    return {"status": "ok", "service": "daily"}

