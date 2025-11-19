"""
Daily Report Builder

FSM 결과를 CanonicalReport로 변환

Author: AI Assistant
Created: 2025-11-18
"""
from typing import List, Dict, Any, Set
from datetime import date
import hashlib
import re

from app.domain.report.schemas import (
    CanonicalReport,
    TaskItem,
    KPIItem
)


def calculate_text_similarity(text1: str, text2: str) -> float:
    """
    두 텍스트의 유사도 계산 (Jaccard similarity)
    
    Args:
        text1: 첫 번째 텍스트
        text2: 두 번째 텍스트
        
    Returns:
        유사도 (0.0 ~ 1.0)
    """
    # 정규화: 소문자, 공백 제거, 특수문자 제거
    def normalize(text: str) -> Set[str]:
        text = text.lower()
        text = re.sub(r'[^\w\s가-힣]', '', text)
        # 2글자 이상의 단어만 추출 (조사 제거)
        words = [w for w in text.split() if len(w) >= 2]
        return set(words)
    
    set1 = normalize(text1)
    set2 = normalize(text2)
    
    if not set1 or not set2:
        return 0.0
    
    intersection = set1 & set2
    union = set1 | set2
    
    return len(intersection) / len(union) if union else 0.0


def find_completed_main_tasks(
    main_tasks: List[Dict[str, Any]],
    time_tasks: List[Dict[str, Any]],
    similarity_threshold: float = 0.4
) -> Set[int]:
    """
    실제 수행된 main_tasks 인덱스 찾기
    
    Args:
        main_tasks: 예정된 업무 목록
        time_tasks: 실제 수행한 업무 목록
        similarity_threshold: 유사도 임계값 (기본 0.4 = 40%)
        
    Returns:
        실제 수행된 main_task의 인덱스 Set
    """
    completed_indices = set()
    
    for main_idx, main_task in enumerate(main_tasks):
        main_title = main_task.get("title", "")
        main_category = main_task.get("category", "")
        main_desc = main_task.get("description", "")
        
        # main_task의 전체 텍스트 (title + description + category)
        main_text = f"{main_title} {main_desc} {main_category}"
        
        for time_task in time_tasks:
            time_title = time_task.get("title", "")
            time_category = time_task.get("category", "")
            time_desc = time_task.get("description", "")
            
            # time_task의 전체 텍스트
            time_text = f"{time_title} {time_desc} {time_category}"
            
            # 유사도 계산
            similarity = calculate_text_similarity(main_text, time_text)
            
            # 카테고리가 같으면 bonus
            category_match = (
                main_category and time_category and 
                main_category.lower() == time_category.lower()
            )
            
            # 매칭 조건:
            # 1) 유사도가 임계값 이상이거나
            # 2) 카테고리가 같고 title에 공통 키워드가 있을 때
            if similarity >= similarity_threshold:
                completed_indices.add(main_idx)
                print(f"✅ 매칭: '{main_title}' ↔ '{time_title}' (유사도: {similarity:.2f})")
                break
            elif category_match and similarity >= 0.2:
                # 카테고리 같으면 낮은 유사도(20%)도 허용
                completed_indices.add(main_idx)
                print(f"✅ 카테고리 매칭: '{main_title}' ↔ '{time_title}' (유사도: {similarity:.2f})")
                break
    
    return completed_indices


def build_daily_report(
    owner: str,
    target_date: date,
    main_tasks: List[Dict[str, Any]],
    time_tasks: List[Dict[str, Any]]
) -> CanonicalReport:
    """
    일일보고서 생성
    
    실무 기준:
    - main_tasks = 아침에 선택한 "예정" 업무
    - time_tasks = FSM에서 입력한 "실제 수행" 업무
    - 실제 수행되지 않은 main_tasks → unresolved (미종결 업무)
    
    Args:
        owner: 작성자
        target_date: 날짜
        main_tasks: 금일 진행 업무 (예정, TodayPlan에서 선택)
        time_tasks: 시간대별 세부업무 (실제 수행, FSM 입력)
        
    Returns:
        CanonicalReport 객체
    """
    # report_id 생성 (deterministic)
    report_id = generate_report_id(owner, target_date)
    
    # 🔥 실제 수행된 main_task 인덱스 찾기 (fuzzy matching)
    completed_main_indices = find_completed_main_tasks(main_tasks, time_tasks)
    
    # 🔥 미종결 업무 = main_tasks 중 수행되지 않은 것
    unresolved_tasks = [
        main_tasks[i].get("title", "")
        for i in range(len(main_tasks))
        if i not in completed_main_indices
    ]
    
    # 🔥 plans = 모든 main_tasks의 title (예정 업무 전체)
    plans = [task.get("title", "") for task in main_tasks]
    
    # 🔥 tasks = time_tasks만 (실제 완료 업무)
    tasks = []
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
            status="completed",  # 실제 완료됨
            note=f"카테고리: {task_dict.get('category', '')}"
        )
        tasks.append(task)
    
    # 로그 출력
    print(f"\n📊 일일보고서 생성 요약:")
    print(f"  - 예정 업무(plans): {len(main_tasks)}개")
    print(f"  - 실제 완료(tasks): {len(time_tasks)}개")
    print(f"  - 미종결(issues): {len(unresolved_tasks)}개")
    if unresolved_tasks:
        print(f"  - 미종결 목록: {', '.join(unresolved_tasks)}")
    
    # CanonicalReport 생성
    return CanonicalReport(
        report_id=report_id,
        report_type="daily",
        owner=owner,
        period_start=target_date,
        period_end=target_date,
        tasks=tasks,  # 🔥 실제 완료 업무만
        kpis=[],
        issues=unresolved_tasks,  # 🔥 미종결 업무
        plans=plans,  # 🔥 예정 업무 전체
        metadata={
            "source": "daily_fsm",
            "planned_task_count": len(main_tasks),
            "completed_task_count": len(time_tasks),
            "unresolved_task_count": len(unresolved_tasks),
            "completion_rate": f"{len(completed_main_indices)}/{len(main_tasks)}" if main_tasks else "0/0"
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

