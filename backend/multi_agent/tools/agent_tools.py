"""
Agent Tools

각 전문 에이전트를 LangChain Tool로 래핑합니다.
Supervisor Agent가 이 도구들을 호출하여 작업을 수행합니다.

LangChain 1.1.0 호환
"""

from typing import List
from langchain_core.tools import tool, Tool

# 전역 에이전트 인스턴스 (Lazy loading)
_chatbot_agent = None
_rag_agent = None
_brainstorming_agent = None
_planner_agent = None
_report_agent = None
_therapy_agent = None


def get_chatbot_agent():
    """ChatbotAgent 싱글톤"""
    global _chatbot_agent
    if _chatbot_agent is None:
        from backend.multi_agent.agents.chatbot_agent import ChatbotAgent
        _chatbot_agent = ChatbotAgent()
    return _chatbot_agent


def get_rag_agent():
    """RAGAgent 싱글톤"""
    global _rag_agent
    if _rag_agent is None:
        from backend.multi_agent.agents.rag_agent import RAGAgent
        _rag_agent = RAGAgent()
    return _rag_agent


def get_brainstorming_agent():
    """BrainstormingAgent 싱글톤"""
    global _brainstorming_agent
    if _brainstorming_agent is None:
        from backend.multi_agent.agents.brainstorming_agent import BrainstormingAgent
        _brainstorming_agent = BrainstormingAgent()
    return _brainstorming_agent


def get_planner_agent():
    """PlannerAgent 싱글톤"""
    global _planner_agent
    if _planner_agent is None:
        from backend.multi_agent.agents.planner_agent import PlannerAgent
        _planner_agent = PlannerAgent()
    return _planner_agent


def get_report_agent():
    """ReportAgent 싱글톤"""
    global _report_agent
    if _report_agent is None:
        from backend.multi_agent.agents.report_agent import ReportAgent
        _report_agent = ReportAgent()
    return _report_agent


def get_therapy_agent():
    """TherapyAgent 싱글톤"""
    global _therapy_agent
    if _therapy_agent is None:
        from backend.multi_agent.agents.therapy_agent import TherapyAgent
        _therapy_agent = TherapyAgent()
    return _therapy_agent


# Tool 정의

@tool
async def chatbot_tool(query: str) -> str:
    """
    일반적인 대화와 질문에 답변합니다.
    
    사용 시기:
    - 인사말이나 잡담
    - 일상적인 질문
    - 특정 도메인에 속하지 않는 일반적인 대화
    
    Args:
        query: 사용자의 질문이나 메시지
        
    Returns:
        str: 챗봇의 응답
    """
    agent = get_chatbot_agent()
    return await agent.process(query)


@tool
async def rag_tool(query: str) -> str:
    """
    회사 문서, 규정, 정책을 검색하여 답변합니다.
    
    사용 시기:
    - HR 규정, 복지 정책 문의
    - 연차, 휴가 규정 질문
    - 회사 내부 문서 검색
    - 사내 정책이나 절차 문의
    
    Args:
        query: 검색할 질문
        
    Returns:
        str: 문서 기반 답변
    """
    agent = get_rag_agent()
    return await agent.process(query)


@tool
async def brainstorming_tool(query: str) -> str:
    """
    창의적인 아이디어와 브레인스토밍 기법을 제안합니다.
    
    사용 시기:
    - 새로운 아이디어가 필요할 때
    - 문제 해결 방법을 찾을 때
    - 창의적 사고가 필요할 때
    - 브레인스토밍 방법을 알고 싶을 때
    
    Args:
        query: 아이디어나 해결책이 필요한 주제
        
    Returns:
        str: 브레인스토밍 제안
    """
    agent = get_brainstorming_agent()
    return await agent.process(query)


@tool
async def planner_tool(query: str) -> str:
    """
    일정 관리와 계획 수립을 도와줍니다.
    
    사용 시기:
    - 오늘의 할 일 정리
    - 업무 일정 관리
    - 시간 관리 조언
    - 계획 수립 도움
    
    Args:
        query: 일정이나 계획 관련 질문
        
    Returns:
        str: 일정 관리 응답
    """
    agent = get_planner_agent()
    return await agent.process(query)


@tool
async def report_tool(query: str) -> str:
    """
    업무 리포트와 실적 분석을 생성합니다.
    
    사용 시기:
    - 일간/주간/월간 리포트 요청
    - 실적 분석 필요
    - 성과 평가 자료
    - 통계 및 데이터 분석
    
    Args:
        query: 리포트 관련 질문
        
    Returns:
        str: 리포트 응답
    """
    agent = get_report_agent()
    return await agent.process(query)


@tool
async def therapy_tool(query: str) -> str:
    """
    심리 상담과 정신 건강 지원을 제공합니다.
    
    사용 시기:
    - 감정적 지원이 필요할 때
    - 스트레스나 걱정을 나누고 싶을 때
    - 대인관계 문제로 고민할 때
    - 심리적 조언이 필요할 때
    - 정신 건강 관리가 필요할 때
    
    Args:
        query: 상담 내용이나 고민
        
    Returns:
        str: 심리 상담 응답
    """
    agent = get_therapy_agent()
    return await agent.process(query)


def get_all_agent_tools() -> List[Tool]:
    """
    모든 에이전트 도구 목록 반환
    
    Returns:
        List[Tool]: Supervisor가 사용할 도구 목록
    """
    return [
        chatbot_tool,
        rag_tool,
        brainstorming_tool,
        planner_tool,
        report_tool,
        therapy_tool,
    ]

