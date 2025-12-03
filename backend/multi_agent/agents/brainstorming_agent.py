"""
Brainstorming Agent

브레인스토밍 및 창의적 아이디어 제안 에이전트
기존 BrainstormingService를 활용합니다.
"""

from typing import Dict, Any, Optional
from .base_agent import BaseAgent

# 브레인스토밍 에이전트 클래스
class BrainstormingAgent(BaseAgent):

    # 초기화 함수    
    def __init__(self):
        super().__init__(
            name="brainstorming",
            description="창의적인 아이디어 발상과 브레인스토밍 기법을 제안하는 에이전트입니다. "
                       "문제 해결, 아이디어 도출, 창의적 사고 방법 등을 안내합니다."
        )
        # Lazy loading: 실제 사용 시에만 BrainstormingService 로드
        self._brainstorming_service = None
    
    # @property: 메소드를 변수처럼 사용할 수 있게 해주는 기능
    @property
    def brainstorming_service(self):
        """BrainstormingService lazy loading"""
        if self._brainstorming_service is None:
            from app.domain.brainstorming.service import BrainstormingService
            self._brainstorming_service = BrainstormingService()
        return self._brainstorming_service
    
    # 브레인스토밍 진행하는 비동기 함수
    async def process(self, query: str, context: Optional[Dict[str, Any]] = None) -> str:

        try:
            # 사용자가 명시적으로 시작을 원하거나, Supervisor가 강력하게 추천한 경우
            # RAG 검색 대신 "제안" 모드로 응답
            
            # 간단한 키워드 체크로 시작 의도 파악
            start_keywords = ["시작", "할래", "해줘", "켜줘", "열어줘", "고고", "좋아", "응"]
            # 아이디어가 없거나 필요하다는 표현도 제안 트리거로 포함
            need_keywords = ["떠오르지", "안 나", "막막해", "필요해", "없을까", "만들고", "하고싶", "안 떠올라", "굳었어", "떠올", "생각이", "아이디어"]
            
            is_start_intent = any(k in query for k in start_keywords)
            is_need_intent = any(k in query for k in need_keywords)
            
            if is_start_intent or is_need_intent:
                return "SUGGESTION: 브레인스토밍 도구를 실행해서 아이디어를 발전시켜 볼까요?"
            
            # 컨텍스트에서 context_count 추출 (기본값: 3)
            context_count = 3
            if context and "context_count" in context:
                context_count = context["context_count"]
            
            # 브레인스토밍 제안 생성 (RAG)
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
            
            # 마지막에 제안 메시지 추가
            answer += "\n\n💡 **브레인스토밍 도구를 실행할까요?**"
            
            return answer
            
        except Exception as e:
            return f"브레인스토밍 제안 생성 중 오류가 발생했습니다: {str(e)}"
    
    # 브레인스토밍 에이전트 기능 목록 리턴
    def get_capabilities(self) -> list:
        
        return [
            "창의적 아이디어 제안",
            "브레인스토밍 기법 안내",
            "문제 해결 방법 제시",
            "협업 방법 제안",
            "혁신적 사고 촉진",
        ]

