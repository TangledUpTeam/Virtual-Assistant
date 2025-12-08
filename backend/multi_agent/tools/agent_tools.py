"""
Agent Tools

각 전문 에이전트를 LangChain Tool로 래핑합니다.
Supervisor Agent가 이 도구들을 호출하여 작업을 수행합니다.

LangChain 1.1.0 호환
"""

from typing import List, Dict, Any, Optional
from langchain_core.tools import tool, Tool

from ..context import get_session_id, get_user_context
from app.domain.chatbot.memory_manager import MemoryManager

# 전역 에이전트 인스턴스 (Lazy loading)
_chatbot_agent = None
_rag_agent = None
_brainstorming_agent = None
_planner_agent = None
_report_agent = None
_therapy_agent = None
_notion_agent = None
_email_agent = None

# MemoryManager 초기화
memory_manager = MemoryManager()

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

# 심리 상담 에이전트 호출
def get_therapy_agent():
    global _therapy_agent
    if _therapy_agent is None:
        from backend.multi_agent.agents.therapy_agent import TherapyAgent
        _therapy_agent = TherapyAgent()
    return _therapy_agent

# Notion 에이전트 호출
def get_notion_agent():
    global _notion_agent
    if _notion_agent is None:
        from backend.multi_agent.agents.notion_agent import NotionAgent
        _notion_agent = NotionAgent()
    return _notion_agent

# Email 에이전트 호출
def get_email_agent():
    global _email_agent
    if _email_agent is None:
        from backend.multi_agent.agents.email_agent import EmailAgent
        _email_agent = EmailAgent()
    return _email_agent

# Insurance RAG 에이전트 호출
_insurance_agent = None
def get_insurance_agent():
    global _insurance_agent
    if _insurance_agent is None:
        from multi_agent.agents.insurance_rag_agent import InsuranceRAGAgent
        _insurance_agent = InsuranceRAGAgent()
    return _insurance_agent

def _parse_history_markdown(markdown: str) -> List[Dict[str, Any]]:
    """MemoryManager의 마크다운 히스토리를 파싱하여 리스트로 변환"""
    messages = []
    if not markdown:
        return messages
        
    # 구분자로 분리
    chunks = markdown.split("\n---\n")
    
    for chunk in chunks:
        chunk = chunk.strip()
        if not chunk:
            continue
            
        role = "unknown"
        if "## 👤 사용자" in chunk:
            role = "user"
        elif "## 🤖 AI 비서" in chunk:
            role = "assistant"
        else:
            continue # 헤더나 기타 내용
            
        # 내용 추출 (시간 다음 줄부터)
        lines = chunk.split('\n')
        content_start = -1
        for i, line in enumerate(lines):
            if line.startswith("**시간:**"):
                content_start = i + 2 # 빈 줄 건너뛰기
                break
        
        if content_start != -1 and content_start < len(lines):
            content = "\n".join(lines[content_start:]).strip()
            if content:
                messages.append({"role": role, "content": content})
            
    return messages

def get_current_context() -> Dict[str, Any]:
    """현재 컨텍스트(세션, 사용자, 대화 기록)를 반환"""
    session_id = get_session_id()
    user_context = get_user_context()
    
    context = user_context.copy()
    if session_id:
        context["session_id"] = session_id
        
        # 대화 기록 가져오기
        try:
            history_md = memory_manager.get_all_messages(session_id)
            history = _parse_history_markdown(history_md)
            context["conversation_history"] = history
        except Exception as e:
            print(f"[ERROR] History fetch failed: {e}")
            context["conversation_history"] = []
            
    return context

# Tool 정의

# 챗봇 툴 정의
@tool
async def chatbot_tool(query: str) -> str:
    """일반적인 대화와 질문에 답변합니다. 인사말, 잡담, 일상적인 질문을 처리합니다."""
    agent = get_chatbot_agent()
    context = get_current_context()
    return await agent.process(query, context=context)

# 회사 문서, 규정 및 정책을 검색하여 답변(HR)
@tool
async def rag_tool(query: str) -> str:
    """회사 문서, 규정, 정책을 검색하여 답변합니다. HR 규정, 복지 정책, 연차/휴가 규정 등을 처리합니다."""
    agent = get_rag_agent()
    context = get_current_context()
    return await agent.process(query, context=context)

# 브레인스토밍 기법 제안 -> 아이디어 도출
@tool
async def brainstorming_tool(query: str) -> str:
    """창의적인 아이디어와 브레인스토밍 기법을 제안합니다. 새로운 아이디어, 문제 해결 방법을 제공합니다."""
    agent = get_brainstorming_agent()
    context = get_current_context()
    return await agent.process(query, context=context)

# 일정 관리와 계획 수립을 도와줌
@tool
async def planner_tool(query: str) -> str:
    """일정 관리와 계획 수립을 도와줍니다. 오늘의 할 일, 업무 일정 관리, 시간 관리 조언을 제공합니다."""
    agent = get_planner_agent()
    context = get_current_context()
    return await agent.process(query, context=context)

# 업무 리포트와 실적 분석을 생성
@tool
async def report_tool(query: str) -> str:
    """업무 리포트와 실적 분석을 생성합니다. 일간/주간/월간 리포트, 성과 평가 자료를 제공합니다."""
    agent = get_report_agent()
    context = get_current_context()
    return await agent.process(query, context=context)

# 심리 상담 제공
@tool
async def therapy_tool(query: str) -> str:
    """심리 상담과 정신 건강 지원을 제공합니다. 감정적 지원, 스트레스 관리, 대인관계 조언을 제공합니다."""
    agent = get_therapy_agent()
    context = get_current_context()
    return await agent.process(query, context=context)

# Notion 페이지 관리
@tool
async def notion_tool(query: str) -> str:
    """Notion 페이지를 관리합니다. 페이지 검색, 생성, 대화 내용 저장 등을 처리합니다."""
    agent = get_notion_agent()
    context = get_current_context()
    
    # user_id 추출 (context에서)
    user_id = context.get("user_id", "default_user")
    
    result = await agent.process(query, user_id, context)
    
    # 결과가 dict 형태면 answer 추출
    if isinstance(result, dict):
        return result.get("answer", str(result))
    return str(result)

# 이메일 전송 및 검색
@tool
async def email_tool(query: str) -> str:
    """이메일을 전송하거나 검색합니다. 메일 보내기, 첨부파일 전송, 안 읽은 메일 확인 등을 처리합니다."""
    agent = get_email_agent()
    context = get_current_context()
    
    # user_id 추출 (context에서)
    user_id = context.get("user_id", "default_user")
    
    result = await agent.process(query, context)
    
    # 결과가 dict 형태면 answer 추출
    if isinstance(result, dict):
        return result.get("answer", str(result))
    return str(result)

# 보험/의료급여 문서 기반 정보 제공
@tool
async def insurance_tool(query: str) -> str:
    """
    보험/의료급여 법규 및 정책 문서 기반 정보 제공.
    
    사용 대상:
    - 보험 상품, 의료급여 규정, 청구 절차, 보장 범위, 환수 기준 등의 법적/정책 정보 필요
    - 민법, 의료급여법, 형법, 도로교통법 등 법령 관련 질문
    - 상해요인 판단, 부당이득, 손해배상, 도급인 책임 등의 법적 판단 필요
    - 판례, 선례, 사례 기반의 구체적 기준 확인 필요
    
    예시 질문:
    - "민법 741조와 의료급여법 23조의 부당이득 개념의 차이는?"
    - "의료급여비용 환수 기준은?"
    - "자살시도자 의료급여 적용 기준은?"
    - "도급인의 책임이 인정되는 경우는?"
    - "부도/파산 시 결손처분 대상이 되는 조건은?"
    
    참고: 보험 상품 설명, 일반 상식, 감정 표현, 계획 수립 등은 다른 도구를 사용합니다.
    """
    agent = get_insurance_agent()
    context = get_current_context()
    return await agent.process(query, context=context)


# 모든 에이전트를 도구로 해서 도구 리스트 리턴
def get_all_agent_tools() -> List[Tool]:
    return [
        chatbot_tool,
        rag_tool,
        brainstorming_tool,
        planner_tool,
        report_tool,
        therapy_tool,
        notion_tool,
        email_tool,
        insurance_tool,
    ]