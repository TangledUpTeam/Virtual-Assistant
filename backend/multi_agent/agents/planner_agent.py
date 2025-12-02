"""
Planner Agent

일정 관리 및 계획 수립 에이전트
기존 Daily/Plan 서비스를 활용합니다.
"""

from typing import Dict, Any, Optional
from .base_agent import BaseAgent


class PlannerAgent(BaseAgent):
    """
    일정 관리 및 계획 수립 에이전트
    
    기존 Daily/Plan 서비스를 래핑하여 일정 관리와 계획 수립을 지원합니다.
    """
    
    def __init__(self):
        super().__init__(
            name="planner",
            description="일정 관리, 계획 수립, 할 일 관리를 도와주는 에이전트입니다. "
                       "오늘의 계획, 업무 일정, 시간 관리 등을 지원합니다."
        )
        # Lazy loading: 실제 사용 시에만 서비스 로드
        self._llm_client = None
    
    @property
    def llm_client(self):
        """LLM Client lazy loading"""
        if self._llm_client is None:
            from app.llm.client import get_llm
            self._llm_client = get_llm(model="gpt-4o-mini", temperature=0.7)
        return self._llm_client
    
    async def process(self, query: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        일정 관리 및 계획 수립
        
        Args:
            query: 사용자 질문 (예: "오늘 할 일", "일정 추가")
            context: 추가 컨텍스트 (user_id, date 등)
            
        Returns:
            str: 일정 관리 응답
        """
        try:
            # 일정 관리 관련 시스템 프롬프트
            system_prompt = """당신은 일정 관리와 계획 수립을 도와주는 AI 어시스턴트입니다.

역할:
- 사용자의 일정을 효율적으로 관리하도록 도와줍니다.
- 할 일 목록을 작성하고 우선순위를 정하는 데 도움을 줍니다.
- 시간 관리 팁과 생산성 향상 방법을 제안합니다.
- 업무와 개인 일정의 균형을 맞추도록 조언합니다.

응답 스타일:
- 구체적이고 실행 가능한 조언을 제공합니다.
- 시간대별로 일정을 구조화하여 제시합니다.
- 우선순위와 중요도를 명확히 표시합니다.
- 친근하고 격려하는 톤을 유지합니다."""

            # LLM을 통해 일정 관리 응답 생성
            response = await self.llm_client.acomplete(
                system_prompt=system_prompt,
                user_prompt=query
            )
            
            return response
            
        except Exception as e:
            return f"일정 관리 처리 중 오류가 발생했습니다: {str(e)}"
    
    def get_capabilities(self) -> list:
        """에이전트 기능 목록"""
        return [
            "일정 관리",
            "할 일 목록 작성",
            "시간 관리 조언",
            "업무 계획 수립",
            "생산성 향상 팁",
        ]

