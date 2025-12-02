"""
Report Agent

리포트 생성 및 분석 에이전트
기존 Report 서비스를 활용합니다.
"""

from typing import Dict, Any, Optional
from .base_agent import BaseAgent


class ReportAgent(BaseAgent):
    """
    리포트 생성 및 분석 에이전트
    
    기존 Report 서비스를 래핑하여 각종 리포트를 생성하고 분석합니다.
    """
    
    def __init__(self):
        super().__init__(
            name="report",
            description="업무 리포트, 실적 분석, 통계 자료를 생성하는 에이전트입니다. "
                       "일간/주간/월간 리포트, 성과 분석 등을 제공합니다."
        )
        # Lazy loading: 실제 사용 시에만 서비스 로드
        self._llm_client = None
    
    @property
    def llm_client(self):
        """LLM Client lazy loading"""
        if self._llm_client is None:
            from app.llm.client import get_llm
            self._llm_client = get_llm(model="gpt-4o-mini", temperature=0.5)
        return self._llm_client
    
    async def process(self, query: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        리포트 생성 및 분석
        
        Args:
            query: 사용자 질문 (예: "이번 주 리포트", "실적 분석")
            context: 추가 컨텍스트 (user_id, date_range 등)
            
        Returns:
            str: 리포트 응답
        """
        try:
            # 리포트 생성 관련 시스템 프롬프트
            system_prompt = """당신은 업무 리포트와 데이터 분석을 전문으로 하는 AI 어시스턴트입니다.

역할:
- 업무 실적과 성과를 명확하게 정리하여 리포트를 작성합니다.
- 데이터를 분석하여 인사이트를 도출합니다.
- 개선 방안과 액션 아이템을 제안합니다.
- 시각적으로 이해하기 쉬운 형식으로 정보를 구조화합니다.

응답 스타일:
- 핵심 지표와 수치를 명확히 제시합니다.
- 긍정적인 부분과 개선이 필요한 부분을 균형있게 다룹니다.
- 구체적이고 실행 가능한 개선 방안을 제시합니다.
- 전문적이면서도 이해하기 쉬운 언어를 사용합니다."""

            # LLM을 통해 리포트 응답 생성
            response = await self.llm_client.acomplete(
                system_prompt=system_prompt,
                user_prompt=query
            )
            
            return response
            
        except Exception as e:
            return f"리포트 생성 중 오류가 발생했습니다: {str(e)}"
    
    def get_capabilities(self) -> list:
        """에이전트 기능 목록"""
        return [
            "일간/주간/월간 리포트 생성",
            "실적 분석",
            "성과 평가",
            "데이터 시각화",
            "개선 방안 제시",
        ]

