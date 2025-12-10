"""
월간 KPI 계산기

카테고리 기반 KPI 계산
"""
from typing import Dict, Any, List
from datetime import date
from sqlalchemy.orm import Session

from app.domain.report.daily.repository import DailyReportRepository
from app.core.config import settings

REPORT_OWNER = settings.REPORT_WORKSPACE_OWNER


def calculate_monthly_kpi(
    db: Session,
    year: int,
    month: int
) -> Dict[str, Any]:
    """
    월간 KPI 계산 (카테고리 기반)
    
    해당 월의 모든 일일보고서에서 detail_tasks의 카테고리를 기반으로 KPI를 계산합니다.
    
    Args:
        db: 데이터베이스 세션
        year: 연도
        month: 월 (1~12)
        
    Returns:
        {
            "new_contracts": int,
            "renewals": int,
            "consultations": int,
            "analysis": str
        }
    """
    from calendar import monthrange
    
    # 해당 월의 첫날과 마지막날 계산
    first_day = date(year, month, 1)
    last_day_num = monthrange(year, month)[1]
    last_day = date(year, month, last_day_num)
    
    # 해당 월의 모든 일일보고서 조회
    daily_reports = DailyReportRepository.list_by_owner_and_period_range(
        db=db,
        owner=REPORT_OWNER,
        period_start=first_day,
        period_end=last_day
    )
    
    # 카테고리별 카운트
    new_contracts = 0
    renewals = 0
    consultations = 0
    
    # 모든 일일보고서의 detail_tasks 순회
    for report in daily_reports:
        if not report.report_json:
            continue
        
        daily_data = report.report_json.get("daily", {})
        detail_tasks = daily_data.get("detail_tasks", [])
        
        for task in detail_tasks:
            if not isinstance(task, dict):
                continue
            
            # note 필드에서 카테고리 추출
            note = task.get("note", "")
            if not note:
                continue
            
            # "카테고리: " 또는 "카테고리:" 형식 처리
            category = ""
            if "카테고리:" in note:
                category = note.split("카테고리:")[-1].strip()
            elif "카테고리 " in note:
                category = note.split("카테고리 ")[-1].strip()
            
            if not category:
                continue
            
            # 카테고리별 카운트
            if category == "신규 계약":
                new_contracts += 1
            elif category == "유지 계약":
                renewals += 1
            elif category == "상담":
                consultations += 1
    
    # 분석 텍스트 생성
    analysis = f"{year}년 {month}월 업무 통계: 신규 계약 {new_contracts}건, 유지 계약 {renewals}건, 상담 {consultations}건"
    
    return {
        "new_contracts": new_contracts,
        "renewals": renewals,
        "consultations": consultations,
        "analysis": analysis
    }

