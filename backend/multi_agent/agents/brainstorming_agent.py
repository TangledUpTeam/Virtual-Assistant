"""
Brainstorming Agent

브레인스토밍 및 창의적 아이디어 제안 에이전트
기존 BrainstormingService를 활용합니다.
"""

from typing import Dict, Any, Optional
from .base_agent import BaseAgent


class BrainstormingAgent(BaseAgent):
    """
    브레인스토밍 및 창의적 아이디어 제안 에이전트
    
    기존 BrainstormingService를 래핑하여 창의적인 아이디어와 
    브레인스토밍 기법을 제안합니다.
    """
    
    def __init__(self):
        super().__init__(
            name="brainstorming",
            description="창의적인 아이디어 발상과 브레인스토밍 기법을 제안하는 에이전트입니다. "
                       "문제 해결, 아이디어 도출, 창의적 사고 방법 등을 안내합니다."
        )
        # Lazy loading: 실제 사용 시에만 BrainstormingService 로드
        self._brainstorming_service = None
    
    @property
    def brainstorming_service(self):
        """BrainstormingService lazy loading"""
        if self._brainstorming_service is None:
            from app.domain.brainstorming.service import BrainstormingService
            self._brainstorming_service = BrainstormingService()
        return self._brainstorming_service
    
    async def process(self, query: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        브레인스토밍 제안 생성
        
        Args:
            query: 사용자 질문 (예: "팀 협업 방법", "창의적 아이디어 도출")
            context: 추가 컨텍스트 (context_count 등)
            
        Returns:
            str: 브레인스토밍 제안
        """
        try:
            # 컨텍스트에서 context_count 추출 (기본값: 3)
            context_count = 3
            if context and "context_count" in context:
                context_count = context["context_count"]
            
            # 브레인스토밍 제안 생성
            result = self.brainstorming_service.generate_suggestions(
                query=query,
                context_count=context_count
            )
            
            # 제안과 출처 포함한 응답 생성
            answer = result["suggestions"]
            
            # 출처 정보 추가
            if result.get("sources"):
                answer += "\n\n📚 **참고한 브레인스토밍 기법:**\n"
                for source in result["sources"]:
                    answer += f"- {source['title']} (유사도: {source['similarity']:.2f})\n"
            
            return answer
            
        except Exception as e:
            return f"브레인스토밍 제안 생성 중 오류가 발생했습니다: {str(e)}"
    
    def get_capabilities(self) -> list:
        """에이전트 기능 목록"""
        return [
            "창의적 아이디어 제안",
            "브레인스토밍 기법 안내",
            "문제 해결 방법 제시",
            "협업 방법 제안",
            "혁신적 사고 촉진",
        ]

