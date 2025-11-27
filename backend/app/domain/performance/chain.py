"""
Performance Report Chain

실적 보고서 자동 생성 체인
KPI 관련 업무를 중심으로 실적 보고서를 자동 생성
"""
from datetime import date
from typing import List
from sqlalchemy.orm import Session
import uuid
import json
import os
import re
from pathlib import Path

from app.domain.report.schemas import CanonicalReport, TaskItem, KPIItem
from app.infrastructure.vector_store import get_unified_collection
from app.domain.search.retriever import UnifiedRetriever
from app.core.config import settings


# KPI 관련 카테고리 키워드
KPI_RELATED_KEYWORDS = [
    "영업", "성과", "고객상담", "계약", "실적", 
    "목표", "달성", "KPI", "매출", "수익"
]


def load_kpi_documents(base_path: str = "backend") -> List[dict]:
    """
    KPI 관련 JSON 파일을 로드
    
    Args:
        base_path: 기본 경로
        
    Returns:
        KPI 문서 리스트
    """
    kpi_files = [
        "output/KPI 자료_kpi_canonical.json",
        "output/reports/실적 보고서 양식_performance_canonical.json"
    ]
    
    all_kpis = []
    
    for file_path in kpi_files:
        full_path = Path(base_path) / file_path
        if full_path.exists():
            try:
                with open(full_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        all_kpis.extend(data)
                    elif isinstance(data, dict):
                        all_kpis.append(data)
            except Exception as e:
                print(f"⚠️  KPI 파일 로드 실패 ({file_path}): {e}")
    
    return all_kpis


def is_kpi_related_task(task: dict) -> bool:
    """
    Task가 KPI 관련 업무인지 확인
    
    Args:
        task: TaskItem dict
        
    Returns:
        KPI 관련 여부
    """
    title = task.get("title", "").lower()
    description = task.get("description", "").lower()
    note = task.get("note", "").lower()
    
    text = f"{title} {description} {note}"
    
    return any(keyword.lower() in text for keyword in KPI_RELATED_KEYWORDS)


def filter_kpi_tasks(all_tasks: List[dict]) -> List[dict]:
    """
    KPI 관련 task만 필터링
    
    Args:
        all_tasks: 전체 TaskItem dict 리스트
        
    Returns:
        필터링된 KPI task 리스트
    """
    return [task for task in all_tasks if is_kpi_related_task(task)]


def calculate_performance_kpis(tasks: List[dict]) -> List[KPIItem]:
    """
    일일보고서 데이터를 기반으로 실적보고서 KPI 계산
    
    실적보고서는 일일보고서 데이터만 사용하여 KPI를 계산합니다.
    KPI 문서(RAG 데이터)는 "KPI 설명/해설" 섹션 작성용으로만 사용되며,
    실제 실적 수치는 여기서 계산된 값 또는 별도로 제공되는 데이터를 사용합니다.
    
    Args:
        tasks: 해당 연도의 모든 TaskItem dict 리스트
        
    Returns:
        KPIItem 리스트
    """
    kpis = []
    
    if not tasks:
        return kpis
    
    # 모든 task 텍스트를 하나로 합침
    all_text = " ".join([f"{task.get('title', '')} {task.get('description', '')}" for task in tasks]).lower()
    
    # 1. 신규 계약 건수 계산
    new_contract_keywords = ["신규", "계약", "체결", "가입", "신규 계약"]
    new_contract_count = 0
    for task in tasks:
        task_text = f"{task.get('title', '')} {task.get('description', '')}".lower()
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
    maintain_keywords = ["유지", "갱신", "미납", "연체", "해지 방지"]
    maintain_count = 0
    renew_count = 0
    non_payment_prevention_count = 0
    
    for task in tasks:
        task_text = f"{task.get('title', '')} {task.get('description', '')}".lower()
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
    consultation_keywords = ["상담", "통화", "전화", "방문", "온라인", "미팅"]
    phone_count = 0
    visit_count = 0
    online_count = 0
    
    for task in tasks:
        task_text = f"{task.get('title', '')} {task.get('description', '')}".lower()
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
    
    print(f"[INFO] 실적보고서 KPI 계산 완료: {len(kpis)}개 KPI 생성")
    
    return kpis


def convert_kpi_docs_to_items(kpi_docs: List[dict]) -> List[KPIItem]:
    """
    KPI 문서를 KPIItem으로 변환
    
    Args:
        kpi_docs: KPI 문서 리스트
        
    Returns:
        KPIItem 리스트
    """
    kpi_items = []
    
    for doc in kpi_docs:
        # KPI 자료의 구조에 맞게 변환
        if "kpi_name" in doc:
            kpi_item = KPIItem(
                kpi_name=doc.get("kpi_name", ""),
                value=doc.get("values", ""),
                unit=doc.get("unit"),
                category=doc.get("category"),
                note=doc.get("description", "")
            )
            kpi_items.append(kpi_item)
        # CanonicalReport의 KPI 구조인 경우
        elif "tasks" in doc or "kpis" in doc:
            if "kpis" in doc and isinstance(doc["kpis"], list):
                for kpi_data in doc["kpis"]:
                    kpi_item = KPIItem(**kpi_data)
                    kpi_items.append(kpi_item)
    
    return kpi_items


def get_year_range(target_date: date) -> tuple[date, date]:
    """
    target_date가 속한 연도의 1월 1일~12월 31일 날짜 범위를 계산
    
    Args:
        target_date: 기준 날짜
        
    Returns:
        (first_day, last_day) 튜플
    """
    first_day = date(target_date.year, 1, 1)
    last_day = date(target_date.year, 12, 31)
    return (first_day, last_day)


def generate_performance_report(
    db: Session,
    owner: str,
    target_date: date
) -> CanonicalReport:
    """
    실적 보고서 자동 생성
    
    실적보고서는 매년 마지막 주에 작성하며, 해당 연도의 1월 1일~12월 31일 일일보고서 데이터를
    ChromaDB에서 가져와서 KPI 문서와 함께 작성합니다.
    
    Args:
        db: 데이터베이스 세션
        owner: 작성자
        target_date: 기준 날짜 (해당 연도의 아무 날짜, 보통 마지막 주)
        
    Returns:
        CanonicalReport (performance)
        
    Raises:
        ValueError: 해당 기간에 일일보고서가 없는 경우
    """
    # 1. 해당 연도의 1월 1일~12월 31일 날짜 계산
    period_start, period_end = get_year_range(target_date)
    # 1. 벡터DB에서 실적 보고서 데이터 검색
    collection = get_unified_collection()
    retriever = UnifiedRetriever(
        collection=collection,
        openai_api_key=settings.OPENAI_API_KEY
    )
    
    print(f"[DEBUG] 실적 보고서 데이터 검색: owner={owner}, year={target_date.year}, period={period_start}~{period_end}")
    
    # 1-1. 요일별 세부 업무 (task 타입) 검색
    task_results = retriever.search_daily(
        query=f"{owner} 실적 업무 KPI",
        owner=owner,
        period_start=period_start.isoformat(),
        period_end=period_end.isoformat(),
        n_results=1000,  # 연간이므로 매우 많은 데이터
        chunk_types=["task"]
    )
    
    if not task_results:
        task_results = retriever.search_daily(
            query=f"{owner} 실적 업무 KPI",
            owner=owner,
            n_results=1000,
            chunk_types=["task"]
        )
    
    print(f"[INFO] 벡터DB task 검색 완료: {len(task_results)}개 청크 발견")
    
    # 1-2. 특이사항 (issue 타입) 검색
    issue_results = retriever.search_daily(
        query=f"{owner} 실적 특이사항 이슈",
        owner=owner,
        period_start=period_start.isoformat(),
        period_end=period_end.isoformat(),
        n_results=500,
        chunk_types=["issue"]
    )
    
    if not issue_results:
        issue_results = retriever.search_daily(
            query=f"{owner} 실적 특이사항 이슈",
            owner=owner,
            n_results=500,
            chunk_types=["issue"]
        )
    
    print(f"[INFO] 벡터DB issue 검색 완료: {len(issue_results)}개 청크 발견")
    
    # 1-3. 계획 (plan 타입) 검색
    plan_results = retriever.search_daily(
        query=f"{owner} 실적 계획",
        owner=owner,
        period_start=period_start.isoformat(),
        period_end=period_end.isoformat(),
        n_results=500,
        chunk_types=["plan"]
    )
    
    if not plan_results:
        plan_results = retriever.search_daily(
            query=f"{owner} 실적 계획",
            owner=owner,
            n_results=500,
            chunk_types=["plan"]
        )
    
    print(f"[INFO] 벡터DB plan 검색 완료: {len(plan_results)}개 청크 발견")
    
    # 2. 벡터DB 검색 결과를 TaskItem, Issue, Plan으로 변환
    all_tasks = []
    seen_task_ids = set()
    for result in task_results:
        metadata = result.metadata
        task_id = metadata.get("task_id", f"task_{len(all_tasks)}")
        
        if task_id in seen_task_ids:
            continue
        seen_task_ids.add(task_id)
        
        try:
            task_dict = {
                "title": result.text[:100] if len(result.text) > 100 else result.text,
                "description": result.text,
                "category": metadata.get("category", "기타"),
                "time_range": metadata.get("time_slot", ""),
                "status": metadata.get("status", "완료")
            }
            all_tasks.append(task_dict)
        except Exception as e:
            print(f"[WARNING] Task 변환 실패: {e}, text={result.text[:50]}")
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
    
    print(f"[INFO] 벡터DB 데이터 변환 완료: tasks={len(all_tasks)}개, issues={len(issues)}개, plans={len(plans)}개")
    
    if not all_tasks:
        raise ValueError(f"해당 기간({period_start}~{period_end})에 벡터DB에서 업무 데이터를 찾을 수 없습니다.")
    
    # 3. 실적보고서는 일일보고서 데이터만 사용
    # KPI 문서는 "KPI 설명/해설" 섹션 작성용으로만 사용되며, 
    # 실제 실적 수치는 일일보고서 데이터에서 계산하거나 별도로 제공되는 데이터를 사용
    # 따라서 여기서는 KPI 문서를 검색하지 않음
    
    # 일일보고서 데이터에서 KPI 계산 (월간보고서와 유사한 방식)
    all_kpis = calculate_performance_kpis(all_tasks)
    
    print(f"[INFO] 일일보고서 데이터 기반 KPI 계산 완료: {len(all_kpis)}개")
    
    # 4. TaskItem 변환 (time_range를 time_start, time_end로 파싱)
    tasks = []
    for task_dict in all_tasks:
        # time_range 파싱 (예: "09:00~10:00" -> time_start="09:00", time_end="10:00")
        time_range = task_dict.get("time_range", "")
        time_start, time_end = None, None
        if time_range:
            if "~" in time_range:
                parts = time_range.split("~")
                if len(parts) == 2:
                    time_start = parts[0].strip()
                    time_end = parts[1].strip()
            elif "-" in time_range:
                parts = time_range.split("-")
                if len(parts) == 2:
                    time_start = parts[0].strip()
                    time_end = parts[1].strip()
        
        task = TaskItem(
            task_id=task_dict.get("task_id", f"task_{len(tasks)}"),
            title=task_dict.get("title", ""),
            description=task_dict.get("description", ""),
            time_start=time_start,
            time_end=time_end,
            status=task_dict.get("status", "완료")
        )
        tasks.append(task)
    
    # 8. CanonicalReport 생성
    report = CanonicalReport(
        report_id=str(uuid.uuid4()),
        report_type="performance",
        owner=owner,
        period_start=period_start,
        period_end=period_end,
        tasks=tasks,
        kpis=all_kpis,
        issues=issues,
        plans=plans,
        metadata={
            "source": "performance_chain",
            "task_count": len(all_tasks),
            "issue_count": len(issues),
            "plan_count": len(plans),
            "total_kpi_count": len(all_kpis),
            "note": "실적보고서는 일일보고서 데이터만 사용하여 작성됩니다. KPI 문서는 'KPI 설명/해설' 섹션 작성용으로만 사용됩니다."
        }
    )
    
    return report

