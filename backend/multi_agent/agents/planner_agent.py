"""
Planner Agent

일정 관리 및 계획 수립 에이전트
기존 TodayPlanGenerator 서비스를 활용합니다.
"""

from typing import Dict, Any, Optional
from datetime import date
from .base_agent import BaseAgent

# 일정 관리 및 계획 수립 에이전트 클래스
class PlannerAgent(BaseAgent):

    # 초기화 함수
    def __init__(self):
        super().__init__(
            name="planner",
            description="일정 관리, 계획 수립, 할 일 관리를 도와주는 에이전트입니다. "
                       "오늘의 계획, 업무 일정, 시간 관리 등을 지원합니다."
        )
        # Lazy loading: 실제 사용 시에만 서비스 로드
        self._plan_generator = None
    
    # @property: 메소드를 변수처럼 사용할 수 있게 해주는 기능
    @property
    def plan_generator(self):
        """TodayPlanGenerator lazy loading"""
        if self._plan_generator is None:
            from app.infrastructure.database import SessionLocal
            from app.domain.planner.tools import YesterdayReportTool
            from app.llm.client import LLMClient
            from app.domain.planner.today_plan_chain import TodayPlanGenerator
            
            # DB 세션 생성
            db = SessionLocal()
            
            # 의존성 초기화
            retriever_tool = YesterdayReportTool(db)
            llm_client = LLMClient(model="gpt-4o-mini", temperature=0.7)
            
            # TodayPlanGenerator 초기화
            self._plan_generator = TodayPlanGenerator(
                retriever_tool=retriever_tool,
                llm_client=llm_client,
                vector_retriever=None  # 선택적
            )
        return self._plan_generator
    
    # 일정 관리 및 계획 수립을 도와주는 비동기 함수
    async def process(self, query: str, context: Optional[Dict[str, Any]] = None) -> str:

        try:
            # 컨텍스트에서 owner와 target_date 추출
            owner = "user"  # 기본값
            target_date = date.today()  # 기본값: 오늘
            
            if context:
                owner = context.get("owner", owner)
                if "target_date" in context:
                    target_date = context["target_date"]
                elif "user_id" in context:
                    # user_id가 있으면 owner로 사용 (실제 구현에서는 user_id로 owner 조회)
                    owner = str(context["user_id"])
            
            # TodayPlanRequest 생성
            from app.domain.planner.schemas import TodayPlanRequest
            request = TodayPlanRequest(
                owner=owner,
                target_date=target_date
            )
            
            # TodayPlanGenerator를 통해 일정 생성
            response = await self.plan_generator.generate(request)
            
            # 응답 포맷팅
            result = f"📅 **오늘의 추천 일정**\n\n"
            
            if response.tasks:
                for i, task in enumerate(response.tasks, 1):
                    priority_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(task.priority, "⚪")
                    result += f"{i}. {priority_emoji} **{task.title}**\n"
                    if task.description:
                        result += f"   - {task.description}\n"
                    if task.expected_time:
                        result += f"   - 예상 시간: {task.expected_time}\n"
                    if task.category:
                        result += f"   - 카테고리: {task.category}\n"
                    result += "\n"
            else:
                result += "추천 일정이 생성되지 않았습니다.\n\n"
            
            if response.summary:
                result += f"**요약:** {response.summary}\n"
            
            return result
            
        except Exception as e:
            # 오류 발생 시 기본 LLM 응답으로 폴백
            try:
                from app.llm.client import get_llm
                llm_client = get_llm(model="gpt-4o-mini", temperature=0.7)
                
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

                response = await llm_client.acomplete(
                    system_prompt=system_prompt,
                    user_prompt=query
                )
                return response
            except Exception as fallback_error:
                return f"일정 관리 처리 중 오류가 발생했습니다: {str(e)}"

    # 에이전트 기능 목록 리턴해주는 함수    
    def get_capabilities(self) -> list:

        return [
            "오늘의 추천 일정 생성",
            "전날 미종결 업무 기반 계획",
            "일정 관리",
            "할 일 목록 작성",
            "시간 관리 조언",
            "업무 계획 수립",
            "생산성 향상 팁",
        ]

