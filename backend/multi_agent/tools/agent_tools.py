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

# 일정 관리 및 계획 수립 에이전트 호출
def get_planner_agent():
    global _planner_agent
    if _planner_agent is None:
        from backend.multi_agent.agents.planner_agent import PlannerAgent
        _planner_agent = PlannerAgent()
    return _planner_agent

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
    agent = get_chatbot_agent()
    return await agent.process(query)

# 회사 문서, 규정 및 정책을 검색하여 답변(HR)
@tool
async def rag_tool(query: str) -> str:
    agent = get_rag_agent()
    return await agent.process(query)

# 브레인스토밍 기법 제안 -> 아이디어 도출
@tool
async def brainstorming_tool(query: str) -> str:
    agent = get_brainstorming_agent()
    return await agent.process(query)

# 일정 관리와 계획 수립을 도와줌
@tool
async def planner_tool(query: str) -> str:
    agent = get_planner_agent()
    return await agent.process(query)

# 업무 리포트와 실적 분석을 생성
@tool
async def report_tool(query: str) -> str:
    agent = get_report_agent()
    return await agent.process(query)

# 심리 상담 제공
@tool
async def therapy_tool(query: str) -> str:
    agent = get_therapy_agent()
    return await agent.process(query)

# 모든 에이전트를 도구로 해서 도구 리스트 리턴
def get_all_agent_tools() -> List[Tool]:
    return [
        chatbot_tool,
        rag_tool,
        brainstorming_tool,
        planner_tool,
        report_tool,
        therapy_tool,
    ]