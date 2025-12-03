"""
Supervisor Agent

중앙 Supervisor Agent
사용자 질문을 분석하여 적절한 전문 에이전트를 선택하고 조율합니다.
"""

import time
import os
from typing import Dict, Any, Optional, List
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langgraph.prebuilt import create_react_agent

from .config import multi_agent_config
from .tools.agent_tools import get_all_agent_tools
from .schemas import MultiAgentRequest, MultiAgentResponse

# SuperViser Agent 클래스
# Tool Calling 패턴으로 에이전트 호출
class SupervisorAgent:
    
    # 초기화 함수
    def __init__(self):

        # LangSmith 추적 설정
        if multi_agent_config.LANGSMITH_TRACING:
            os.environ["LANGCHAIN_TRACING_V2"] = "true"
            os.environ["LANGCHAIN_API_KEY"] = multi_agent_config.LANGSMITH_API_KEY or ""
            os.environ["LANGCHAIN_PROJECT"] = multi_agent_config.LANGSMITH_PROJECT
        
        # LLM 초기화
        self.llm = ChatOpenAI(
            model=multi_agent_config.SUPERVISOR_MODEL,
            temperature=multi_agent_config.SUPERVISOR_TEMPERATURE,
            max_tokens=multi_agent_config.MAX_TOKENS,
            api_key=multi_agent_config.OPENAI_API_KEY
        )
        
        # 전문 에이전트 도구 가져오기
        self.tools = get_all_agent_tools()
        
        # System message 생성
        self.system_message = self._create_system_message()
        
        # LangGraph Agent 생성 (LangChain 1.1.0 + LangGraph 1.0.4 호환)
        self.agent_executor = create_react_agent(
            model=self.llm,
            tools=self.tools,
            state_modifier=self.system_message
        )
    
    # System message 생성 함수(45줄에 rtn)
    # 역할, 에이전트 목록, 키워드, 예시, 규칙 등등 제공
    def _create_system_message(self) -> str:

        system_message = """당신은 사용자의 질문을 분석하여 적절한 전문 에이전트에게 작업을 위임하는 Supervisor AI입니다.

**당신의 역할:**
1. 사용자의 질문을 이해하고 의도를 파악합니다.
2. 질문에 포함된 키워드와 맥락을 분석합니다.
3. 질문에 가장 적합한 전문 에이전트를 선택합니다.
4. 선택한 에이전트에게 작업을 위임하고 결과를 받습니다.
5. 최종 결과를 사용자에게 명확하고 친절하게 전달합니다.

**사용 가능한 전문 에이전트:**

1. **chatbot_tool**: 일반 대화, 인사, 잡담
   - 키워드: 안녕, 하이, 헬로, 반가워, 고마워, 감사, 날씨, 오늘, 내일, 어제, 시간, 몇 시, 기분, 좋아, 싫어, 행복, 잘 지내, 어떻게 지내, 뭐해, 뭐하니, 놀자, 재미, 즐거워, 좋은 하루, 좋은 밤, 잘 자, 안녕히, 뭐야, 그게 뭐야, 재밌어, 웃겨, 하하, 헤헤
   - 예시: "안녕하세요!", "오늘 날씨 좋네요", "고마워요"

2. **rag_tool**: 회사 문서, 규정, 정책 검색
   - 키워드: 연차, 휴가, 근로시간, 유연근무, 근무지, 변경, 급여, 성과급, 연말정산, 명세서, 복지, 건강검진, 보험, 선택적, 제휴, 교육, 승진, 인사평가, 포상, 의무교육, 법인카드, 규정, 정보보호, 개인정보, 가치평가, 금융소비자, 프로세스, 신청, 지원, 기준, 정책, 규칙, 가이드, 매뉴얼, 절차, 방법, 회사, 사내, 내부, 문서, 자료, 찾아, 검색, 알려줘, 말해줘, 확인, 조회, 보여줘, 설명
   - 예시: "연차 규정이 어떻게 돼?", "복지 정책 알려줘", "급여 명세서는 어디서 확인해?"

3. **brainstorming_tool**: 창의적 아이디어, 브레인스토밍
   - 키워드: 아이디어, 브레인스토밍, 창의적, 혁신, 발상, 생각, 방법, 전략, 기획, 제안, 개선, 새로운, 참신한, 독창적, 문제 해결, 해결책, 대안, 접근법, 마케팅, 프로젝트, 기법, 도출, 막막해, 떠오르지 않아, 머리가 굳었어, 영감, 기발한, 상상력, 발상의 전환, 필요해, 없을까, 해줘, 하자, 시작
   - 예시: "새로운 마케팅 아이디어를 내고 싶어", "문제 해결 방법 제안해줘", "창의적 사고 기법 알려줘", "좋은 생각이 안 떠올라", "아이디어 좀 줘", "기획이 막혔어", "뭔가 새로운 게 필요해", "아이디어가 필요해", "좋은 기획 없을까?", "새로운 아이디어를 만들고 싶어", "브레인스토밍 같은 걸 하고 싶은데", "브레인스토밍 해줘", "브레인스토밍 하자", "브레인스토밍 시작"

4. **planner_tool**: 일정 관리, 계획 수립
   - 키워드: 일정, 계획, 스케줄, 할 일, 업무, 작업, 정리, 관리, 시간, 오늘, 내일, 이번 주, 다음 주, 우선순위, 마감, 데드라인, 목표, 생산성, 효율, 타임라인, 일과
   - 예시: "오늘 할 일을 정리해줘", "일정 관리 방법 알려줘", "업무 우선순위 정하는 법"

5. **report_tool**: 리포트 생성, 실적 분석
   - 키워드: 리포트, 보고서, 실적, 성과, 분석, 통계, 데이터, 결과, 평가, 지표, KPI, 매출, 수치, 추이, 트렌드, 요약, 정리, 일간, 주간, 월간, 분기, 연간
   - 예시: "이번 주 실적을 분석해줘", "월간 리포트 작성해줘", "성과 평가 자료 만들어줘"

6. **therapy_tool**: 심리 상담, 정신 건강 지원
   - 키워드: 
     * 기본 감정: 힘들어, 상담, 짜증, 우울, 불안, 스트레스, 고민, 걱정, 슬프, 외로, 화나, 답답, 심리, 아들러
     * 부정적 감정: 절망, 포기, 무기력, 자책, 후회, 미안, 두려움, 공포, 불안감, 초조, 분노, 화남, 짜증나, 성가심, 불쾌, 슬픔, 비참, 절망적, 우울함, 침체, 외로움, 고독, 쓸쓸, 허전, 외톨이, 답답함, 막막, 난처, 곤란, 피곤, 지침, 무력감, 의욕없음, 수치, 수치심, 열받, 열받아, 화낼, 미치, 미쳐, 억울, 억울해, 멍하
     * 관계/대인관계: 갈등, 싸움, 다툼, 오해, 불화, 이별, 헤어짐, 이혼, 결별, 배신, 상처, 아픔, 서운, 소외, 왕따, 따돌림, 무시, 배제, 멀리하는, 따로 노는, 겉돌고, 혼자, 남겨지는, 불편
     * 직장/학업 스트레스: 직장, 업무, 과로, 번아웃, 시험, 공부, 학업, 성적, 압박, 실패, 좌절, 낙담, 실망, 상사, 팀장, 부장, 동기, 동료, 욕, 쌍욕, 폭언, 인격모독, 소리지르, 화풀이, 그만두, 퇴사, 사직, 적응, 분위기, 문화, 익숙, 부담, 어울리, 소통, 환경, 출근, 노력, 긴장, 낯설, 대화, 규칙, 절차, 복잡, 시스템, 효율, 회의, 의견, 표현, 출퇴근, 루틴, 리듬, 변화, 부담감, 프로젝트
     * 자기존중감: 자존감, 자신감, 열등감, 비교, 열등, 자기비하, 자기혐오, 부족함, 능력부족, 무능력, 쓸모없음
     * 트라우마: 트라우마, 상처, 과거, 기억, 악몽, 플래시백, ptsd
     * 신체 반응: 심장, 떨려, 떨림, 손떨림, 잠이 안 와, 불면, 수면장애, 수면
     * 감정 조절: 감정조절, 감정 조절, 퍼붓, 퍼붓다, 대처, 현명, 해결
     * 자살 사고: 죽고 싶, 자살, 자살사고
     * 상담/치료: 심리상담, 정신건강, 치료, 치유, 회복, 마음, 감정, 기분, 상태, 조언, 도움, 지원, 위로, 격려, 공감
     * 일상적 표현: 안좋아, 안좋음, 나쁨, 최악, 끔찍, 괴로워, 괴롭, 아파, 아픔, 고통, 힘듦, 어려움, 난감, 막막함
     * 영어: counseling, therapy, help, depressed, anxious, sad, angry, lonely, frustrated, stressed, worried, scared, afraid, fear, panic, hopeless, helpless, worthless, empty, guilt, shame, regret, remorse, jealous, envy, tired, exhausted, burnout, overwhelmed, confused, lost, psychology, mental health, counselor, therapist, support, comfort, encouragement, empathy, trauma, alcoholic, drunk, abusive, violence, trust, mistrust, trustworthy, parent, family, perfect, perfectionism, insecure, instability, inflexible, overbearing, control
   - 예시: "스트레스가 많아서 힘들어", "우울한 기분이 들어", "대인관계 문제로 고민이야", "번아웃이 와", "상사가 무서워", "자존감이 낮아", "트라우마가 있어"

**에이전트 선택 가이드:**
1. **"브레인스토밍"이라는 단어가 명시적으로 포함되면 무조건 brainstorming_tool을 선택하세요.**
2. 질문에 포함된 키워드를 먼저 확인하세요.
3. 여러 에이전트의 키워드가 겹치면, 질문의 주요 목적을 파악하세요.
4. 감정적 표현(힘들어, 우울해 등)이 있으면 therapy_tool을 우선 고려하세요.
5. 회사/업무 관련 정보 요청은 rag_tool을 사용하세요.
6. 일반적인 인사나 잡담은 chatbot_tool을 사용하세요.

**중요한 규칙:**
- 질문의 핵심 의도를 정확히 파악하세요.
- 가장 적합한 에이전트 하나를 선택하세요.
- 에이전트의 응답을 그대로 사용자에게 전달하세요.
- 에이전트가 이미 충분한 답변을 제공했다면 추가 설명 없이 그대로 전달하세요.
- 한국어로 응답하세요.
"""
        
        return system_message
    
    # 사용자 질문을 처리하는 비동기 함수
    async def process(self, request: MultiAgentRequest) -> MultiAgentResponse:

        start_time = time.time()
        
        try:
            # LangGraph Agent 실행
            result = await self.agent_executor.ainvoke({
                "messages": [HumanMessage(content=request.query)]
            })
            
            # 결과 추출 (LangGraph는 messages 형태로 반환)
            messages = result.get("messages", [])
            answer = "응답을 생성할 수 없습니다."
            agent_used = "supervisor"
            
            # 마지막 AI 메시지에서 답변 추출
            for msg in reversed(messages):
                if hasattr(msg, 'content') and msg.content:
                    answer = msg.content
                    break
            
            # 사용된 도구 추출
            intermediate_steps = []
            for msg in messages:
                if hasattr(msg, 'tool_calls') and msg.tool_calls:
                    for tool_call in msg.tool_calls:
                        tool_name = tool_call.get('name', 'unknown')
                        agent_used = tool_name.replace('_tool', '')
                        intermediate_steps.append({
                            "agent": agent_used,
                            "action": "process_query",
                            "result": "success"
                        })
            
            # 처리 시간 계산
            processing_time = time.time() - start_time
            
            # 응답 생성
            response = MultiAgentResponse(
                query=request.query,
                answer=answer,
                agent_used=agent_used,
                intermediate_steps=intermediate_steps if intermediate_steps else [
                    {
                        "agent": agent_used,
                        "action": "process_query",
                        "result": "success"
                    }
                ],
                processing_time=processing_time,
                session_id=request.session_id
            )
            
            return response
            
        # 오류 처리
        except Exception as e:
            
            processing_time = time.time() - start_time
            error_message = f"질문 처리 중 오류가 발생했습니다"
            
            return MultiAgentResponse(
                query=request.query,
                answer=error_message,
                agent_used="error",
                intermediate_steps=[
                    {
                        "agent": "supervisor",
                        "action": "error",
                        "error": str(e)
                    }
                ],
                processing_time=processing_time,
                session_id=request.session_id
            )
    
    # 사용 가능한 에이전트 목록 반환
    def get_available_agents(self) -> List[Dict[str, Any]]:

        agents = []
        
        # 에이전트 목록에 이름이랑 설명 추가
        for tool in self.tools:
            agents.append({
                "name": tool.name,
                "description": tool.description,
            })
        
        return agents

