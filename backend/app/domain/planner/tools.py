"""
Report Retrieval Tool

전날 보고서에서 미종결 업무와 익일 계획을 추출합니다.

Author: AI Assistant
Created: 2025-11-18
"""
from typing import Dict, List, Any
from datetime import date, timedelta
from chromadb import Collection

from app.domain.search.retriever import UnifiedRetriever


class YesterdayReportTool:
    """전날 보고서 검색 도구"""
    
    def __init__(self, retriever: UnifiedRetriever):
        """
        초기화
        
        Args:
            retriever: UnifiedRetriever 인스턴스
        """
        self.retriever = retriever
    
    def get_yesterday_report(
        self,
        owner: str,
        target_date: date
    ) -> Dict[str, Any]:
        """
        전날 보고서에서 미종결 업무와 익일 계획 추출
        
        Args:
            owner: 작성자명
            target_date: 기준 날짜 (오늘)
            
        Returns:
            {
                "unresolved": List[str],  # 미종결 업무 (issues)
                "next_day_plan": List[str],  # 익일 계획 (plans)
                "raw_chunks": List[dict],  # 원본 청크들
                "found": bool  # 데이터 발견 여부
            }
        """
        # 전날 날짜 계산
        yesterday = target_date - timedelta(days=1)
        yesterday_str = yesterday.isoformat()
        
        # 전날 보고서 검색
        results = self.retriever.search_daily(
            query=f"{owner} 업무 보고서" if owner else "업무 보고서",
            owner=owner if owner else None,
            single_date=yesterday_str,
            n_results=20  # 충분히 많이 가져오기
        )
        
        # 결과 분류
        unresolved = []  # issue 타입
        next_day_plan = []  # plan 타입
        tasks = []  # task 타입
        raw_chunks = []
        
        for result in results:
            chunk_type = result.chunk_type
            text = result.text
            metadata = result.metadata
            
            # 청크 정보 저장
            raw_chunks.append({
                "chunk_id": result.chunk_id,
                "chunk_type": chunk_type,
                "text": text,
                "metadata": metadata
            })
            
            # chunk_type에 따라 분류
            if chunk_type == "issue":
                unresolved.append(text)
            elif chunk_type == "plan":
                next_day_plan.append(text)
            elif chunk_type == "task":
                tasks.append(text)
        
        return {
            "unresolved": unresolved,
            "next_day_plan": next_day_plan,
            "tasks": tasks,
            "raw_chunks": raw_chunks,
            "found": len(results) > 0,
            "search_date": yesterday_str,
            "owner": owner
        }


def get_yesterday_report(
    owner: str,
    target_date: date,
    retriever: UnifiedRetriever
) -> Dict[str, Any]:
    """
    헬퍼 함수: 전날 보고서 가져오기
    
    Args:
        owner: 작성자명
        target_date: 기준 날짜
        retriever: UnifiedRetriever 인스턴스
        
    Returns:
        전날 보고서 정보 딕셔너리
    """
    tool = YesterdayReportTool(retriever)
    return tool.get_yesterday_report(owner, target_date)

