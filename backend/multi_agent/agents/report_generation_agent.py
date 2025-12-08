"""
Report Generation Agent

보고서 작성 및 생성 전문 에이전트
- 일일보고서 FSM 입력/빌드 (daily_fsm.py, daily_builder.py)
- 주간/월간 보고서 자동 생성 (weekly/monthly chain)
- HTML/PDF 생성 및 Canonical 변환
- 상태 기반 워크플로우형 Agent
"""

from typing import Any, Dict, Optional
from datetime import date

from multi_agent.agents.report_base import ReportBaseAgent
from multi_agent.agents.report_main_router import ReportPromptRegistry
from app.domain.report.daily.daily_fsm import DailyReportFSM
from app.domain.report.daily.task_parser import TaskParser
from app.domain.report.daily.daily_builder import build_daily_report
from app.domain.report.weekly.chain import generate_weekly_report
from app.domain.report.monthly.chain import generate_monthly_report
from app.reporting.html_renderer import render_report_html
from app.llm.client import LLMClient


class ReportGenerationAgent(ReportBaseAgent):
    """보고서 작성 및 생성 에이전트"""
    
    def __init__(self, llm_client: Optional[LLMClient] = None, prompt_registry=None):
        """초기화"""
        super().__init__(
            name="ReportGenerationAgent",
            description="일일/주간/월간 보고서 작성 및 생성을 도와주는 에이전트입니다. FSM 기반 대화형 일일보고서 작성과 주간/월간 보고서 자동 생성을 지원합니다.",
            llm_client=llm_client
        )
        self.prompt_registry = prompt_registry or ReportPromptRegistry
        
        # TaskParser 초기화
        self.task_parser = TaskParser(self.llm, prompt_registry=self.prompt_registry)
        
        # FSM 초기화
        self.fsm = DailyReportFSM(self.task_parser)

    def configure_prompts(self, prompt_registry):
        """Prompt registry 주입 (router에서 호출)."""
        self.prompt_registry = prompt_registry or ReportPromptRegistry
        if hasattr(self.task_parser, "prompt_registry"):
            self.task_parser.prompt_registry = self.prompt_registry
    
    async def process(self, query: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        보고서 요청 처리
        
        Args:
            query: 사용자 질문
            context: {
                "action": "daily_start|daily_answer|weekly_generate|monthly_generate",
                "owner": str,
                "target_date": date,
                ...
            }
            
        Returns:
            처리 결과 문자열
        """
        if context and context.get("prompt_registry"):
            self.configure_prompts(context.get("prompt_registry"))

        if not context:
            return "보고서 작성을 위해서는 추가 정보가 필요합니다."
        
        action = context.get("action")
        
        if action == "daily_start":
            return await self._start_daily_report(context)
        elif action == "daily_answer":
            return await self._process_daily_answer(context)
        elif action == "weekly_generate":
            return await self._generate_weekly_report(context)
        elif action == "monthly_generate":
            return await self._generate_monthly_report(context)
        else:
            return "알 수 없는 보고서 작업입니다. action을 지정해주세요."
    
    async def _start_daily_report(self, context: Dict[str, Any]) -> str:
        """일일보고서 FSM 시작"""
        # 실제 구현은 기존 API 엔드포인트와 동일
        # 여기서는 간략화된 응답만 반환
        return "일일보고서 작성을 시작합니다. 시간대별로 업무 내용을 입력해주세요."
    
    async def _process_daily_answer(self, context: Dict[str, Any]) -> str:
        """일일보고서 FSM 답변 처리"""
        # 실제 구현은 기존 API 엔드포인트와 동일
        return "답변이 저장되었습니다. 다음 시간대를 입력해주세요."
    
    async def _generate_weekly_report(self, context: Dict[str, Any]) -> str:
        """주간보고서 생성"""
        # owner는 더 이상 필수 아님 (단일 워크스페이스로 동작)
        target_date = context.get("target_date", date.today())
        
        try:
            # DB 세션이 필요하므로 여기서는 메시지만 반환
            # 실제 생성은 API 엔드포인트에서 수행
            return f"주간보고서 생성을 시작합니다."
            
        except Exception as e:
            return f"주간보고서 생성 중 오류: {str(e)}"
    
    async def _generate_monthly_report(self, context: Dict[str, Any]) -> str:
        """월간보고서 생성"""
        # owner는 더 이상 필수 아님 (단일 워크스페이스로 동작)
        year = context.get("year")
        month = context.get("month")
        
        if not year or not month:
            return "년도(year), 월(month) 정보가 필요합니다."
        
        try:
            return f"{year}년 {month}월 월간보고서 생성을 시작합니다."
            
        except Exception as e:
            return f"월간보고서 생성 중 오류: {str(e)}"
    
    # ========================================
    # 직접 호출용 메서드 (API 엔드포인트용)
    # ========================================
    
    def get_fsm(self) -> DailyReportFSM:
        """FSM 인스턴스 반환 (API에서 직접 사용)"""
        return self.fsm
    
    def get_task_parser(self) -> TaskParser:
        """TaskParser 인스턴스 반환"""
        return self.task_parser

