"""
Weekly Report Chain

주간 보고서 자동 생성 체인
target_date 기준으로 해당 주의 월~금 일일보고서를 조회하여 주간 보고서를 자동 생성
"""
from datetime import date, timedelta
from typing import List
from sqlalchemy.orm import Session
import uuid

from app.domain.report.schemas import CanonicalReport, TaskItem, KPIItem
from app.domain.daily.repository import DailyReportRepository
from app.domain.daily.models import DailyReport


def get_week_range(target_date: date) -> tuple[date, date]:
    """
    target_date가 속한 주의 월요일~금요일 날짜 범위를 계산
    
    Args:
        target_date: 기준 날짜
        
    Returns:
        (monday, friday) 튜플
    """
    # 해당 주의 월요일 찾기 (weekday: 0=월, 6=일)
    weekday = target_date.weekday()
    monday = target_date - timedelta(days=weekday)
    friday = monday + timedelta(days=4)
    return (monday, friday)


def aggregate_daily_reports(daily_reports: List[DailyReport]) -> dict:
    """
    여러 일일보고서를 집계하여 주간 보고서 데이터를 생성
    
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


def generate_weekly_report(
    db: Session,
    owner: str,
    target_date: date
) -> CanonicalReport:
    """
    주간 보고서 자동 생성
    
    Args:
        db: 데이터베이스 세션
        owner: 작성자
        target_date: 기준 날짜 (해당 주의 아무 날짜)
        
    Returns:
        CanonicalReport (weekly)
        
    Raises:
        ValueError: 해당 기간에 일일보고서가 없는 경우
    """
    # 1. 해당 주의 월~금 날짜 계산
    monday, friday = get_week_range(target_date)
    
    # 2. 일일보고서 조회
    daily_reports = DailyReportRepository.list_by_owner_and_date_range(
        db=db,
        owner=owner,
        start_date=monday,
        end_date=friday
    )
    
    if not daily_reports:
        raise ValueError(f"해당 기간({monday}~{friday})에 일일보고서가 없습니다.")
    
    # 3. 일일보고서 집계
    aggregated = aggregate_daily_reports(daily_reports)
    
    # 4. TaskItem 변환
    tasks = [TaskItem(**task) for task in aggregated["tasks"]]
    
    # 5. KPIItem 변환
    kpis = [KPIItem(**kpi) for kpi in aggregated["kpis"]]
    
    # 6. 완료율 계산
    completion_rate = calculate_completion_rate(aggregated["tasks"])
    
    # 7. CanonicalReport 생성
    report = CanonicalReport(
        report_id=str(uuid.uuid4()),
        report_type="weekly",
        owner=owner,
        period_start=monday,
        period_end=friday,
        tasks=tasks,
        kpis=kpis,
        issues=aggregated["issues"],
        plans=aggregated["plans"],
        metadata={
            "source": "weekly_chain",
            "daily_count": len(daily_reports),
            "completion_rate": round(completion_rate, 2),
            "week_dates": [monday.isoformat(), friday.isoformat()]
        }
    )
    
    return report

