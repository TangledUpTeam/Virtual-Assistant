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


def generate_performance_report(
    db: Session,
    owner: str,
    period_start: date,
    period_end: date
) -> CanonicalReport:
    """
    실적 보고서 자동 생성
    
    Args:
        db: 데이터베이스 세션
        owner: 작성자
        period_start: 시작일
        period_end: 종료일
        
    Returns:
        CanonicalReport (performance)
        
    Raises:
        ValueError: 해당 기간에 일일보고서가 없는 경우
    """
    # 1. 벡터DB에서 실적 보고서 데이터 검색
    collection = get_unified_collection()
    retriever = UnifiedRetriever(
        collection=collection,
        openai_api_key=settings.OPENAI_API_KEY
    )
    
    print(f"[DEBUG] 실적 보고서 데이터 검색: owner={owner}, period={period_start}~{period_end}")
    
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
    
    # 3. KPI 관련 task만 필터링
    kpi_tasks = filter_kpi_tasks(all_tasks)
    
    # 4. KPI 문서 로드
    kpi_docs = load_kpi_documents()
    
    # 5. KPI 문서를 KPIItem으로 변환
    kpi_items_from_docs = convert_kpi_docs_to_items(kpi_docs)
    
    # 6. KPI 문서의 KPI만 사용 (벡터DB에서 KPI는 가져오지 않음)
    all_kpis = kpi_items_from_docs
    
    # 7. TaskItem 변환
    tasks = [TaskItem(**task) for task in kpi_tasks]
    
    # 8. CanonicalReport 생성
    report = CanonicalReport(
        report_id=str(uuid.uuid4()),
        report_type="performance",
        owner=owner,
        period_start=period_start,
        period_end=period_end,
        tasks=tasks,
        kpis=all_kpis,
        issues=aggregated["issues"],
        plans=aggregated["plans"],
        metadata={
            "source": "performance_chain",
            "task_count": len(all_tasks),
            "kpi_task_count": len(kpi_tasks),
            "issue_count": len(issues),
            "plan_count": len(plans),
            "kpi_document_count": len(kpi_docs),
            "total_kpi_count": len(all_kpis)
        }
    )
    
    return report

