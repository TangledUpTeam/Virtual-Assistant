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
from app.domain.daily.repository import DailyReportRepository
from app.domain.daily.models import DailyReport


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


def aggregate_daily_reports(daily_reports: List[DailyReport]) -> dict:
    """
    여러 일일보고서를 집계하여 실적 보고서 데이터를 생성
    
    Args:
        daily_reports: 일일보고서 리스트
        
    Returns:
        집계된 데이터 dict {tasks, plans, issues, kpis}
    """
    all_tasks = []
    all_plans = []
    all_issues = []
    all_kpis = []
    
    for daily_report in daily_reports:
        report_json = daily_report.report_json
        
        # tasks 수집
        if "tasks" in report_json:
            all_tasks.extend(report_json["tasks"])
        
        # plans 수집
        if "plans" in report_json:
            all_plans.extend(report_json["plans"])
        
        # issues 수집
        if "issues" in report_json:
            all_issues.extend(report_json["issues"])
        
        # kpis 수집
        if "kpis" in report_json:
            all_kpis.extend(report_json["kpis"])
    
    return {
        "tasks": all_tasks,
        "plans": all_plans,
        "issues": all_issues,
        "kpis": all_kpis
    }


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
    # 1. 일일보고서 조회
    daily_reports = DailyReportRepository.list_by_owner_and_date_range(
        db=db,
        owner=owner,
        start_date=period_start,
        end_date=period_end
    )
    
    if not daily_reports:
        raise ValueError(f"해당 기간({period_start}~{period_end})에 일일보고서가 없습니다.")
    
    # 2. 일일보고서 집계
    aggregated = aggregate_daily_reports(daily_reports)
    
    # 3. KPI 관련 task만 필터링
    kpi_tasks = filter_kpi_tasks(aggregated["tasks"])
    
    # 4. KPI 문서 로드
    kpi_docs = load_kpi_documents()
    
    # 5. KPI 문서를 KPIItem으로 변환
    kpi_items_from_docs = convert_kpi_docs_to_items(kpi_docs)
    
    # 6. 일일보고서의 KPI + KPI 문서의 KPI 합치기
    all_kpis = []
    # 일일보고서의 KPI
    for kpi_data in aggregated["kpis"]:
        all_kpis.append(KPIItem(**kpi_data))
    # KPI 문서의 KPI
    all_kpis.extend(kpi_items_from_docs)
    
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
            "daily_count": len(daily_reports),
            "kpi_document_count": len(kpi_docs),
            "matched_task_count": len(kpi_tasks),
            "total_kpi_count": len(all_kpis)
        }
    )
    
    return report

