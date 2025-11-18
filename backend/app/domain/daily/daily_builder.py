"""
Daily Report Builder

FSM 결과를 CanonicalReport로 변환

Author: AI Assistant
Created: 2025-11-18
"""
from typing import List, Dict, Any
from datetime import date
import hashlib

from app.domain.report.schemas import (
    CanonicalReport,
    TaskItem,
    KPIItem
)


def build_daily_report(
    owner: str,
    target_date: date,
    main_tasks: List[Dict[str, Any]],
    time_tasks: List[Dict[str, Any]]
) -> CanonicalReport:
    """
    일일보고서 생성
    
    Args:
        owner: 작성자
        target_date: 날짜
        main_tasks: 금일 진행 업무 (TodayPlan에서 선택된 것)
        time_tasks: 시간대별 세부업무 (FSM이 생성한 것)
        
    Returns:
        CanonicalReport 객체
    """
    # report_id 생성 (deterministic)
    report_id = generate_report_id(owner, target_date)
    
    # TaskItem 변환
    tasks = []
    
    # 1. 금일 진행 업무 추가
    for i, task_dict in enumerate(main_tasks):
        task = TaskItem(
            task_id=f"main_{i+1}",
            title=task_dict.get("title", ""),
            description=task_dict.get("description", ""),
            time_start="",
            time_end="",
            status="planned",  # 진행 예정
            note=f"카테고리: {task_dict.get('category', '')}"
        )
        tasks.append(task)
    
    # 2. 시간대별 세부업무 추가
    for i, task_dict in enumerate(time_tasks):
        time_range = task_dict.get("time_range", "")
        time_start, time_end = "", ""
        
        if "~" in time_range:
            parts = time_range.split("~")
            time_start = parts[0].strip()
            time_end = parts[1].strip() if len(parts) > 1 else ""
        
        task = TaskItem(
            task_id=f"time_{i+1}",
            title=task_dict.get("title", ""),
            description=task_dict.get("description", ""),
            time_start=time_start,
            time_end=time_end,
            status="completed",  # 완료됨
            note=f"카테고리: {task_dict.get('category', '')}"
        )
        tasks.append(task)
    
    # CanonicalReport 생성
    return CanonicalReport(
        report_id=report_id,
        report_type="daily",
        owner=owner,
        period_start=target_date,
        period_end=target_date,
        tasks=tasks,
        kpis=[],
        issues=[],
        plans=[],
        metadata={
            "source": "daily_fsm",
            "main_task_count": len(main_tasks),
            "time_task_count": len(time_tasks),
            "total_task_count": len(tasks)
        }
    )


def generate_report_id(owner: str, target_date: date) -> str:
    """
    보고서 ID 생성 (deterministic)
    
    Args:
        owner: 작성자
        target_date: 날짜
        
    Returns:
        보고서 ID
    """
    key = f"daily_{owner}_{target_date.isoformat()}"
    hash_obj = hashlib.sha256(key.encode('utf-8'))
    return hash_obj.hexdigest()[:32]

