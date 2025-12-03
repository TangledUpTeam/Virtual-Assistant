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
_report_agent = None
_therapy_agent = None

# 챗봇 에이전트 호출
def get_chatbot_agent():
    global _chatbot_agent
    if _chatbot_agent is None:
        from backend.multi_agent.agents.chatbot_agent import ChatbotAgent
        _chatbot_agent = ChatbotAgent()
    return _chatbot_agent

# 회사 문서/규정 검색 에이전트 호출
def get_rag_agent():
    global _rag_agent
    if _rag_agent is None:
        from backend.multi_agent.agents.rag_agent import RAGAgent
        _rag_agent = RAGAgent()
    return _rag_agent

# 브레인스토밍 에이전트 호출
def get_brainstorming_agent():
    global _brainstorming_agent
    if _brainstorming_agent is None:
        from backend.multi_agent.agents.brainstorming_agent import BrainstormingAgent
        _brainstorming_agent = BrainstormingAgent()
    return _brainstorming_agent


# 업무 리포트 생성 및 실적 분석 에이전트 호출
def get_report_agent():
    global _report_agent
    if _report_agent is None:
        from backend.multi_agent.agents.report_agent import ReportAgent
        _report_agent = ReportAgent()
    return _report_agent

# 심리상담 에이전트 호출
def get_therapy_agent():
    global _therapy_agent
    if _therapy_agent is None:
        from backend.multi_agent.agents.therapy_agent import TherapyAgent
        _therapy_agent = TherapyAgent()
    return _therapy_agent


# Tool 정의

# 챗봇 툴 정의
# 일반적인 대화와 질문에 답변
@tool
async def chatbot_tool(query: str) -> str:
    """일반적인 대화와 질문에 답변합니다. 인사말, 잡담, 일상적인 질문을 처리합니다."""
    agent = get_chatbot_agent()
    return await agent.process(query)

# 회사 문서, 규정 및 정책을 검색하여 답변(HR)
@tool
async def rag_tool(query: str) -> str:
    """회사 문서, 규정, 정책을 검색하여 답변합니다. HR 규정, 복지 정책, 연차/휴가 규정 등을 처리합니다."""
    agent = get_rag_agent()
    return await agent.process(query)

# 브레인스토밍 기법 제안 -> 아이디어 도출
@tool
async def brainstorming_tool(query: str) -> str:
    """창의적인 아이디어와 브레인스토밍 기법을 제안합니다. 새로운 아이디어, 문제 해결 방법을 제공합니다."""
    agent = get_brainstorming_agent()
    return await agent.process(query)


# 업무 플래닝, 보고서 작성, 보고서 검색/대화를 수행
@tool
async def report_tool(query: str) -> str:
    """
    업무 플래닝, 보고서 작성, 보고서 검색을 수행합니다.
    - 금일 추천 업무 및 업무 플래닝
    - 일일/주간/월간 보고서 작성 및 HTML 생성
    - 과거 보고서 검색 및 실적 조회 (RAG 기반 대화)
    """
    agent = get_report_agent()
    return await agent.process(query)

# 심리 상담 제공
@tool
async def therapy_tool(query: str) -> str:
    """심리 상담과 정신 건강 지원을 제공합니다. 감정적 지원, 스트레스 관리, 대인관계 조언을 제공합니다."""
    agent = get_therapy_agent()
    return await agent.process(query)

# 모든 에이전트를 도구로 해서 도구 리스트 리턴
def get_all_agent_tools() -> List[Tool]:
    return [
        chatbot_tool,
        rag_tool,
        brainstorming_tool,
        report_tool,
        therapy_tool,
    ]