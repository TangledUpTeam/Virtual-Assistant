"""
메타데이터 자동 태깅 파서
"""
import re
from typing import List, Dict, Any
from datetime import datetime, date
from app.domain.report.schemas import CanonicalReport

def calculate_week_id(d: date) -> str:
    year, week, _ = d.isocalendar()
    return f"{year}-W{week:02d}"


def calculate_month_id(d: date) -> str:
    return d.strftime("%Y-%m")


def extract_customers(text: str) -> List[str]:
    pattern = r'[가-힣]{2,4}(?=\s*고객|님|씨|에게|와|과|의)'
    matches = re.findall(pattern, text)
    
    context_pattern = r'고객\s*([가-힣]{2,4})'
    context_matches = re.findall(context_pattern, text)
    
    all_names = list(set(matches + context_matches))
    return [name for name in all_names if len(name) >= 2]


def classify_tasks(text: str) -> List[str]:
    text_lower = text.lower()
    tasks = []
    
    if any(word in text_lower for word in ["상담", "리드", "문진", "신규"]):
        tasks.append("new_lead")
    
    if any(word in text_lower for word in ["갱신", "유지", "특약변경", "주소변경", "재계약"]):
        tasks.append("maintenance")
    
    if any(word in text_lower for word in ["보장분석", "포트폴리오", "리포트", "분석"]):
        tasks.append("reporting")
    
    if any(word in text_lower for word in ["자료요청", "자료대기", "추가요청", "대기"]):
        tasks.append("pending")
    
    if any(word in text_lower for word in ["입원", "수술", "청구", "사고", "보상"]):
        tasks.append("claim")
    
    return tasks if tasks else ["general"]


def extract_time_range(text: str) -> str:
    time_pattern = r'(\d{2}:\d{2})\s*[-~]\s*(\d{2}:\d{2})'
    matches = re.findall(time_pattern, text)
    if matches:
        return f"{matches[0][0]}-{matches[0][1]}"
    return ""


def is_pending_related(text: str) -> bool:
    pending_keywords = ["미종결", "대기", "보류", "추후", "예정"]
    return any(keyword in text for keyword in pending_keywords)


def is_summary_related(text: str) -> bool:
    summary_keywords = ["요약", "전체", "통계", "종합", "금일 진행"]
    return any(keyword in text for keyword in summary_keywords)


def build_metadata(
    chunk: Dict[str, Any],
    canonical: CanonicalReport
) -> Dict[str, Any]:
    text = chunk.get("text", "")
    chunk_type = chunk["metadata"].get("chunk_type", "todo_chunk")
    
    report_date = canonical.period_start if canonical.period_start else date.today()
    
    tasks_list = classify_tasks(text)
    customers_list = extract_customers(text)
    
    metadata = {
        "date": report_date.isoformat(),
        "week_id": calculate_week_id(report_date),
        "month_id": calculate_month_id(report_date),
        "chunk_type": chunk_type,
        "tasks": ", ".join(tasks_list) if tasks_list else "",
        "customers": ", ".join(customers_list) if customers_list else "",
        "is_pending": is_pending_related(text),
        "is_summary_related": is_summary_related(text),
        "doc_id": f"daily_{report_date.strftime('%Y_%m_%d')}",
        "chunk_index": chunk["metadata"].get("chunk_index", 0)
    }
    
    if chunk_type == "detail_chunk":
        time_range = extract_time_range(text)
        if time_range:
            metadata["time_range"] = time_range
    
    return metadata

