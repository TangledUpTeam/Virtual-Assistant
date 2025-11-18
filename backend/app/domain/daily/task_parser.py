"""
Task Parser

자연어 업무 설명을 구조화된 TaskItem으로 변환

Author: AI Assistant
Created: 2025-11-18
"""
from typing import Dict, Any
import json
from app.llm.client import LLMClient


class TaskParser:
    """자연어 → TaskItem 변환기"""
    
    SYSTEM_PROMPT = """당신은 보험 설계사의 업무 기록을 정규화하는 AI입니다.

사용자의 자연어 업무 설명을 분석하여 다음을 추출하세요:
- title: 업무 제목 (간단명료)
- description: 상세 설명
- category: 업무 카테고리
- time_range: 시간대 (그대로 유지)

카테고리 분류 규칙:
- "상담", "고객", "연금", "실손", "암보험" → "고객 상담"
- "문서", "정리", "CRM", "시스템" → "내부 업무"  
- "회의", "미팅", "교육" → "회의/교육"
- "휴식", "땡땡이", "쉼" → "기타"
- "학습", "공부", "연구" → "학습"

반드시 JSON 형식으로만 응답:
{
  "title": "업무 제목",
  "description": "상세 설명",
  "category": "카테고리",
  "time_range": "시간대"
}
"""
    
    def __init__(self, llm_client: LLMClient):
        """
        초기화
        
        Args:
            llm_client: LLM 클라이언트
        """
        self.llm_client = llm_client
    
    async def parse(
        self,
        text: str,
        time_range: str
    ) -> Dict[str, Any]:
        """
        자연어를 TaskItem으로 변환
        
        Args:
            text: 사용자의 자연어 입력
            time_range: 시간대 (예: "09:00~10:00")
            
        Returns:
            TaskItem 딕셔너리
        """
        user_prompt = f"""시간대: {time_range}
업무 내용: {text}

위 업무를 분석하여 JSON으로 변환해주세요."""

        try:
            result = await self.llm_client.acomplete_json(
                system_prompt=self.SYSTEM_PROMPT,
                user_prompt=user_prompt,
                temperature=0.3,
                max_tokens=300
            )
            
            # time_range 보장
            result["time_range"] = time_range
            
            return result
        
        except Exception as e:
            print(f"[ERROR] Task parsing failed: {e}")
            # 기본 응답
            return {
                "title": text[:50],
                "description": text,
                "category": "기타",
                "time_range": time_range
            }
    
    def parse_sync(
        self,
        text: str,
        time_range: str
    ) -> Dict[str, Any]:
        """
        동기 버전: 자연어를 TaskItem으로 변환
        
        Args:
            text: 사용자의 자연어 입력
            time_range: 시간대
            
        Returns:
            TaskItem 딕셔너리
        """
        user_prompt = f"""시간대: {time_range}
업무 내용: {text}

위 업무를 분석하여 JSON으로 변환해주세요."""

        try:
            result = self.llm_client.complete_json(
                system_prompt=self.SYSTEM_PROMPT,
                user_prompt=user_prompt,
                temperature=0.3,
                max_tokens=300
            )
            
            # time_range 보장
            result["time_range"] = time_range
            
            return result
        
        except Exception as e:
            print(f"[ERROR] Task parsing failed: {e}")
            # 기본 응답
            return {
                "title": text[:50],
                "description": text,
                "category": "기타",
                "time_range": time_range
            }

