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
import re

from app.domain.report.canonical_models import CanonicalReport
# 하위 호환성을 위해 TaskItem, KPIItem은 임시로 유지
try:
    from app.domain.report.schemas import TaskItem, KPIItem
except ImportError:
    from typing import Optional
    from pydantic import BaseModel, Field
    class TaskItem(BaseModel):
        task_id: Optional[str] = None
        title: str = ""
        description: str = ""
        time_start: Optional[str] = None
        time_end: Optional[str] = None
        status: Optional[str] = None
        note: str = ""
    class KPIItem(BaseModel):
        kpi_name: str = ""
        value: str = ""
        unit: Optional[str] = None
        category: Optional[str] = None
        note: str = ""
from app.infrastructure.vector_store_advanced import get_vector_store
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


def calculate_monthly_kpis(tasks: List[TaskItem]) -> List[KPIItem]:
    """
    일일보고서 데이터를 기반으로 월간 핵심 지표 계산
    
    Args:
        tasks: 해당 월의 모든 TaskItem 리스트
        
    Returns:
        KPIItem 리스트
    """
    kpis = []
    
    if not tasks:
        return kpis
    
    # 모든 task 텍스트를 하나로 합침
    all_text = " ".join([f"{task.title} {task.description}" for task in tasks]).lower()
    
    # 1. 신규 계약 건수 계산
    # "신규", "계약", "체결", "가입" 등의 키워드가 포함된 task 카운트
    new_contract_keywords = ["신규", "계약", "체결", "가입", "신규 계약"]
    new_contract_count = 0
    for task in tasks:
        task_text = f"{task.title} {task.description}".lower()
        if any(keyword in task_text for keyword in new_contract_keywords):
            new_contract_count += 1
    
    if new_contract_count > 0:
        kpis.append(KPIItem(
            kpi_name="신규_계약_건수",
            value=str(new_contract_count),
            unit="건",
            category="계약",
            note=""
        ))
    
    # 2. 유지 계약 건수 계산
    # "유지", "갱신", "미납 방지" 등의 키워드가 포함된 task 카운트
    maintain_keywords = ["유지", "갱신", "미납", "연체", "해지 방지"]
    maintain_count = 0
    renew_count = 0
    non_payment_prevention_count = 0
    
    for task in tasks:
        task_text = f"{task.title} {task.description}".lower()
        if any(keyword in task_text for keyword in maintain_keywords):
            if "갱신" in task_text:
                renew_count += 1
            elif "미납" in task_text or "연체" in task_text:
                non_payment_prevention_count += 1
            else:
                maintain_count += 1
    
    if maintain_count > 0 or renew_count > 0 or non_payment_prevention_count > 0:
        if maintain_count > 0:
            kpis.append(KPIItem(
                kpi_name="유지_계약_유지",
                value=str(maintain_count),
                unit="건",
                category="유지계약",
                note=""
            ))
        if renew_count > 0:
            kpis.append(KPIItem(
                kpi_name="유지_계약_갱신",
                value=str(renew_count),
                unit="건",
                category="유지계약",
                note=""
            ))
        if non_payment_prevention_count > 0:
            kpis.append(KPIItem(
                kpi_name="유지_계약_미납_방지",
                value=str(non_payment_prevention_count),
                unit="건",
                category="유지계약",
                note=""
            ))
    
    # 3. 상담 진행 건수 계산
    # "상담", "전화", "방문", "온라인" 등의 키워드가 포함된 task 카운트
    consultation_keywords = ["상담", "통화", "전화", "방문", "온라인", "미팅"]
    phone_count = 0
    visit_count = 0
    online_count = 0
    
    for task in tasks:
        task_text = f"{task.title} {task.description}".lower()
        if any(keyword in task_text for keyword in consultation_keywords):
            if "전화" in task_text or "통화" in task_text:
                phone_count += 1
            elif "방문" in task_text:
                visit_count += 1
            elif "온라인" in task_text:
                online_count += 1
            else:
                # 기본적으로 전화로 카운트
                phone_count += 1
    
    if phone_count > 0 or visit_count > 0 or online_count > 0:
        if phone_count > 0:
            kpis.append(KPIItem(
                kpi_name="상담_전화",
                value=str(phone_count),
                unit="건",
                category="상담",
                note=""
            ))
        if visit_count > 0:
            kpis.append(KPIItem(
                kpi_name="상담_방문",
                value=str(visit_count),
                unit="건",
                category="상담",
                note=""
            ))
        if online_count > 0:
            kpis.append(KPIItem(
                kpi_name="상담_온라인",
                value=str(online_count),
                unit="건",
                category="상담",
                note=""
            ))
    
    print(f"[INFO] 월간 핵심 지표 계산 완료: {len(kpis)}개 KPI 생성")
    
    return kpis


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
    vector_store = get_vector_store()
    collection = vector_store.get_collection()
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
        chunk_types=["detail_chunk"]
    )
    
    if not task_results:
        task_results = retriever.search_daily(
            query=f"{owner} 월간 업무",
            owner=owner,
            n_results=500,
            chunk_types=["detail_chunk"]
        )
    
    print(f"[INFO] 벡터DB task 검색 완료: {len(task_results)}개 청크 발견")
    
    # 2-2. 특이사항 (issue 타입) 검색
    issue_results = retriever.search_daily(
        query=f"{owner} 월간 특이사항 이슈",
        owner=owner,
        period_start=first_day.isoformat(),
        period_end=last_day.isoformat(),
        n_results=200,
        chunk_types=["pending_chunk"]
    )
    
    if not issue_results:
        issue_results = retriever.search_daily(
            query=f"{owner} 월간 특이사항 이슈",
            owner=owner,
            n_results=200,
            chunk_types=["pending_chunk"]
        )
    
    print(f"[INFO] 벡터DB issue 검색 완료: {len(issue_results)}개 청크 발견")
    
    # 2-3. 계획 (plan 타입) 검색
    plan_results = retriever.search_daily(
        query=f"{owner} 월간 계획",
        owner=owner,
        period_start=first_day.isoformat(),
        period_end=last_day.isoformat(),
        n_results=200,
        chunk_types=["plan_chunk"]
    )
    
    if not plan_results:
        plan_results = retriever.search_daily(
            query=f"{owner} 월간 계획",
            owner=owner,
            n_results=200,
            chunk_types=["plan_chunk"]
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
            # time_slot 파싱 (예: "09:00~10:00" -> time_start="09:00", time_end="10:00")
            time_slot = metadata.get("time_slot", "")
            time_start, time_end = None, None
            if time_slot and "~" in time_slot:
                parts = time_slot.split("~")
                if len(parts) == 2:
                    time_start = parts[0].strip()
                    time_end = parts[1].strip()
            
            task_item = TaskItem(
                task_id=task_id,
                title=result.text[:100] if len(result.text) > 100 else result.text,
                description=result.text,
                time_start=time_start,
                time_end=time_end,
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
    
    # 4. 월간 핵심 지표 계산 (일일보고서 데이터 기반)
    kpis = calculate_monthly_kpis(tasks)
    
    # 5. 완료율 계산
    task_dicts = [{"status": task.status} for task in tasks]
    completion_rate = calculate_completion_rate(task_dicts)
    
    # 6. CanonicalReport 생성
    report = CanonicalReport(
        report_id=str(uuid.uuid4()),
        report_type="monthly",
        owner=owner,
        period_start=first_day,
        period_end=last_day,
        tasks=tasks,
        kpis=kpis,
        issues=issues,
        plans=plans,
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

