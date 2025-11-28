"""
고급 청킹 엔진
의미 단위 세밀 청킹 + LLM 재정제 기반
"""
import os
import hashlib
import re
from typing import List, Dict, Any, Optional
from datetime import date

from langchain.text_splitter import CharacterTextSplitter
from openai import OpenAI

from app.domain.report.schemas import CanonicalReport
from app.domain.report.metadata_extractor import (
    calculate_week_id,
    calculate_month_id,
    extract_customers,
    classify_tasks,
    is_pending_related,
    is_summary_related
)


CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "500"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "100"))


def generate_chunk_id(*parts: str) -> str:
    """청크 ID 생성"""
    combined = "|".join(str(p) for p in parts)
    hash_obj = hashlib.sha256(combined.encode('utf-8'))
    return hash_obj.hexdigest()[:32]


def _build_base_metadata(canonical: CanonicalReport) -> Dict[str, Any]:
    """
    공통 메타데이터 생성
    
    Returns:
        base_meta 딕셔너리
    """
    report_date = canonical.period_start if canonical.period_start else date.today()
    
    return {
        "report_id": canonical.report_id,
        "report_type": canonical.report_type,
        "date": report_date.isoformat(),
        "week_id": calculate_week_id(report_date),
        "month_id": calculate_month_id(report_date),
        "owner": canonical.owner,
        "is_pending": False,  # 기본값, 각 청크에서 오버라이드 가능
        "is_summary_related": False  # 기본값, 각 청크에서 오버라이드 가능
    }


def _extract_chunk_metadata(text: str, chunk_type: str) -> Dict[str, Any]:
    """
    청크 텍스트에서 자동 메타데이터 추출
    
    Args:
        text: 청크 텍스트
        chunk_type: 청크 타입
        
    Returns:
        추출된 메타데이터 딕셔너리
    """
    customers_list = extract_customers(text)
    tasks_list = classify_tasks(text)
    
    metadata = {
        "customers": ", ".join(customers_list) if customers_list else "",
        "tasks": ", ".join(tasks_list) if tasks_list else "",
        "is_pending": is_pending_related(text),
        "is_summary_related": is_summary_related(text)
    }
    
    # detail_chunk인 경우 time_range 추출
    if chunk_type == "detail_chunk":
        time_pattern = r'(\d{2}:\d{2})\s*[-~]\s*(\d{2}:\d{2})'
        matches = re.findall(time_pattern, text)
        if matches:
            metadata["time_range"] = f"{matches[0][0]}-{matches[0][1]}"
        else:
            metadata["time_range"] = ""
    
    return metadata


def _build_header_chunk(
    canonical: CanonicalReport,
    base_meta: Dict[str, Any],
    chunk_index: int
) -> Optional[Dict[str, Any]]:
    """
    헤더 청크 생성
    
    Returns:
        header_chunk 딕셔너리 또는 None
    """
    header_text = f"""작성일자: {canonical.period_start.isoformat() if canonical.period_start else ''}
작성자: {canonical.owner}"""
    
    # 금일 진행 업무 추가
    if canonical.metadata.get('금일_진행_업무'):
        금일_업무 = canonical.metadata.get('금일_진행_업무')
        if isinstance(금일_업무, list):
            header_text += f"\n금일 진행 업무:\n" + "\n".join([f"- {item}" for item in 금일_업무])
        else:
            header_text += f"\n금일 진행 업무: {금일_업무}"
    
    # 특이사항 추가
    if canonical.metadata.get('특이사항'):
        header_text += f"\n특이사항: {canonical.metadata.get('특이사항')}"
    
    if not header_text.strip():
        return None
    
    # 메타데이터 구성
    chunk_meta = _extract_chunk_metadata(header_text, "header_chunk")
    metadata = {
        **base_meta,
        **chunk_meta,
        "chunk_type": "header_chunk",
        "chunk_index": chunk_index,
        "time_range": ""
    }
    
    return {
        "id": generate_chunk_id(canonical.report_id, "header", "0"),
        "text": header_text,
        "metadata": metadata
    }


def _build_task_chunks(
    canonical: CanonicalReport,
    base_meta: Dict[str, Any],
    start_index: int
) -> List[Dict[str, Any]]:
    """
    Task 청크들 생성 (개별 detail_chunk)
    
    Returns:
        task_chunks 리스트
    """
    chunks = []
    chunk_index = start_index
    
    for task_idx, task in enumerate(canonical.tasks):
        if not task.description:
            continue
        
        # 시간대 처리 (없어도 정상 처리)
        time_str = ""
        time_range = ""
        if task.time_start and task.time_end:
            time_str = f"{task.time_start}~{task.time_end}"
            time_range = f"{task.time_start}-{task.time_end}"
        
        # 텍스트 구성
        task_text = f"{time_str} {task.description}".strip()
        if task.note:
            task_text += f"\n비고: {task.note}"
        
        # 메타데이터 구성
        chunk_meta = _extract_chunk_metadata(task_text, "detail_chunk")
        if time_range:
            chunk_meta["time_range"] = time_range
        
        metadata = {
            **base_meta,
            **chunk_meta,
            "chunk_type": "detail_chunk",
            "chunk_index": chunk_index,
            "task_id": task.task_id or f"task_{task_idx}"
        }
        
        chunks.append({
            "id": generate_chunk_id(canonical.report_id, "task", str(task_idx)),
            "text": task_text,
            "metadata": metadata
        })
        
        chunk_index += 1
    
    return chunks


def _build_issue_chunks(
    canonical: CanonicalReport,
    base_meta: Dict[str, Any],
    start_index: int
) -> List[Dict[str, Any]]:
    """
    Issue 청크들 생성 (개별 pending_chunk)
    
    Returns:
        issue_chunks 리스트
    """
    chunks = []
    chunk_index = start_index
    
    for issue_idx, issue in enumerate(canonical.issues):
        if not issue:
            continue
        
        # 메타데이터 구성
        chunk_meta = _extract_chunk_metadata(issue, "pending_chunk")
        metadata = {
            **base_meta,
            **chunk_meta,
            "chunk_type": "pending_chunk",
            "chunk_index": chunk_index,
            "time_range": ""
        }
        
        chunks.append({
            "id": generate_chunk_id(canonical.report_id, "issue", str(issue_idx)),
            "text": issue,
            "metadata": metadata
        })
        
        chunk_index += 1
    
    return chunks


def _build_plan_chunks(
    canonical: CanonicalReport,
    base_meta: Dict[str, Any],
    start_index: int
) -> List[Dict[str, Any]]:
    """
    Plan 청크들 생성 (개별 plan_chunk)
    
    Returns:
        plan_chunks 리스트
    """
    chunks = []
    chunk_index = start_index
    
    for plan_idx, plan in enumerate(canonical.plans):
        if not plan:
            continue
        
        # 메타데이터 구성
        chunk_meta = _extract_chunk_metadata(plan, "plan_chunk")
        metadata = {
            **base_meta,
            **chunk_meta,
            "chunk_type": "plan_chunk",
            "chunk_index": chunk_index,
            "time_range": ""
        }
        
        chunks.append({
            "id": generate_chunk_id(canonical.report_id, "plan", str(plan_idx)),
            "text": plan,
            "metadata": metadata
        })
        
        chunk_index += 1
    
    return chunks


def _recombine_detail_chunks(
    detail_chunks: List[Dict[str, Any]],
    base_meta: Dict[str, Any],
    start_index: int
) -> List[Dict[str, Any]]:
    """
    detail_chunk들을 시간대별로 2-3개씩 그룹화
    
    Args:
        detail_chunks: detail_chunk 리스트
        base_meta: 공통 메타데이터
        start_index: 시작 chunk_index
        
    Returns:
        그룹화된 청크 리스트 (grouped_detail_chunk 타입)
    """
    if not detail_chunks or len(detail_chunks) < 2:
        return []
    
    recombined = []
    chunk_index = start_index
    i = 0
    
    while i < len(detail_chunks):
        # 2-3개씩 그룹화
        group_size = 3 if i + 3 <= len(detail_chunks) else 2
        if group_size < 2:
            break
            
        group = detail_chunks[i:i+group_size]
        
        # 텍스트 결합
        combined_text = "\n".join([c["text"] for c in group])
        
        # time_range 계산
        time_ranges = [c["metadata"].get("time_range", "") for c in group if c["metadata"].get("time_range")]
        time_range = ""
        if time_ranges:
            start_time = time_ranges[0].split("-")[0] if "-" in time_ranges[0] else time_ranges[0]
            end_time = time_ranges[-1].split("-")[-1] if "-" in time_ranges[-1] else time_ranges[-1]
            time_range = f"{start_time}-{end_time}"
        
        # 메타데이터 구성
        chunk_meta = _extract_chunk_metadata(combined_text, "grouped_detail_chunk")
        if time_range:
            chunk_meta["time_range"] = time_range
        
        metadata = {
            **base_meta,
            **chunk_meta,
            "chunk_type": "grouped_detail_chunk",
            "chunk_index": chunk_index,
            "combined_count": group_size,
            "source_chunk_ids": [c["id"] for c in group]
        }
        
        recombined.append({
            "id": generate_chunk_id(group[0]["id"], "combined", str(chunk_index)),
            "text": combined_text,
            "metadata": metadata
        })
        
        chunk_index += 1
        i += group_size
    
    return recombined


def _apply_llm_refine(
    chunks: List[Dict[str, Any]],
    api_key: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    LLM 재정제 적용 (원문 보존, refined_text는 metadata에 저장)
    
    Args:
        chunks: 청크 리스트
        api_key: OpenAI API 키
        
    Returns:
        재정제된 청크 리스트 (원문 text는 보존)
    """
    if not api_key:
        api_key = os.getenv("OPENAI_API_KEY")
    
    if not api_key:
        return chunks
    
    client = OpenAI(api_key=api_key)
    
    for chunk in chunks:
        # detail_chunk와 plan_chunk만 재정제
        chunk_type = chunk["metadata"].get("chunk_type", "")
        if chunk_type not in ["detail_chunk", "plan_chunk", "grouped_detail_chunk"]:
            continue
        
        try:
            prompt = f"""다음 텍스트를 의미 단위의 문장 묶음으로 재정렬하세요.
불필요한 부분은 제거하고, 핵심 의미만 유지하세요.

원본:
{chunk["text"]}

재정렬된 텍스트:"""
            
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=1000
            )
            
            refined_text = response.choices[0].message.content.strip()
            if refined_text:
                # 원문은 보존하고, refined_text는 metadata에 저장
                chunk["metadata"]["refined_text"] = refined_text
        except Exception as e:
            # 재정제 실패 시 원문 유지
            pass
    
    return chunks


def chunk_daily_report(
    canonical: CanonicalReport,
    api_key: Optional[str] = None,
    use_llm_refine: bool = True
) -> List[Dict[str, Any]]:
    """
    일일 보고서를 의미 단위로 세밀하게 청킹
    
    Args:
        canonical: CanonicalReport 객체
        api_key: OpenAI API 키 (LLM 재정제용)
        use_llm_refine: LLM 재정제 사용 여부
        
    Returns:
        청크 리스트
    """
    # 1. 공통 메타데이터 생성
    base_meta = _build_base_metadata(canonical)
    
    chunks = []
    chunk_index = 0
    
    # 2. 헤더 청크 생성
    header_chunk = _build_header_chunk(canonical, base_meta, chunk_index)
    if header_chunk:
        chunks.append(header_chunk)
        chunk_index += 1
    
    # 3. Task 청크들 생성 (개별 detail_chunk)
    task_chunks = _build_task_chunks(canonical, base_meta, chunk_index)
    chunks.extend(task_chunks)
    task_chunk_count = len(task_chunks)
    chunk_index += task_chunk_count
    
    # 4. Issue 청크들 생성 (개별 pending_chunk)
    issue_chunks = _build_issue_chunks(canonical, base_meta, chunk_index)
    chunks.extend(issue_chunks)
    chunk_index += len(issue_chunks)
    
    # 5. Plan 청크들 생성 (개별 plan_chunk)
    plan_chunks = _build_plan_chunks(canonical, base_meta, chunk_index)
    chunks.extend(plan_chunks)
    chunk_index += len(plan_chunks)
    
    # 6. detail_chunk들을 시간대별로 그룹화 (grouped_detail_chunk 생성)
    if task_chunks:
        grouped_chunks = _recombine_detail_chunks(task_chunks, base_meta, chunk_index)
        chunks.extend(grouped_chunks)
    
    # 7. LLM 재정제 적용 (원문 보존)
    if use_llm_refine:
        chunks = _apply_llm_refine(chunks, api_key)
    
    return chunks
