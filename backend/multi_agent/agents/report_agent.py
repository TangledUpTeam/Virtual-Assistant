"""
Report Agent

리포트 생성 및 분석 에이전트
기존 Report 서비스를 활용합니다.
"""

from typing import Dict, Any, Optional
from datetime import date
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
        self._report_export_service = None
        self._llm_client = None
    
    @property
    def report_export_service(self):
        """ReportExportService lazy loading"""
        if self._report_export_service is None:
            from app.reporting.service.report_export_service import ReportExportService
            self._report_export_service = ReportExportService()
        return self._report_export_service
    
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
            context: 추가 컨텍스트 (user_id, date_range, owner 등)
            
        Returns:
            str: 리포트 응답
        """
        try:
            from app.infrastructure.database import SessionLocal
            from datetime import date, timedelta
            from app.domain.daily.repository import DailyReportRepository
            from app.domain.weekly.repository import WeeklyReportRepository
            from app.domain.monthly.repository import MonthlyReportRepository
            from app.domain.performance.repository import PerformanceReportRepository
            from app.domain.report.core.canonical_models import CanonicalReport
            
            # 컨텍스트에서 정보 추출
            owner = "user"  # 기본값
            target_date = date.today()  # 기본값: 오늘
            
            if context:
                owner = context.get("owner", owner)
                if "target_date" in context:
                    target_date = context["target_date"]
                elif "user_id" in context:
                    owner = str(context["user_id"])
            
            # DB 세션 생성
            db = SessionLocal()
            report_data = None
            report_type = None
            
            try:
                # 질문 분석하여 리포트 타입 결정
                query_lower = query.lower()
                
                # 일간 리포트
                if any(keyword in query_lower for keyword in ["일간", "오늘", "오늘의", "오늘 리포트", "daily"]):
                    report_data = DailyReportRepository.get_by_owner_and_date(db, owner, target_date)
                    report_type = "일간"
                
                # 주간 리포트
                elif any(keyword in query_lower for keyword in ["주간", "이번 주", "이번주", "weekly"]):
                    # 이번 주 시작일과 종료일 계산
                    days_since_monday = target_date.weekday()
                    week_start = target_date - timedelta(days=days_since_monday)
                    week_end = week_start + timedelta(days=6)
                    report_data = WeeklyReportRepository.get_by_owner_and_period(db, owner, week_start, week_end)
                    report_type = "주간"
                
                # 월간 리포트
                elif any(keyword in query_lower for keyword in ["월간", "이번 달", "이번달", "이번 월", "monthly"]):
                    # 이번 달 시작일과 종료일 계산
                    month_start = date(target_date.year, target_date.month, 1)
                    if target_date.month == 12:
                        month_end = date(target_date.year + 1, 1, 1) - timedelta(days=1)
                    else:
                        month_end = date(target_date.year, target_date.month + 1, 1) - timedelta(days=1)
                    report_data = MonthlyReportRepository.get_by_owner_and_period(db, owner, month_start, month_end)
                    report_type = "월간"
                
                # 실적 리포트
                elif any(keyword in query_lower for keyword in ["실적", "성과", "performance", "분기"]):
                    # 분기 계산
                    quarter = (target_date.month - 1) // 3 + 1
                    quarter_start_month = (quarter - 1) * 3 + 1
                    quarter_end_month = quarter * 3
                    quarter_start = date(target_date.year, quarter_start_month, 1)
                    if quarter_end_month == 12:
                        quarter_end = date(target_date.year + 1, 1, 1) - timedelta(days=1)
                    else:
                        quarter_end = date(target_date.year, quarter_end_month + 1, 1) - timedelta(days=1)
                    report_data = PerformanceReportRepository.get_by_owner_and_period(db, owner, quarter_start, quarter_end)
                    report_type = "실적"
                
                # 리포트 데이터가 있으면 분석
                if report_data:
                    # CanonicalReport로 변환
                    report_json = report_data.report_json
                    canonical_report = CanonicalReport(**report_json)
                    
                    # 리포트 데이터를 텍스트로 변환
                    report_summary = self._format_report_data(canonical_report, report_type)
                    
                    # LLM으로 분석
                    system_prompt = """당신은 업무 리포트와 데이터 분석을 전문으로 하는 AI 어시스턴트입니다.

역할:
- 제공된 리포트 데이터를 분석하여 인사이트를 도출합니다.
- 핵심 지표와 성과를 명확하게 정리합니다.
- 개선 방안과 액션 아이템을 제안합니다.
- 시각적으로 이해하기 쉬운 형식으로 정보를 구조화합니다.

응답 스타일:
- 핵심 지표와 수치를 명확히 제시합니다.
- 긍정적인 부분과 개선이 필요한 부분을 균형있게 다룹니다.
- 구체적이고 실행 가능한 개선 방안을 제시합니다.
- 전문적이면서도 이해하기 쉬운 언어를 사용합니다."""
                    
                    user_prompt = f"""다음 {report_type} 리포트 데이터를 분석해주세요:

{report_summary}

사용자 질문: {query}

위 데이터를 바탕으로 분석 결과를 제공해주세요."""
                    
                    response = await self.llm_client.acomplete(
                        system_prompt=system_prompt,
                        user_prompt=user_prompt
                    )
                    
                    return response
                else:
                    # 리포트 데이터가 없으면 안내 메시지
                    return f"{report_type or '리포트'} 데이터를 찾을 수 없습니다. 리포트가 생성되지 않았거나 다른 기간의 리포트를 요청해주세요."
                    
            finally:
                db.close()
            
        except Exception as e:
            return f"리포트 생성 중 오류가 발생했습니다: {str(e)}"
    
    def _format_report_data(self, report, report_type: str) -> str:
        """리포트 데이터를 텍스트 형식으로 변환"""
        result = f"=== {report_type} 리포트 ===\n\n"
        result += f"작성자: {report.owner}\n"
        result += f"기간: {report.period_start} ~ {report.period_end}\n\n"
        
        # Tasks
        if report.tasks:
            result += "📋 업무 목록:\n"
            for i, task in enumerate(report.tasks, 1):
                result += f"{i}. {task.title}\n"
                if task.description:
                    result += f"   - {task.description}\n"
                if task.time_start and task.time_end:
                    result += f"   - 시간: {task.time_start} ~ {task.time_end}\n"
                if task.note:
                    result += f"   - 비고: {task.note}\n"
            result += "\n"
        
        # KPIs
        if report.kpis:
            result += "📊 핵심 지표:\n"
            for kpi in report.kpis:
                result += f"- {kpi.kpi_name}: {kpi.value} {kpi.unit or ''}\n"
                if kpi.note:
                    result += f"  (비고: {kpi.note})\n"
            result += "\n"
        
        # Issues
        if report.issues:
            result += "⚠️ 이슈/미종결 업무:\n"
            for issue in report.issues:
                result += f"- {issue}\n"
            result += "\n"
        
        # Plans
        if report.plans:
            result += "📅 계획:\n"
            for plan in report.plans:
                result += f"- {plan}\n"
            result += "\n"
        
        # Metadata
        if report.metadata:
            result += "📝 추가 정보:\n"
            for key, value in report.metadata.items():
                if value:
                    result += f"- {key}: {value}\n"
        
        return result
    
    def get_capabilities(self) -> list:
        """에이전트 기능 목록"""
        return [
            "일간/주간/월간 리포트 생성",
            "실적 분석",
            "성과 평가",
            "데이터 시각화",
            "개선 방안 제시",
        ]

