"""
Report Main Router Agent

사용자 요청을 분석하여 적절한 보고서 전문 에이전트에게 라우팅
- Intent Classification (Rule + LLM)
- Context 주입 및 전달
- 세부 비즈니스 로직은 전문 에이전트에게 위임
"""

from typing import Any, Dict, Optional
from datetime import date
import re

from multi_agent.agents.report_base import ReportBaseAgent
from multi_agent.agents.report_tools import get_planning_agent, get_report_generation_agent, get_report_rag_agent
from app.llm.client import LLMClient


class ReportMainRouterAgent(ReportBaseAgent):
    """보고서 메인 라우터 에이전트 - Intent Classification 및 라우팅"""
    
    # Intent 분류
    INTENT_PLANNING = "planning"
    INTENT_REPORT = "report"
    INTENT_RAG = "rag"
    INTENT_UNKNOWN = "unknown"
    
    def __init__(self, llm_client: Optional[LLMClient] = None):
        """초기화"""
        super().__init__(
            name="ReportMainRouterAgent",
            description="사용자 요청을 분석하여 적절한 보고서 전문 에이전트에게 라우팅하는 메인 에이전트입니다.",
            llm_client=llm_client
        )
        
        # 전문 에이전트들 (Lazy loading)
        self._planning_agent = None
        self._report_agent = None
        self._rag_agent = None
    
    @property
    def planning_agent(self):
        """PlanningAgent 인스턴스"""
        if self._planning_agent is None:
            self._planning_agent = get_planning_agent()
        return self._planning_agent
    
    @property
    def report_agent(self):
        """ReportGenerationAgent 인스턴스"""
        if self._report_agent is None:
            self._report_agent = get_report_generation_agent()
        return self._report_agent
    
    @property
    def rag_agent(self):
        """ReportRAGAgent 인스턴스"""
        if self._rag_agent is None:
            self._rag_agent = get_report_rag_agent()
        return self._rag_agent
    
    def _classify_intent_by_rule(self, query: str) -> Optional[str]:
        """
        룰 기반 Intent Classification (빠른 판단)
        
        Args:
            query: 사용자 질문
            
        Returns:
            Intent 또는 None (룰로 판단 불가)
        """
        query_lower = query.lower()
        
        # Planning 키워드
        planning_keywords = [
            "오늘", "업무", "플래닝", "계획", "할일", "추천", "일정",
            "today", "plan", "planning", "schedule", "todo"
        ]
        
        # Report 키워드
        report_keywords = [
            "보고서", "작성", "생성", "일일", "주간", "월간",
            "report", "daily", "weekly", "monthly", "generate"
        ]
        
        # RAG 키워드 (검색, 과거 업무 조회)
        rag_keywords = [
            "언제", "찾아", "검색", "조회", "했었", "미종결", "고객",
            "지난주", "저번주", "이번주", "지난달", "저번달", "이번달", "지난해", "저번해",
            "when", "search", "find", "lookup", "unresolved", "customer",
            "last week", "last month", "last year"
        ]
        
        # 키워드 매칭
        if any(kw in query_lower for kw in planning_keywords):
            # "오늘" + "추천" 또는 "업무" + "계획" 등
            if any(kw in query_lower for kw in ["추천", "계획", "플래닝", "할일"]):
                return self.INTENT_PLANNING
        
        if any(kw in query_lower for kw in report_keywords):
            return self.INTENT_REPORT
        
        if any(kw in query_lower for kw in rag_keywords):
            return self.INTENT_RAG
        
        # 룰로 판단 불가
        return None
    
    async def _classify_intent_by_llm(self, query: str) -> str:
        """
        LLM 기반 Intent Classification (룰 실패 시)
        
        Args:
            query: 사용자 질문
            
        Returns:
            Intent (planning|report|rag|unknown)
        """
        system_prompt = """당신은 사용자의 요청을 분석하여 적절한 에이전트로 라우팅하는 전문가입니다.

다음 3가지 에이전트 중 하나를 선택하세요:

1. **planning**: 업무 플래닝, 오늘 할 일 추천, 일정 관리
   - 예: "오늘 업무 추천해줘", "오늘 뭐 해야 할까?"
   
2. **report**: 보고서 작성 및 생성 (일일/주간/월간)
   - 예: "일일 보고서 작성", "주간 보고서 생성", "월간 보고서 만들어줘"
   
3. **rag**: 과거 업무 내역 검색 및 조회
   - 예: "나 최근에 연금 상담 언제 했었지?", "미종결 업무 뭐 있어?", "고객 상담 기록 찾아줘"

반드시 다음 JSON 형식으로만 응답:
{
  "intent": "planning|report|rag|unknown",
  "confidence": 0.0 ~ 1.0,
  "reason": "판단 이유"
}
"""
        
        user_prompt = f"사용자 요청: {query}"
        
        try:
            result = await self.llm.acomplete_json(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.3,
                max_tokens=200
            )
            
            intent = result.get("intent", self.INTENT_UNKNOWN)
            confidence = result.get("confidence", 0.0)
            reason = result.get("reason", "")
            
            print(f"[INFO] LLM Intent Classification: {intent} (confidence={confidence:.2f}, reason={reason})")
            
            return intent
            
        except Exception as e:
            print(f"[ERROR] LLM Intent Classification 실패: {e}")
            return self.INTENT_UNKNOWN
    
    async def classify_intent(self, query: str) -> str:
        """
        Intent Classification (Rule + LLM Hybrid)
        
        Args:
            query: 사용자 질문
            
        Returns:
            Intent (planning|report|rag|unknown)
        """
        # 1단계: 룰 기반 분류 (빠름)
        intent = self._classify_intent_by_rule(query)
        
        if intent:
            print(f"[INFO] Rule-based Intent: {intent}")
            return intent
        
        # 2단계: LLM 기반 분류 (정확함)
        intent = await self._classify_intent_by_llm(query)
        
        return intent
    
    async def process(self, query: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        사용자 요청 처리 및 라우팅
        
        Args:
            query: 사용자 질문
            context: {"owner": str, "target_date": date, ...} 포함
            
        Returns:
            처리 결과 문자열
        """
        # Intent Classification
        intent = await self.classify_intent(query)
        
        print(f"[INFO] ReportMainRouterAgent - Intent: {intent}, Query: {query}")
        
        # 전문 에이전트에게 라우팅
        try:
            if intent == self.INTENT_PLANNING:
                return await self.planning_agent.process(query, context)
            
            elif intent == self.INTENT_REPORT:
                return await self.report_agent.process(query, context)
            
            elif intent == self.INTENT_RAG:
                return await self.rag_agent.process(query, context)
            
            else:
                return "죄송합니다. 요청을 이해하지 못했습니다. 업무 플래닝, 보고서 작성, 또는 과거 업무 검색 중 어떤 것을 도와드릴까요?"
        
        except Exception as e:
            print(f"[ERROR] ReportMainRouterAgent 처리 실패: {e}")
            import traceback
            traceback.print_exc()
            return f"요청 처리 중 오류가 발생했습니다: {str(e)}"
    
    async def route_to_agent(
        self,
        query: str,
        owner: str,
        target_date: Optional[date] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        API 엔드포인트용 라우팅 (구조화된 응답)
        
        Args:
            query: 사용자 질문
            owner: 작성자
            target_date: 대상 날짜
            **kwargs: 추가 컨텍스트
            
        Returns:
            {
                "intent": str,
                "agent": str,
                "response": str,
                "context": dict
            }
        """
        # Intent 분류
        intent = await self.classify_intent(query)
        
        # 컨텍스트 구성
        context = {
            "owner": owner,
            "target_date": target_date or date.today(),
            **kwargs
        }
        
        # 처리
        response = await self.process(query, context)
        
        return {
            "intent": intent,
            "agent": intent,  # intent와 agent 이름이 동일
            "response": response,
            "context": context
        }

