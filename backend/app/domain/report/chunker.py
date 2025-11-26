"""
보고서 청킹 유틸리티

CanonicalReport를 RAG용 청크로 변환하는 기능 제공
LLM 없이 Python 코드만으로 처리
"""
import uuid
import hashlib
from typing import List, Dict, Any

from app.domain.report.schemas import CanonicalReport, TaskItem, KPIItem


# ========================================
# 설정
# ========================================
MAX_CHUNK_LENGTH = 1000  # 최대 청크 텍스트 길이 (글자 수)


# ========================================
# ID 생성 함수
# ========================================
def generate_chunk_id(*parts: str) -> str:
    """
    결정적(deterministic) chunk ID 생성
    
    동일한 입력에 대해 항상 동일한 ID를 생성합니다.
    이를 통해 재실행 시 중복 데이터가 쌓이지 않습니다.
    
    Args:
        *parts: ID 생성에 사용할 문자열들
        
    Returns:
        SHA256 해시 기반 ID (32자)
    """
    # 모든 부분을 결합
    combined = "|".join(str(p) for p in parts)
    # SHA256 해시 생성 (32자로 축약)
    hash_obj = hashlib.sha256(combined.encode('utf-8'))
    return hash_obj.hexdigest()[:32]


# ========================================
# 메타데이터 생성 함수
# ========================================
def build_chunk_metadata(
    chunk_type: str,
    canonical: CanonicalReport,
    **kwargs
) -> Dict[str, Any]:
    """
    청크 메타데이터 자동 생성
    
    Args:
        chunk_type: 청크 타입 (task|kpi|issue|plan|summary)
        canonical: CanonicalReport 객체
        **kwargs: 청크 타입별 추가 메타데이터
        
    Returns:
        메타데이터 딕셔너리
    """
    # 공통 메타데이터
    metadata = {
        "chunk_type": chunk_type,
        "report_id": canonical.report_id,
        "report_type": canonical.report_type,
        "owner": canonical.owner,
        "doc_type": canonical.report_type,  # retriever에서 doc_type으로 필터링
    }
    
    # 날짜 정보 추가
    if canonical.period_start:
        metadata["period_start"] = canonical.period_start.isoformat()
        # 일일보고서의 경우 date 필드도 추가 (retriever에서 date로 검색)
        if canonical.report_type == "daily":
            metadata["date"] = canonical.period_start.isoformat()
    
    if canonical.period_end:
        metadata["period_end"] = canonical.period_end.isoformat()
    
    # 청크 타입별 추가 필드
    if chunk_type == "task":
        # task_id, task_status, time_slot
        if "task_id" in kwargs:
            metadata["task_id"] = kwargs["task_id"]
        if "task_status" in kwargs:
            metadata["task_status"] = kwargs["task_status"]
        if "time_slot" in kwargs:
            metadata["time_slot"] = kwargs["time_slot"]
    
    elif chunk_type == "kpi":
        # kpi_name, kpi_tags
        if "kpi_name" in kwargs:
            metadata["kpi_name"] = kwargs["kpi_name"]
        if "kpi_tags" in kwargs:
            metadata["kpi_tags"] = kwargs["kpi_tags"]
        elif "category" in kwargs:
            # category를 kpi_tags로 변환
            metadata["kpi_tags"] = [kwargs["category"]] if kwargs["category"] else []
    
    elif chunk_type == "issue":
        # issue_flag
        metadata["issue_flag"] = True
    
    elif chunk_type == "plan":
        # plan_flag
        metadata["plan_flag"] = True
    
    elif chunk_type == "summary":
        # 통계 정보
        if "task_count" in kwargs:
            metadata["task_count"] = kwargs["task_count"]
        if "kpi_count" in kwargs:
            metadata["kpi_count"] = kwargs["kpi_count"]
        if "issue_count" in kwargs:
            metadata["issue_count"] = kwargs["issue_count"]
        if "plan_count" in kwargs:
            metadata["plan_count"] = kwargs["plan_count"]
    
    # 분할 청크인 경우
    if "part" in kwargs:
        metadata["part"] = kwargs["part"]
        metadata["total_parts"] = kwargs["total_parts"]
    
    return metadata


# ========================================
# 헬퍼 함수
# ========================================
def _split_text_by_length(text: str, max_length: int) -> List[str]:
    """
    긴 텍스트를 최대 길이 기준으로 분할
    
    Args:
        text: 분할할 텍스트
        max_length: 최대 길이
        
    Returns:
        분할된 텍스트 리스트
    """
    if len(text) <= max_length:
        return [text]
    
    chunks = []
    start = 0
    while start < len(text):
        end = start + max_length
        chunk = text[start:end]
        chunks.append(chunk)
        start = end
    
    return chunks


def _create_chunk(
    chunk_id: str,
    text: str,
    metadata: Dict[str, Any]
) -> Dict[str, Any]:
    """
    청크 딕셔너리 생성
    
    Args:
        chunk_id: 청크 ID
        text: 임베딩할 텍스트
        metadata: 메타데이터
        
    Returns:
        청크 딕셔너리
    """
    return {
        "id": chunk_id,
        "text": text,
        "metadata": metadata
    }


# ========================================
# Task 청킹
# ========================================
def _chunk_task(
    task: TaskItem,
    canonical: CanonicalReport
) -> List[Dict[str, Any]]:
    """
    TaskItem을 청크로 변환
    
    Args:
        task: TaskItem 객체
        canonical: CanonicalReport 객체
        
    Returns:
        청크 리스트
    """
    # 텍스트 구성: title + description + 시간
    text_parts = []
    
    if task.title:
        text_parts.append(task.title)
    
    if task.description and task.description != task.title:
        text_parts.append(task.description)
    
    # 시간대 추가
    time_slot = None
    if task.time_start and task.time_end:
        time_slot = f"{task.time_start}~{task.time_end}"
        text_parts.append(time_slot)
    
    # 비고 추가
    if task.note:
        text_parts.append(f"비고: {task.note}")
    
    text = "\n".join(text_parts)
    
    # 메타데이터 생성
    metadata = build_chunk_metadata(
        chunk_type="task",
        canonical=canonical,
        task_id=task.task_id,
        task_status=task.status,
        time_slot=time_slot
    )
    
    # 텍스트 길이 체크 및 분할
    if len(text) <= MAX_CHUNK_LENGTH:
        # deterministic ID 생성
        chunk_id = generate_chunk_id(canonical.report_id, "task", task.task_id or "", "0")
        return [_create_chunk(chunk_id, text, metadata)]
    else:
        # 긴 텍스트는 분할
        text_parts = _split_text_by_length(text, MAX_CHUNK_LENGTH)
        chunks = []
        for idx, part in enumerate(text_parts):
            # deterministic ID 생성 (part index 포함)
            chunk_id = generate_chunk_id(canonical.report_id, "task", task.task_id or "", str(idx))
            # 분할 청크용 메타데이터 재생성
            part_metadata = build_chunk_metadata(
                chunk_type="task",
                canonical=canonical,
                task_id=task.task_id,
                task_status=task.status,
                time_slot=time_slot,
                part=idx + 1,
                total_parts=len(text_parts)
            )
            chunks.append(_create_chunk(chunk_id, part, part_metadata))
        return chunks


# ========================================
# KPI 청킹
# ========================================
def _chunk_kpi(
    kpi: KPIItem,
    canonical: CanonicalReport
) -> List[Dict[str, Any]]:
    """
    KPIItem을 청크로 변환
    
    Args:
        kpi: KPIItem 객체
        canonical: CanonicalReport 객체
        
    Returns:
        청크 리스트
    """
    # 텍스트 구성: kpi_name: value (unit)
    text_parts = [f"{kpi.kpi_name}: {kpi.value}"]
    
    if kpi.unit:
        text_parts.append(f"({kpi.unit})")
    
    if kpi.note:
        text_parts.append(f"\n비고: {kpi.note}")
    
    text = " ".join(text_parts)
    
    # 메타데이터 생성
    metadata = build_chunk_metadata(
        chunk_type="kpi",
        canonical=canonical,
        kpi_name=kpi.kpi_name,
        category=kpi.category
    )
    
    # 텍스트 길이 체크 및 분할
    if len(text) <= MAX_CHUNK_LENGTH:
        chunk_id = generate_chunk_id(canonical.report_id, "kpi", kpi.name or kpi.kpi_name or "", "0")
        return [_create_chunk(chunk_id, text, metadata)]
    else:
        text_parts = _split_text_by_length(text, MAX_CHUNK_LENGTH)
        chunks = []
        for idx, part in enumerate(text_parts):
            chunk_id = generate_chunk_id(canonical.report_id, "kpi", kpi.name or kpi.kpi_name or "", str(idx))
            # 분할 청크용 메타데이터 재생성
            part_metadata = build_chunk_metadata(
                chunk_type="kpi",
                canonical=canonical,
                kpi_name=kpi.kpi_name,
                category=kpi.category,
                part=idx + 1,
                total_parts=len(text_parts)
            )
            chunks.append(_create_chunk(chunk_id, part, part_metadata))
        return chunks


# ========================================
# Issue 청킹
# ========================================
def _chunk_issue(
    issue: str,
    canonical: CanonicalReport,
    issue_idx: int = 0
) -> List[Dict[str, Any]]:
    """
    Issue 문자열을 청크로 변환
    
    Args:
        issue: 이슈 텍스트
        canonical: CanonicalReport 객체
        
    Returns:
        청크 리스트
    """
    # 메타데이터 생성
    metadata = build_chunk_metadata(
        chunk_type="issue",
        canonical=canonical
    )
    
    # 텍스트 길이 체크 및 분할
    if len(issue) <= MAX_CHUNK_LENGTH:
        chunk_id = generate_chunk_id(canonical.report_id, "issue", str(issue_idx), "0")
        return [_create_chunk(chunk_id, issue, metadata)]
    else:
        text_parts = _split_text_by_length(issue, MAX_CHUNK_LENGTH)
        chunks = []
        for idx, part in enumerate(text_parts):
            chunk_id = generate_chunk_id(canonical.report_id, "issue", str(issue_idx), str(idx))
            # 분할 청크용 메타데이터 재생성
            part_metadata = build_chunk_metadata(
                chunk_type="issue",
                canonical=canonical,
                part=idx + 1,
                total_parts=len(text_parts)
            )
            chunks.append(_create_chunk(chunk_id, part, part_metadata))
        return chunks


# ========================================
# Plan 청킹
# ========================================
def _chunk_plan(
    plan: str,
    canonical: CanonicalReport,
    plan_idx: int = 0
) -> List[Dict[str, Any]]:
    """
    Plan 문자열을 청크로 변환
    
    Args:
        plan: 계획 텍스트
        canonical: CanonicalReport 객체
        
    Returns:
        청크 리스트
    """
    # 메타데이터 생성
    metadata = build_chunk_metadata(
        chunk_type="plan",
        canonical=canonical
    )
    
    # 텍스트 길이 체크 및 분할
    if len(plan) <= MAX_CHUNK_LENGTH:
        chunk_id = generate_chunk_id(canonical.report_id, "plan", str(plan_idx), "0")
        return [_create_chunk(chunk_id, plan, metadata)]
    else:
        text_parts = _split_text_by_length(plan, MAX_CHUNK_LENGTH)
        chunks = []
        for idx, part in enumerate(text_parts):
            chunk_id = generate_chunk_id(canonical.report_id, "plan", str(plan_idx), str(idx))
            # 분할 청크용 메타데이터 재생성
            part_metadata = build_chunk_metadata(
                chunk_type="plan",
                canonical=canonical,
                part=idx + 1,
                total_parts=len(text_parts)
            )
            chunks.append(_create_chunk(chunk_id, part, part_metadata))
        return chunks


# ========================================
# Summary 청킹 (전체 보고서 요약)
# ========================================
def _chunk_summary(canonical: CanonicalReport) -> List[Dict[str, Any]]:
    """
    전체 보고서를 요약 청크로 변환
    
    Args:
        canonical: CanonicalReport 객체
        
    Returns:
        청크 리스트
    """
    text_parts = []
    
    # 보고서 기본 정보
    text_parts.append(f"보고서 타입: {canonical.report_type}")
    text_parts.append(f"작성자: {canonical.owner}")
    
    if canonical.period_start:
        text_parts.append(f"기간: {canonical.period_start} ~ {canonical.period_end}")
    
    # Tasks 요약
    if canonical.tasks:
        text_parts.append(f"\n작업 {len(canonical.tasks)}건:")
        for task in canonical.tasks[:5]:  # 최대 5개만
            text_parts.append(f"- {task.title}")
        if len(canonical.tasks) > 5:
            text_parts.append(f"... 외 {len(canonical.tasks) - 5}건")
    
    # KPIs 요약
    if canonical.kpis:
        text_parts.append(f"\nKPI {len(canonical.kpis)}건:")
        for kpi in canonical.kpis[:5]:  # 최대 5개만
            text_parts.append(f"- {kpi.kpi_name}: {kpi.value}")
        if len(canonical.kpis) > 5:
            text_parts.append(f"... 외 {len(canonical.kpis) - 5}건")
    
    # Issues
    if canonical.issues:
        text_parts.append(f"\n이슈 {len(canonical.issues)}건:")
        for issue in canonical.issues:
            text_parts.append(f"- {issue}")
    
    # Plans
    if canonical.plans:
        text_parts.append(f"\n계획 {len(canonical.plans)}건:")
        for plan in canonical.plans:
            text_parts.append(f"- {plan}")
    
    text = "\n".join(text_parts)
    
    # 메타데이터 생성
    metadata = build_chunk_metadata(
        chunk_type="summary",
        canonical=canonical,
        task_count=len(canonical.tasks),
        kpi_count=len(canonical.kpis),
        issue_count=len(canonical.issues),
        plan_count=len(canonical.plans)
    )
    
    # 텍스트 길이 체크 및 분할
    if len(text) <= MAX_CHUNK_LENGTH:
        chunk_id = generate_chunk_id(canonical.report_id, "summary", "0")
        return [_create_chunk(chunk_id, text, metadata)]
    else:
        text_parts = _split_text_by_length(text, MAX_CHUNK_LENGTH)
        chunks = []
        for idx, part in enumerate(text_parts):
            chunk_id = generate_chunk_id(canonical.report_id, "summary", str(idx))
            # 분할 청크용 메타데이터 재생성
            part_metadata = build_chunk_metadata(
                chunk_type="summary",
                canonical=canonical,
                task_count=len(canonical.tasks),
                kpi_count=len(canonical.kpis),
                issue_count=len(canonical.issues),
                plan_count=len(canonical.plans),
                part=idx + 1,
                total_parts=len(text_parts)
            )
            chunks.append(_create_chunk(chunk_id, part, part_metadata))
        return chunks


# ========================================
# 메인 청킹 함수
# ========================================
def chunk_report(
    canonical_report: CanonicalReport,
    include_summary: bool = True
) -> List[Dict[str, Any]]:
    """
    CanonicalReport를 RAG용 청크 리스트로 변환
    
    Args:
        canonical_report: 정규화된 보고서 객체
        include_summary: 전체 요약 청크 포함 여부 (기본값: True)
        
    Returns:
        청크 리스트, 각 청크는 다음 구조:
        {
            "id": "uuid",
            "text": "임베딩할 텍스트",
            "metadata": {...}
        }
    """
    chunks = []
    
    # (1) Tasks 청킹
    for task in canonical_report.tasks:
        task_chunks = _chunk_task(task, canonical_report)
        chunks.extend(task_chunks)
    
    # (2) KPIs 청킹
    for kpi in canonical_report.kpis:
        kpi_chunks = _chunk_kpi(kpi, canonical_report)
        chunks.extend(kpi_chunks)
    
    # (3) Issues 청킹
    for idx, issue in enumerate(canonical_report.issues):
        issue_chunks = _chunk_issue(issue, canonical_report, issue_idx=idx)
        chunks.extend(issue_chunks)
    
    # (4) Plans 청킹
    for idx, plan in enumerate(canonical_report.plans):
        plan_chunks = _chunk_plan(plan, canonical_report, plan_idx=idx)
        chunks.extend(plan_chunks)
    
    # (5) Summary 청킹 (옵션)
    if include_summary:
        summary_chunks = _chunk_summary(canonical_report)
        chunks.extend(summary_chunks)
    
    return chunks


# ========================================
# 청크 통계 함수
# ========================================
def get_chunk_statistics(chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    청크 통계 정보 반환
    
    Args:
        chunks: 청크 리스트
        
    Returns:
        통계 정보 딕셔너리
    """
    stats = {
        "total_chunks": len(chunks),
        "chunk_types": {},
        "avg_text_length": 0,
        "max_text_length": 0,
        "min_text_length": float('inf')
    }
    
    total_length = 0
    
    for chunk in chunks:
        # 타입별 카운트
        chunk_type = chunk["metadata"].get("chunk_type", "unknown")
        stats["chunk_types"][chunk_type] = stats["chunk_types"].get(chunk_type, 0) + 1
        
        # 텍스트 길이 통계 (chunk_text 또는 text 키 모두 지원)
        text = chunk.get("chunk_text") or chunk.get("text", "")
        text_length = len(text)
        total_length += text_length
        stats["max_text_length"] = max(stats["max_text_length"], text_length)
        stats["min_text_length"] = min(stats["min_text_length"], text_length)
    
    if chunks:
        stats["avg_text_length"] = total_length / len(chunks)
        stats["min_text_length"] = stats["min_text_length"] if stats["min_text_length"] != float('inf') else 0
    else:
        stats["min_text_length"] = 0
    
    return stats

