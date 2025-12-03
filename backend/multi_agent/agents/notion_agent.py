"""
Notion Agent

Notion API를 사용하여 페이지 검색, 생성, 수정 등을 처리하는 에이전트
"""

import sys
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

# Tools 경로 추가
tools_path = Path(__file__).resolve().parent.parent.parent.parent / "tools"
if str(tools_path) not in sys.path:
    sys.path.insert(0, str(tools_path))

from tools import notion_tool
from .base_agent import BaseAgent


class NotionAgent(BaseAgent):
    """Notion 작업을 처리하는 전문 에이전트"""
    
    def __init__(self):
        super().__init__(
            name="notion_agent",
            description="Notion 페이지 검색, 생성, 수정 등을 처리합니다."
        )
    
    async def process(self, query: str, user_id: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Notion 작업 처리
        """
        try:
            # 1. 의도 파악
            intent = self._analyze_intent(query)
            
            if intent == "search":
                return await self._search_pages(query, user_id)
            
            elif intent == "create":
                return await self._create_page(query, user_id, context)
            
            elif intent == "get":
                return await self._get_page_content(query, user_id)
            
            else:
                return {
                    "success": False,
                    "answer": "Notion 작업 의도를 파악할 수 없습니다. '페이지 검색', '페이지 생성' 등을 명확히 말씀해주세요.",
                    "agent_used": self.name
                }
        
        except Exception as e:
            return {
                "success": False,
                "answer": f"Notion 작업 중 오류가 발생했습니다: {str(e)}",
                "agent_used": self.name,
                "error": str(e)
            }
    
    def _analyze_intent(self, query: str) -> str:
        """의도 분석"""
        query_lower = query.lower()
        
        # 검색 키워드
        if any(keyword in query_lower for keyword in ["검색", "찾아", "찾기", "어디", "있어"]):
            return "search"
        
        # 생성/저장 키워드
        save_keywords = [
            "만들", "생성", "작성", "추가", "넣어", "적어", 
            "저장", "기록", "정리", "올려", "남겨", "메모"
        ]
        if any(keyword in query_lower for keyword in save_keywords):
            return "create"
        
        # 조회 키워드
        if any(keyword in query_lower for keyword in ["보여", "내용", "읽어", "가져와"]):
            return "get"
        
        return "create"
    
    async def _search_pages(self, query: str, user_id: str) -> Dict[str, Any]:
        """페이지 검색"""
        search_keywords = ["검색", "찾아", "찾기", "어디", "있어"]
        search_query = query
        for keyword in search_keywords:
            search_query = search_query.replace(keyword, "").strip()
        
        result = await notion_tool.search_pages(user_id, search_query, page_size=5)
        
        if result["success"]:
            pages = result["data"]["pages"]
            if pages:
                answer = f"'{search_query}' 검색 결과 {len(pages)}개를 찾았습니다:\n\n"
                for i, page in enumerate(pages, 1):
                    answer += f"{i}. **{page['title']}**\n"
                    answer += f"   - ID: `{page['id']}`\n"
                    answer += f"   - URL: {page['url']}\n\n"
                return {"success": True, "answer": answer, "agent_used": self.name, "data": {"pages": pages}}
            else:
                return {"success": True, "answer": f"'{search_query}'에 대한 검색 결과가 없습니다.", "agent_used": self.name}
        else:
            return {"success": False, "answer": f"페이지 검색 실패: {result['error']}", "agent_used": self.name}
    
    async def _create_page(self, query: str, user_id: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """페이지 생성 (자동화 로직 강화)"""
        
        # 1. 부모 페이지 찾기 (없으면 아무거나라도 찾아서 진행)
        parent_page = await self._find_parent_page(query, user_id)
        
        if not parent_page:
            # 특정 페이지를 못 찾았을 때, 저장할만한 일반적인 페이지를 검색
            default_keywords = ["메모", "Note", "개인", "Home", "General"]
            for keyword in default_keywords:
                result = await notion_tool.search_pages(user_id, keyword, page_size=1)
                if result["success"] and result["data"]["pages"]:
                    parent_page = result["data"]["pages"][0]
                    break
            
            # 그래도 없으면 전체 페이지 중 최신 것 하나 선택
            if not parent_page:
                result = await notion_tool.search_pages(user_id, "", page_size=1)
                if result["success"] and result["data"]["pages"]:
                    parent_page = result["data"]["pages"][0]

        if not parent_page:
            return {
                "success": False,
                "answer": "Notion에 저장할 페이지를 찾을 수 없습니다. Notion이 연동되어 있는지 확인해주세요.",
                "agent_used": self.name
            }
        
        # 2. 내용 및 제목 결정 (대화 내용 정리 우선)
        content = ""
        title = ""
        
        # [핵심] 대화 맥락 저장 요청인지 확인하는 키워드들
        context_keywords = ["상담", "대화", "이야기", "했던", "방금", "이전", "그 내용", "모든 내용", "이거", "그거", "저거"]
        summary_keywords = ["정리", "요약", "기록", "저장", "남겨"]
        
        # 사용자가 "상담 내용 정리해줘"라고 하면 True
        is_context_request = any(k in query for k in context_keywords) or any(k in query for k in summary_keywords)
        
        # 명시적인 텍스트("~라고 적어줘")가 있는지 추출
        extracted_text = self._extract_content(query)
        is_explicit_content = extracted_text != query 

        # [수정된 부분] 추출된 텍스트가 '상담 내용' 같은 지시어라면, 이는 텍스트가 아니라 명령임 -> 대화 기록 사용으로 유도
        ignore_patterns = ["상담", "내용", "대화", "이야기", "이거", "그거"]
        if any(pat in extracted_text for pat in ignore_patterns) and len(extracted_text) < 10:
             is_explicit_content = False
             is_context_request = True

        # 로직 분기: 컨텍스트 저장이 우선순위가 됨 (단, 명확한 "~라고 적어줘"는 제외)
        if is_context_request and context and "conversation_history" in context:
            # Case A: 대화 내용 정리 ("이거 정리해줘", "상담 기록해줘")
            content = self._format_conversation(context["conversation_history"])
            
            # 제목 자동 생성
            now_str = datetime.now().strftime('%Y-%m-%d %H:%M')
            if "상담" in query:
                title = f"🧠 심리상담 기록 ({now_str})"
            elif "브레인" in query or "아이디어" in query:
                title = f"💡 브레인스토밍 아이디어 ({now_str})"
            else:
                title = f"📝 AI 대화 요약 ({now_str})"

        elif is_explicit_content:
            # Case B: 특정 내용 작성 ("'안녕'이라고 적어줘")
            content = extracted_text
            title = content if len(content) < 30 else f"{content[:30]}..."
            
        else:
            # Case C: 쿼리 자체를 내용으로 ("회의록 페이지 만들어")
            content = extracted_text
            title = content if len(content) < 30 else f"{content[:30]}..."

        # 3. 마크다운으로 페이지 생성
        markdown = f"# {title}\n\n{content}"
        
        result = await notion_tool.create_page_from_markdown(
            user_id,
            parent_page["id"],
            title,
            markdown
        )
        
        if result["success"]:
            return {
                "success": True,
                "answer": f"✅ **{parent_page['title']}** 페이지에 **'{title}'**을 저장했습니다!\n[바로가기]({result['data']['url']})",
                "agent_used": self.name,
                "data": result["data"]
            }
        else:
            return {
                "success": False,
                "answer": f"페이지 생성 실패: {result['error']}",
                "agent_used": self.name
            }
    
    async def _find_parent_page(self, query: str, user_id: str) -> Optional[Dict[str, Any]]:
        """자연어로 부모 페이지 찾기"""
        query_lower = query.lower()
        
        # 1. "개인", "내" 키워드 우선 검색
        personal_keywords = ["개인", "내", "나의", "my", "personal"]
        if any(keyword in query_lower for keyword in personal_keywords):
            result = await notion_tool.search_pages(user_id, "개인", page_size=5)
            if result["success"] and result["data"]["pages"]:
                return result["data"]["pages"][0]
        
        # 2. "XXX 페이지에" 패턴 검색
        query_for_search = re.sub(r"['\"]?(.+?)['\"]?(?:라고|이라고|라구|이라구).*", "", query)
        patterns = [r"(.+?)(?:페이지|문서)?\s*에", r"(.+?)(?:페이지|문서)?\s*로"]
        
        for pattern in patterns:
            match = re.search(pattern, query_for_search)
            if match:
                page_name = match.group(1).strip()
                page_name = page_name.replace("그냥", "").strip()
                if len(page_name) > 1:
                    result = await notion_tool.search_pages(user_id, page_name, page_size=5)
                    if result["success"] and result["data"]["pages"]:
                        return result["data"]["pages"][0]
        return None
    
    def _extract_content(self, query: str) -> str:
        """내용 추출"""
        # "~라고" 패턴
        patterns = [r"['\"]?(.+?)['\"]?(?:라고|이라고|라구|이라구)"]
        for pattern in patterns:
            match = re.search(pattern, query)
            if match:
                content = match.group(1).strip()
                content = re.sub(r".*(?:에|로)\s+", "", content) 
                return content
        
        # "~를/을" 패턴
        match = re.search(r"(?:에|로)?\s*['\"]?(.+?)['\"]?(?:를|을)\s*(?:적어|넣어|만들|작성|추가|저장|기록)", query)
        if match:
            candidate = match.group(1).strip()
            if "페이지" not in candidate and "문서" not in candidate and "노션" not in candidate:
                return candidate
        
        return query
    
    def _format_conversation(self, conversation_history: list) -> str:
        """대화 내용을 마크다운으로 깔끔하게 포맷팅"""
        formatted = []
        for msg in conversation_history:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            
            # 시스템 메시지 등은 제외
            if role == "system": continue
                
            if role == "user":
                formatted.append(f"**👤 사용자:**\n{content}")
            elif role == "assistant":
                formatted.append(f"**🤖 AI:**\n{content}")
                
        return "\n\n---\n\n".join(formatted)

    # 필수 인터페이스 메서드들
    async def _get_page_content(self, query: str, user_id: str) -> Dict[str, Any]:
        page_id = self._extract_page_id(query)
        if not page_id:
            return {"success": False, "answer": "페이지 ID를 찾을 수 없습니다."}
        result = await notion_tool.get_page_content(user_id, page_id)
        if result["success"]:
            return {"success": True, "answer": result['data']['markdown'], "data": result['data']}
        return {"success": False, "answer": "실패"}

    def _extract_page_id(self, query: str) -> Optional[str]:
        match = re.search(r'[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}', query)
        if match: return match.group(0)
        return None