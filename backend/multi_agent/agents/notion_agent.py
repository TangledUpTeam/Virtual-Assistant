"""
Notion Agent

Notion API를 사용하여 페이지 검색, 생성, 수정 등을 처리하는 에이전트
(Structured Output 및 Pydantic 적용 버전)
"""

import sys
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

from pydantic import BaseModel, Field

# Tools 경로 추가 (프로젝트 구조에 맞춰 경로 설정)
current_dir = Path(__file__).resolve().parent
tools_path = current_dir.parent.parent.parent / "tools"  # backend/tools

if str(tools_path) not in sys.path:
    sys.path.insert(0, str(tools_path))

# 프로젝트 내부 모듈 import
from tools import notion_tool
from .base_agent import BaseAgent
from app.core.config import settings  # 프로젝트 설정 사용

# LangChain imports
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser

# -------------------------------------------------------------------------
# 데이터 모델 정의 (Pydantic)
# -------------------------------------------------------------------------
class NotionAction(BaseModel):
    """Notion 작업 분석 결과"""
    intent: str = Field(description="작업 의도 (search, create, get, unknown)")
    title: Optional[str] = Field(default=None, description="생성할 페이지 제목. 없으면 문맥에 맞춰 생성.")
    content: Optional[str] = Field(default=None, description="생성할 페이지 내용. 대화 내용 저장이면 'CONTEXT_SUMMARY' 또는 'PREVIOUS_AI_RESPONSE' 등 특수 토큰 사용.")
    parent_page_name: Optional[str] = Field(default=None, description="페이지를 생성할 부모 페이지(폴더) 이름 (예: 개인, 회의록)")
    search_query: Optional[str] = Field(default=None, description="검색할 키워드")
    page_id: Optional[str] = Field(default=None, description="조회할 페이지 ID")


# -------------------------------------------------------------------------
# Notion Agent 클래스
# -------------------------------------------------------------------------
class NotionAgent(BaseAgent):
    """Notion 작업을 처리하는 전문 에이전트"""
    
    def __init__(self):
        super().__init__(
            name="notion_agent",
            description="Notion 페이지 검색, 생성, 수정 등을 처리합니다."
        )
        
        # 1. LLM 초기화
        # 정확한 의도 파악과 JSON 생성을 위해 gpt-4o 사용 권장
        self.llm = ChatOpenAI(
            model="gpt-4o",  
            temperature=0,   # 분석은 정확해야 하므로 0
            api_key=settings.OPENAI_API_KEY
        )
        
        # 2. 구조화된 출력을 위한 설정
        self.structured_llm = None
        try:
            # LangChain 최신 버전 지원 시 with_structured_output 사용
            self.structured_llm = self.llm.with_structured_output(NotionAction)
        except Exception as e:
            print(f"[WARNING] Structured Output 초기화 실패 (Fallback 사용): {e}")
            self.structured_llm = None

    async def process(self, query: str, user_id: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Notion 작업 처리 메인 파이프라인
        """
        try:
            # 1. LLM을 통한 의도 및 정보 분석
            action: NotionAction = await self._analyze_request(query, context)
            
            print(f"[DEBUG] Notion 분석 결과: {action}")
            
            if action.intent == "search":
                # 검색어가 없으면 쿼리 전체 사용 (불필요한 조사 제거 필요할 수 있음)
                search_q = action.search_query or query
                return await self._search_pages(search_q, user_id)
            
            elif action.intent == "create":
                return await self._create_page(action, user_id, context)
            
            elif action.intent == "get":
                # ID가 없으면 검색어(또는 쿼리)로 찾아서 조회
                target = action.page_id or action.search_query or query
                return await self._get_page_content(target, user_id)
            
            else:
                return {
                    "success": False,
                    "answer": "Notion 작업 의도를 명확히 파악할 수 없습니다. '페이지 검색', '페이지 생성' 등을 구체적으로 말씀해주세요.",
                    "agent_used": self.name
                }
        
        except Exception as e:
            return {
                "success": False,
                "answer": f"Notion 작업 중 오류가 발생했습니다: {str(e)}",
                "agent_used": self.name,
                "error": str(e)
            }
    
    async def _analyze_request(self, query: str, context: Optional[Dict[str, Any]] = None) -> NotionAction:
        """사용자 요청을 분석하여 구조화된 데이터로 반환"""
        
        # 대화 맥락이 있으면 프롬프트에 포함 (최근 3개만)
        context_str = ""
        if context and "conversation_history" in context:
            recent_history = context["conversation_history"][-3:]
            formatted_history = []
            for msg in recent_history:
                role = msg.get("role", "unknown")
                content = msg.get("content", "")
                formatted_history.append(f"{role}: {content}")
            context_str = "\n참고 대화 이력:\n" + "\n".join(formatted_history) + "\n"

        system_prompt = """당신은 Notion 전문 AI 비서입니다. 사용자의 요청을 분석하여 다음 정보를 추출하세요.

1. **intent (의도)**:
   - search: 페이지 검색, 찾기 ("~ 찾아줘", "~ 어디 있어?")
   - create: 페이지 생성, 저장, 기록, 정리, 추가 ("~ 적어줘", "~ 만들어줘", "~ 저장해줘", "~ 정리해줘")
   - get: 특정 페이지 내용 확인 ("~ 내용 보여줘")
   - unknown: 불명확함

2. **create 의도일 경우**:
   - title: 페이지 제목. 명시되지 않았으면 내용이나 문맥을 바탕으로 아주 짧고 명확하게 생성. (예: "안녕" -> "안녕")
   - content: 페이지 내용.
      * 사용자가 직접 말한 내용이면 그대로 추출. (예: "안녕이라고 적어" -> "안녕")
      * "저장해줘", "정리해줘", "올려줘", "방금 말한거" 처럼 **이전 대화나 답변을 지칭하는 경우** 반드시 `"PREVIOUS_AI_RESPONSE"` 라고 출력.
      * "대화 내용 전부 저장해줘" 같은 요청이면 `"CONTEXT_SUMMARY"` 라고 출력.
   - parent_page_name: 저장할 위치(부모 페이지) 이름. ("개인 페이지에", "회의록 폴더에" 등). 없으면 null.

3. **search 의도일 경우**:
   - search_query: 검색할 핵심 키워드

4. **get 의도일 경우**:
   - page_id: 페이지 ID가 있다면 추출 (없으면 null)

사용자의 요청을 꼼꼼히 분석하여 정확한 JSON 형식으로 반환하세요."""

        try:
            # Case A: Structured Output 사용 (권장)
            if self.structured_llm:
                prompt = ChatPromptTemplate.from_messages([
                    ("system", system_prompt),
                    ("user", f"{context_str}\n사용자 요청: {query}")
                ])
                chain = prompt | self.structured_llm
                return await chain.ainvoke({})
            
            # Case B: Fallback (일반 Pydantic Parser 사용)
            else:
                parser = PydanticOutputParser(pydantic_object=NotionAction)
                prompt = ChatPromptTemplate.from_messages([
                    ("system", system_prompt + "\n\n{format_instructions}"),
                    ("user", f"{context_str}\n사용자 요청: {query}")
                ])
                chain = prompt | self.llm | parser
                return await chain.ainvoke({"format_instructions": parser.get_format_instructions()})
                
        except Exception as e:
            print(f"[ERROR] 요청 분석 중 오류: {e}")
            # 오류 시 기본값 반환 (안전장치)
            return NotionAction(intent="unknown")

    async def _create_page(self, action: NotionAction, user_id: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """페이지 생성 (LLM 분석 정보 활용)"""
        
        # 1. 부모 페이지 찾기
        parent_page = None
        
        # A. LLM이 추출한 부모 페이지 이름이 있으면 우선 검색
        if action.parent_page_name:
            print(f"[DEBUG] 부모 페이지 검색: {action.parent_page_name}")
            search_res = await notion_tool.search_pages(user_id, action.parent_page_name, page_size=1)
            if search_res["success"] and search_res["data"]["pages"]:
                parent_page = search_res["data"]["pages"][0]
        
        # B. 못 찾았거나 명시 안 했으면 기본 페이지 검색 (개인, 메모 등)
        if not parent_page:
            defaults = ["개인", "Personal", "메모", "Memo", "Note", "Home"]
            for keyword in defaults:
                search_res = await notion_tool.search_pages(user_id, keyword, page_size=1)
                if search_res["success"] and search_res["data"]["pages"]:
                    parent_page = search_res["data"]["pages"][0]
                    break

        # C. 최후의 수단: 전체 중 최신 1개
        if not parent_page:
            search_res = await notion_tool.search_pages(user_id, "", page_size=1)
            if search_res["success"] and search_res["data"]["pages"]:
                parent_page = search_res["data"]["pages"][0]

        if not parent_page:
            return {
                "success": False,
                "answer": "❌ Notion에 저장할 페이지를 찾을 수 없습니다. Notion이 연동되어 있는지, '개인'이나 '메모' 같은 페이지가 있는지 확인해주세요.",
                "agent_used": self.name
            }
        
        # 2. 제목과 내용 결정
        title = action.title
        content = action.content
        
        # 3. 특수 토큰(내용) 처리
        # Case A: 이전 AI 답변 저장
        if content == "PREVIOUS_AI_RESPONSE":
            if context and "conversation_history" in context:
                history = context["conversation_history"]
                # 역순으로 탐색하여 가장 최근의 assistant 메시지 찾기
                last_ai_msg = None
                for msg in reversed(history):
                    if msg.get("role") == "assistant":
                        last_ai_msg = msg
                        break
                
                if last_ai_msg:
                    content = last_ai_msg.get("content", "")
                    # 제목이 없으면 내용 기반으로 자동 생성
                    if not title or title == "내용 정리":
                        title = self._generate_title_from_content(content)
                else:
                    return {"success": False, "answer": "저장할 이전 AI 답변을 찾을 수 없습니다.", "agent_used": self.name}
            else:
                return {"success": False, "answer": "대화 기록(Context)이 없어 내용을 저장할 수 없습니다.", "agent_used": self.name}
                
        # Case B: 대화 전체 요약 저장
        elif content == "CONTEXT_SUMMARY":
            if context and "conversation_history" in context:
                content = self._format_conversation_with_agents(context["conversation_history"])
                if not title:
                    title = f"AI 대화 기록 ({datetime.now().strftime('%Y-%m-%d')})"
            else:
                content = "대화 기록 없음"

        # Case C: 일반 내용 (None이거나 빈 문자열 처리)
        if not content:
            content = "내용 없음"
        
        # 제목이 여전히 없으면 기본값
        if not title:
            title = f"새 페이지 ({datetime.now().strftime('%H:%M')})"

        # 4. 마크다운으로 페이지 생성
        markdown = f"# {title}\n\n{content}"
        
        result = await notion_tool.create_page_from_markdown(
            user_id,
            parent_page["id"],
            title,
            markdown
        )
        
        if result["success"]:
            parent_info = f"**📁 {parent_page['title']}**"
            return {
                "success": True,
                "answer": f"✅ Notion에 저장 완료!\n\n{parent_info}\n**📄 {title}**\n\n[바로가기]({result['data']['url']})",
                "agent_used": self.name,
                "data": {**result["data"], "parent_page": parent_page['title']}
            }
        else:
            return {
                "success": False,
                "answer": f"❌ 페이지 생성 실패: {result['error']}",
                "agent_used": self.name
            }
    
    async def _search_pages(self, query: str, user_id: str) -> Dict[str, Any]:
        """페이지 검색"""
        if not query:
            return {"success": False, "answer": "검색어를 입력해주세요.", "agent_used": self.name}
            
        # 불필요한 조사 제거 (간단한 정규식 보조)
        search_query = re.sub(r"(을|를|이|가|에|에서|으로|로|찾아줘|검색해줘|보여줘)$", "", query).strip()
        
        result = await notion_tool.search_pages(user_id, search_query, page_size=5)
        
        if result["success"]:
            pages = result["data"]["pages"]
            if pages:
                answer = f"🔍 **'{search_query}'** 검색 결과:\n"
                for i, p in enumerate(pages, 1):
                    answer += f"{i}. [{p['title']}]({p['url']})\n"
                return {"success": True, "answer": answer, "agent_used": self.name, "data": {"pages": pages}}
            else:
                return {"success": True, "answer": f"'{search_query}'에 대한 검색 결과가 없습니다.", "agent_used": self.name}
        return {"success": False, "answer": f"검색 중 오류 발생: {result['error']}", "agent_used": self.name}

    async def _get_page_content(self, query: str, user_id: str, page_id: Optional[str] = None) -> Dict[str, Any]:
        """페이지 내용 조회"""
        target_id = page_id
        
        # ID가 없으면 검색해서 찾음
        if not target_id:
            # 이름으로 검색
            search_res = await self._search_pages(query, user_id)
            if search_res["success"] and search_res.get("data", {}).get("pages"):
                target_id = search_res["data"]["pages"][0]["id"]
        
        if not target_id:
            return {"success": False, "answer": "페이지를 찾을 수 없습니다.", "agent_used": self.name}

        # 내용 가져오기
        content_res = await notion_tool.get_page_content(user_id, target_id)
        if content_res["success"]:
            return {
                "success": True,
                "answer": f"📄 **{content_res['data']['title']}** 내용입니다:\n\n{content_res['data']['markdown']}",
                "agent_used": self.name
            }
        return {"success": False, "answer": f"내용을 가져오는데 실패했습니다: {content_res['error']}", "agent_used": self.name}

    def _generate_title_from_content(self, content: str) -> str:
        """내용에서 적절한 제목 생성 (첫 줄 사용)"""
        lines = content.split('\n')
        # 빈 줄 제외하고 첫 번째 줄 찾기
        for line in lines:
            clean_line = line.replace("#", "").strip()
            if clean_line:
                return clean_line[:30] + "..." if len(clean_line) > 30 else clean_line
        return f"메모 ({datetime.now().strftime('%Y-%m-%d')})"

    def _format_conversation_with_agents(self, conversation_history: list) -> str:
        """대화 내용을 마크다운으로 포맷팅"""
        formatted = []
        for msg in conversation_history:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "system": continue
            
            icon = "👤" if role == "user" else "🤖"
            name = "사용자" if role == "user" else "AI"
            
            # 에이전트 정보가 있으면 추가
            if role == "assistant" and msg.get("agent_used"):
                name = f"{msg['agent_used']} Agent"
                
            formatted.append(f"### {icon} {name}\n{content}")
            
        return "\n\n---\n\n".join(formatted)


