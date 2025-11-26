"""
Weekly Report Chain

주간 보고서 자동 생성 체인
target_date 기준으로 해당 주의 월~금 일일보고서를 조회하여 주간 보고서를 자동 생성
"""
from datetime import date, timedelta
from typing import List, Optional
from sqlalchemy.orm import Session
import uuid
import re

from app.domain.report.schemas import CanonicalReport, TaskItem, KPIItem
from app.domain.daily.repository import DailyReportRepository
from app.domain.daily.models import DailyReport
from app.infrastructure.vector_store import get_unified_collection
from app.domain.search.retriever import UnifiedRetriever
from app.llm.client import get_llm
from app.core.config import settings


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


def filter_person_names(text: str) -> bool:
    """
    사람 이름이 포함된 텍스트인지 확인
    
    Args:
        text: 확인할 텍스트
        
    Returns:
        True: 사람 이름이 포함됨, False: 포함되지 않음
    """
    # 한국 성씨 패턴 (김, 박, 최, 이 등)
    person_name_pattern = r'\b(김|박|최|이)[가-힣]{1,3}\b'
    return bool(re.search(person_name_pattern, text))


def generate_weekly_important_tasks(
    tasks: List[TaskItem],
    llm_client=None
) -> List[str]:
    """
    주간 보고서의 요일별 세부 업무에서 중요한 업무 3개 생성
    
    우선순위 기준:
    1) 매출 또는 유지율에 직접 영향
    2) 클레임·특약 점검 등 고객 리스크 관리
    3) 규제·법적 준수 필요 업무
    4) 보험금 청구 등 민원 가능성 높은 업무
    5) 여러 고객에게 반복적으로 영향
    6) 지연 시 리스크 큰 업무(마감 등)
    
    Args:
        tasks: 주간 보고서의 모든 TaskItem 리스트 (요일별 세부 업무)
        llm_client: LLM 클라이언트 (None이면 생성)
        
    Returns:
        주간 중요 업무 리스트 (최대 3개, 큰 카테고리 형태)
    """
    try:
        if not tasks:
            print(f"[WARNING] 주간 중요 업무 생성: tasks가 비어있음")
            return []
        
        # TaskItem을 텍스트로 변환
        task_texts = []
        for task in tasks:
            task_str = task.title
            if task.description:
                task_str += f": {task.description}"
            task_texts.append(task_str)
        
        if not task_texts:
            return []
        
        # LLM 클라이언트 생성
        if llm_client is None:
            llm_client = get_llm()
        
        system_prompt = """너는 보험 설계사의 주간 중요 업무를 선정하는 AI입니다.

주어진 주간 보고서의 요일별 세부 업무 항목들을 분석하여, 다음 우선순위 기준에 따라 중요한 업무 3개를 큰 카테고리 형태로 요약하세요.

우선순위 기준 (높은 순서대로):
1) 매출 또는 유지율에 직접 영향 (신규 계약, 갱신, 해지 방지 등)
2) 클레임·특약 점검 등 고객 리스크 관리 (보험금 청구, 특약 확인, 위험 관리)
3) 규제·법적 준수 필요 업무 (법규 준수, 서류 제출, 마감 등)
4) 보험금 청구 등 민원 가능성 높은 업무 (청구 처리, 민원 대응)
5) 여러 고객에게 반복적으로 영향 (대량 처리, 일괄 업무)
6) 지연 시 리스크 큰 업무 (마감일, 제출 기한 등)

규칙:
1. 반드시 3개의 중요 업무를 생성
2. 각 업무는 큰 카테고리 형태로 요약 (예: "고객 리스크 관리 및 클레임 처리", "신규 계약 및 매출 확대", "규제 준수 및 마감 업무")
3. 구체적인 고객 이름이나 개별 업무가 아닌, 전체적인 업무 카테고리로 작성
4. 위 우선순위 기준에 가장 잘 맞는 업무들을 선정
5. 유사한 업무들은 하나의 카테고리로 묶어서 요약

반드시 다음 JSON 형식으로만 응답:
{
  "important_tasks": [
    "중요 업무 1 (큰 카테고리)",
    "중요 업무 2 (큰 카테고리)",
    "중요 업무 3 (큰 카테고리)"
  ]
}"""

        # 상위 50개만 사용 (너무 많으면 토큰 초과)
        sample_tasks = task_texts[:50]
        user_prompt = f"""다음은 주간 보고서의 요일별 세부 업무 항목들입니다:

{chr(10).join([f"- {task[:150]}" for task in sample_tasks])}

위 업무 항목들을 분석하여, 우선순위 기준에 따라 중요한 업무 3개를 큰 카테고리 형태로 요약해주세요."""

        llm_response = llm_client.complete_json(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.7,
            max_tokens=500
        )
        
        important_tasks = llm_response.get("important_tasks", [])
        
        # 최대 3개로 제한 및 빈 문자열 제거
        important_tasks = [t.strip() for t in important_tasks if t and t.strip()][:3]
        
        print(f"📌 주간 중요 업무 생성 완료: {len(important_tasks)}개")
        for idx, task in enumerate(important_tasks, 1):
            print(f"   {idx}. {task}")
        
        return important_tasks
        
    except Exception as e:
        print(f"[ERROR] 주간 중요 업무 생성 실패: {e}")
        import traceback
        traceback.print_exc()
        return []


def generate_weekly_goals(
    owner: str,
    period_start: date,
    period_end: date,
    llm_client=None
) -> List[str]:
    """
    벡터DB에서 주간 데이터를 검색하여 주간 업무 목표 3개 생성
    
    Args:
        owner: 작성자
        period_start: 시작 날짜 (월요일)
        period_end: 종료 날짜 (금요일)
        llm_client: LLM 클라이언트 (None이면 생성)
        
    Returns:
        주간 업무 목표 리스트 (최대 3개)
    """
    try:
        # 1. 벡터DB에서 주간 데이터 검색
        collection = get_unified_collection()
        retriever = UnifiedRetriever(
            collection=collection,
            openai_api_key=settings.OPENAI_API_KEY
        )
        
        # 주간 범위의 일일보고서 데이터 검색 (period_start와 period_end를 사용하여 한 번에 검색)
        all_results = retriever.search_daily(
            query=f"{owner} 주간 업무 계획 목표",
            owner=owner,
            period_start=period_start.isoformat(),
            period_end=period_end.isoformat(),
            n_results=50,  # 충분한 데이터 수집
            chunk_types=["task", "plan"]
        )
        
        if not all_results:
            print(f"[WARNING] 주간 데이터를 찾을 수 없음: {owner}, {period_start}~{period_end}")
            return []
        
        print(f"[INFO] 벡터DB 검색 완료: {len(all_results)}개 청크 발견")
        
        # 2. 사람 이름이 포함된 업무 제외
        filtered_texts = []
        for result in all_results:
            text = result.text
            if not filter_person_names(text):
                filtered_texts.append(text)
        
        if not filtered_texts:
            print(f"[WARNING] 필터링 후 데이터가 없음")
            return []
        
        print(f"[INFO] 사람 이름 필터링 후: {len(filtered_texts)}개 청크")
        
        # 3. LLM으로 주간 업무 목표 3개 생성
        if llm_client is None:
            llm_client = get_llm()
        
        system_prompt = """너는 보험 설계사의 주간 업무 목표를 생성하는 AI입니다.

주어진 주간 업무 데이터를 분석하여, 한 주간의 큰 계획으로 요약한 주간 업무 목표를 3개 생성하세요.

규칙:
1. 반드시 3개의 목표를 생성
2. 구체적이고 실행 가능한 목표로 작성
3. 사람 이름이 포함된 업무는 제외 (이미 필터링됨)
4. 주간 단위의 큰 계획으로 요약
5. 업무의 공통 패턴과 핵심 목표를 추출

반드시 다음 JSON 형식으로만 응답:
{
  "goals": [
    "목표 1",
    "목표 2",
    "목표 3"
  ]
}"""

        # 상위 30개만 사용 (너무 많으면 토큰 초과)
        sample_texts = filtered_texts[:30]
        user_prompt = f"""다음은 {owner}의 {period_start}~{period_end} 주간 업무 데이터입니다:

{chr(10).join([f"- {text[:200]}" for text in sample_texts])}

위 데이터를 분석하여 주간 업무 목표 3개를 생성해주세요."""

        llm_response = llm_client.complete_json(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.7,
            max_tokens=500
        )
        
        goals = llm_response.get("goals", [])
        
        # 최대 3개로 제한 및 빈 문자열 제거
        goals = [g.strip() for g in goals if g and g.strip()][:3]
        
        return goals
        
    except Exception as e:
        print(f"[ERROR] 주간 업무 목표 생성 실패: {e}")
        import traceback
        traceback.print_exc()
        return []


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
    
    # 7. 주간 업무 목표 생성 (벡터DB 기반)
    llm_client = get_llm()
    weekly_goals = generate_weekly_goals(
        owner=owner,
        period_start=monday,
        period_end=friday,
        llm_client=llm_client
    )
    
    print(f"📋 주간 업무 목표 생성 완료: {len(weekly_goals)}개")
    for idx, goal in enumerate(weekly_goals, 1):
        print(f"   {idx}. {goal}")
    
    # 8. 주간 중요 업무 생성 (요일별 세부 업무에서 추출)
    important_tasks = generate_weekly_important_tasks(
        tasks=tasks,
        llm_client=llm_client
    )
    
    # 9. CanonicalReport 생성
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
            "week_dates": [monday.isoformat(), friday.isoformat()],
            "weekly_goals": weekly_goals,  # 주간 업무 목표
            "important_tasks": important_tasks  # 주간 중요 업무 추가
        }
    )
    
    return report

