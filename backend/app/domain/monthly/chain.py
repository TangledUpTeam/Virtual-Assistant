"""
Monthly Report Chain

월간 보고서 자동 생성 체인
target_date가 속한 달의 1일~말일 일일보고서를 조회하여 월간 보고서를 자동 생성
"""
from datetime import date
from calendar import monthrange
from typing import List
from sqlalchemy.orm import Session
import uuid

from app.domain.report.schemas import CanonicalReport, TaskItem, KPIItem
from app.infrastructure.vector_store import get_unified_collection
from app.domain.search.retriever import UnifiedRetriever
from app.core.config import settings


def get_month_range(target_date: date) -> tuple[date, date]:
    """
    target_date가 속한 달의 1일~말일 날짜 범위를 계산
    
    Args:
        target_date: 기준 날짜
        
    Returns:
        (first_day, last_day) 튜플
    """
    first_day = target_date.replace(day=1)
    last_day_num = monthrange(target_date.year, target_date.month)[1]
    last_day = target_date.replace(day=last_day_num)
    return (first_day, last_day)


def calculate_completion_rate(tasks: List[dict]) -> float:
    """
    완료율 계산: 완료된 task / 전체 task
    
    Args:
        tasks: TaskItem dict 리스트
        
    Returns:
        완료율 (0.0 ~ 1.0)
    """
    if not tasks:
        return 0.0
    
    completed = sum(1 for task in tasks if task.get("status") == "완료")
    return completed / len(tasks)


def generate_monthly_report(
    db: Session,
    owner: str,
    target_date: date
) -> CanonicalReport:
    """
    월간 보고서 자동 생성
    
    Args:
        db: 데이터베이스 세션
        owner: 작성자
        target_date: 기준 날짜 (해당 월의 아무 날짜)
        
    Returns:
        CanonicalReport (monthly)
        
    Raises:
        ValueError: 해당 기간에 일일보고서가 없는 경우
    """
    # 1. 해당 월의 1일~말일 날짜 계산
    first_day, last_day = get_month_range(target_date)
    
    # 2. 벡터DB에서 월간 데이터 검색
    collection = get_unified_collection()
    retriever = UnifiedRetriever(
        collection=collection,
        openai_api_key=settings.OPENAI_API_KEY
    )
    
    print(f"[DEBUG] 월간 보고서 데이터 검색: owner={owner}, period={first_day}~{last_day}")
    
    # 2-1. 요일별 세부 업무 (task 타입) 검색
    task_results = retriever.search_daily(
        query=f"{owner} 월간 업무",
        owner=owner,
        period_start=first_day.isoformat(),
        period_end=last_day.isoformat(),
        n_results=500,  # 월간이므로 더 많은 데이터
        chunk_types=["task"]
    )
    
    if not task_results:
        task_results = retriever.search_daily(
            query=f"{owner} 월간 업무",
            owner=owner,
            n_results=500,
            chunk_types=["task"]
        )
    
    print(f"[INFO] 벡터DB task 검색 완료: {len(task_results)}개 청크 발견")
    
    # 2-2. 특이사항 (issue 타입) 검색
    issue_results = retriever.search_daily(
        query=f"{owner} 월간 특이사항 이슈",
        owner=owner,
        period_start=first_day.isoformat(),
        period_end=last_day.isoformat(),
        n_results=200,
        chunk_types=["issue"]
    )
    
    if not issue_results:
        issue_results = retriever.search_daily(
            query=f"{owner} 월간 특이사항 이슈",
            owner=owner,
            n_results=200,
            chunk_types=["issue"]
        )
    
    print(f"[INFO] 벡터DB issue 검색 완료: {len(issue_results)}개 청크 발견")
    
    # 2-3. 계획 (plan 타입) 검색
    plan_results = retriever.search_daily(
        query=f"{owner} 월간 계획",
        owner=owner,
        period_start=first_day.isoformat(),
        period_end=last_day.isoformat(),
        n_results=200,
        chunk_types=["plan"]
    )
    
    if not plan_results:
        plan_results = retriever.search_daily(
            query=f"{owner} 월간 계획",
            owner=owner,
            n_results=200,
            chunk_types=["plan"]
        )
    
    print(f"[INFO] 벡터DB plan 검색 완료: {len(plan_results)}개 청크 발견")
    
    # 3. 벡터DB 검색 결과를 TaskItem, Issue, Plan으로 변환
    tasks = []
    seen_task_ids = set()
    for result in task_results:
        metadata = result.metadata
        task_id = metadata.get("task_id", f"task_{len(tasks)}")
        
        if task_id in seen_task_ids:
            continue
        seen_task_ids.add(task_id)
        
        try:
            task_item = TaskItem(
                title=result.text[:100] if len(result.text) > 100 else result.text,
                description=result.text,
                category=metadata.get("category", "기타"),
                time_range=metadata.get("time_slot", ""),
                status=metadata.get("status", "완료")
            )
            tasks.append(task_item)
        except Exception as e:
            print(f"[WARNING] TaskItem 변환 실패: {e}, text={result.text[:50]}")
            continue
    
    issues = []
    seen_issue_ids = set()
    for result in issue_results:
        issue_id = result.chunk_id
        if issue_id in seen_issue_ids:
            continue
        seen_issue_ids.add(issue_id)
        issues.append(result.text)
    
    plans = []
    seen_plan_ids = set()
    for result in plan_results:
        plan_id = result.chunk_id
        if plan_id in seen_plan_ids:
            continue
        seen_plan_ids.add(plan_id)
        plans.append(result.text)
    
    print(f"[INFO] 벡터DB 데이터 변환 완료: tasks={len(tasks)}개, issues={len(issues)}개, plans={len(plans)}개")
    
    if not tasks:
        raise ValueError(f"해당 기간({first_day}~{last_day})에 벡터DB에서 업무 데이터를 찾을 수 없습니다.")
    
    # 4. KPIItem 변환 (KPI는 벡터DB에서 가져오지 않음, 빈 리스트)
    kpis = []
    
    # 5. 완료율 계산
    task_dicts = [{"status": task.status} for task in tasks]
    completion_rate = calculate_completion_rate(task_dicts)
    
    # 7. CanonicalReport 생성
    report = CanonicalReport(
        report_id=str(uuid.uuid4()),
        report_type="monthly",
        owner=owner,
        period_start=first_day,
        period_end=last_day,
        tasks=tasks,
        kpis=kpis,
        issues=aggregated["issues"],
        plans=aggregated["plans"],
        metadata={
            "source": "monthly_chain",
            "task_count": len(tasks),
            "issue_count": len(issues),
            "plan_count": len(plans),
            "completion_rate": round(completion_rate, 2),
            "month": f"{target_date.year}-{target_date.month:02d}"
        }
    )
    
    return report

