import sys
from pathlib import Path
from typing import Dict, Any, Optional, Literal, List
import difflib

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

# tools 경로 추가 (환경에 따라 경로가 다를 수 있으므로 유지)
tools_path = Path(__file__).resolve().parent.parent.parent.parent / "tools"
if str(tools_path) not in sys.path:
    sys.path.insert(0, str(tools_path))

from tools import notion_tool
from .base_agent import BaseAgent
from app.core.config import settings


Mode = Literal["search", "get", "create"]


class NotionAgent(BaseAgent):
    """
    Notion 전용 에이전트.
    검색(RAG), 상세 조회(Get), 페이지 생성(Create) 기능을 수행합니다.
    """

    def __init__(self) -> None:
        super().__init__(
            name="notion_agent",
            description="Notion 페이지 검색, 상세 조회, 생성 및 저장을 수행합니다.",
        )
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0,
            api_key=settings.OPENAI_API_KEY,
        )

    async def process(
        self,
        query: str,
        user_id: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        에이전트 메인 실행 함수
        """
        try:
            # 1. 사용자의 의도(Mode) 파악
            mode = await self._decide_mode(query)
            print(f"🤖 [NotionAgent] mode={mode} / query='{query}'")

            # 2. 모드별 핸들러 실행
            if mode == "search":
                return await self._handle_search(query, user_id)

            if mode == "get":
                return await self._get_page_content(query, user_id)

            if mode == "create":
                return await self._create_page(query, user_id, context)

            # 기본값은 검색
            return await self._handle_search(query, user_id)

        except Exception as e:
            return {
                "success": False,
                "answer": f"Notion 에이전트 오류 발생: {str(e)}",
                "agent_used": self.name,
            }

    # ------------------------------------------------------------------
    # 1. 모드 결정 (Context-Aware Router)
    # ------------------------------------------------------------------
    async def _decide_mode(self, query: str, context: Optional[Dict[str, Any]] = None) -> Mode:
        
        # 1. 대화 이력 가져오기 (라우터도 맥락을 알아야 함)
        history_text = "없음 (새로운 대화)"
        if context and "conversation_history" in context:
            # 최근 2턴만 봐도 흐름 파악 가능
            recent = context["conversation_history"][-2:]
            history_text = "\n".join([f"- {m.get('role')}: {m.get('content')}" for m in recent])

        # 2. 강력한 Few-Shot 프롬프트
        system_prompt = """
    당신은 Notion Agent의 '의도 분류기(Intent Classifier)'입니다.
    사용자의 발화와 '이전 대화 흐름'을 분석하여 다음 3가지 모드 중 하나를 선택하세요.

    ### 1. create (생성/저장)
    - **상태 변경(Mutation)**이 목적일 때.
    - 문맥상 정보를 기록, 저장, 추가, 작성, 정리해달라는 의도.

    ### 2. get (조회/가져오기)
    - 사용자가 "내용 보여줘", "읽어줘", "무슨 내용이야?" 같이 **구체적인 내용 확인**을 원할 때.
   - page_id: 페이지 ID가 있다면 추출 (없으면 null)
   - search_query: ID가 없을 경우 검색할 핵심 키워드

    ### 3. search (검색/질문)
    - 특정 정보가 있는지 찾거나, 질문에 대한 답을 원할 때 (RAG).
    - 정보에 대한 질문을 할 경우 검색 결과를 받아 적절하게 응답하세요

    ### 중요 판단 기준
    - 사용자가 저장, 추가, 작성, 정리하라고 하면 -> **create**
    - 사용자가 조회, 가져오기, 읽어줘하면 -> **get**
    - 사용자가 검색, 질문, 정보를 찾고 싶을 때 -> **search**

    반환값은 오직 단어 하나: "search", "get", "create"
    """
        
        # 프롬프트에 '대화 이력'을 같이 태움
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("user", f"[이전 대화 흐름]\n{history_text}\n\n[현재 사용자 입력]\n{query}")
        ])
        
        chain = prompt | self.llm | StrOutputParser()
        result = (await chain.ainvoke({})).strip().lower()
        
        # 하드코딩 제거함. 이제 LLM의 판단을 신뢰.
        if result in ["search", "get", "create"]:
            return result # type: ignore
        return "search"

    # ------------------------------------------------------------------
    # [보조 함수] 전체 페이지 목록 가져오기 (페이지네이션 처리)
    # ------------------------------------------------------------------
    async def _get_all_pages(self, user_id: str, max_pages: int = 100) -> List[Dict[str, Any]]:
        """
        Notion에서 모든 페이지를 가져옵니다 (페이지네이션 처리).
        """
        all_pages = []
        try:
            from tools.token_manager import load_token
            token_data = await load_token(user_id, "notion")
            if not token_data:
                return all_pages
            
            from notion_client import AsyncClient
            notion = AsyncClient(auth=token_data.get("access_token"))
            
            # 첫 페이지 가져오기
            search_response = await notion.search(
                query="",
                filter={"property": "object", "value": "page"},
                page_size=min(100, max_pages)
            )
            
            results = search_response.get("results", [])
            has_more = search_response.get("has_more", False)
            next_cursor = search_response.get("next_cursor")
            
            # 첫 페이지 처리
            for page in results:
                page_id = page.get("id")
                title = "Untitled"
                properties = page.get("properties", {})
                for prop_name, prop_value in properties.items():
                    if prop_value.get("type") == "title":
                        title_array = prop_value.get("title", [])
                        if title_array:
                            title = title_array[0].get("text", {}).get("content", "Untitled")
                        break
                
                all_pages.append({
                    "id": page_id,
                    "title": title,
                    "url": page.get("url", "")
                })
            
            # 페이지네이션 처리 (최대 max_pages까지)
            while has_more and len(all_pages) < max_pages and next_cursor:
                search_response = await notion.search(
                    query="",
                    filter={"property": "object", "value": "page"},
                    page_size=min(100, max_pages - len(all_pages)),
                    start_cursor=next_cursor
                )
                
                results = search_response.get("results", [])
                has_more = search_response.get("has_more", False)
                next_cursor = search_response.get("next_cursor")
                
                for page in results:
                    page_id = page.get("id")
                    title = "Untitled"
                    properties = page.get("properties", {})
                    for prop_name, prop_value in properties.items():
                        if prop_value.get("type") == "title":
                            title_array = prop_value.get("title", [])
                            if title_array:
                                title = title_array[0].get("text", {}).get("content", "Untitled")
                            break
                    
                    all_pages.append({
                        "id": page_id,
                        "title": title,
                        "url": page.get("url", "")
                    })
            
        except Exception as e:
            print(f"⚠️ [전체 페이지 가져오기 오류] {e}")
        
        return all_pages

    # ------------------------------------------------------------------
    # [보조 함수] 자연어 쿼리에서 페이지 이름만 추출
    # ------------------------------------------------------------------
    async def _extract_page_name(self, query: str) -> str:
        """
        자연어 쿼리에서 페이지 이름만 추출합니다.
        
        예시:
        - "프로젝트 아이디어"라는 페이지 → "프로젝트 아이디어"
        - "승진프로세스 개인페이지 안에 개인정리 페이지" → "개인정리"
        - "NLP라는 AI 직군" → "NLP"
        - "프로젝트 아이디어에 저장해줘" → "프로젝트 아이디어"
        """
        extract_prompt = ChatPromptTemplate.from_messages([
            ("system", """
당신은 사용자의 자연어 입력에서 Notion 페이지 이름만 추출하는 전문가입니다.

[임무]
사용자의 입력에서 실제 Notion 페이지 이름만 깔끔하게 추출하세요.
- 불필요한 설명, 조사, 문맥 단어는 제거
- 페이지 이름만 정확히 추출
- 따옴표나 인용부호가 있으면 그 안의 내용을 우선

[예시]
입력: "프로젝트 아이디어"라는 페이지
출력: 프로젝트 아이디어

입력: 승진프로세스 개인페이지 안에 개인정리 페이지
출력: 개인정리

입력: "NLP라는 AI 직군"
출력: NLP

입력: 프로젝트 아이디어에 저장해줘
출력: 프로젝트 아이디어

입력: 개인정리 페이지 내용 보여줘
출력: 개인정리

[규칙]
- 출력은 오직 페이지 이름만 (따옴표 없이)
- 설명이나 추가 텍스트 없이
- 한 단어 또는 여러 단어로 구성된 페이지 이름만
"""),
            ("user", query)
        ])
        
        chain = extract_prompt | self.llm | StrOutputParser()
        extracted = (await chain.ainvoke({})).strip()
        
        # 따옴표 제거 (있을 경우)
        extracted = extracted.strip('"\'')
        
        print(f"📝 [페이지 이름 추출] '{query}' → '{extracted}'")
        return extracted

    # ------------------------------------------------------------------
    # [보조 함수] 유사도 검증 및 매칭 로직 (강화된 버전)
    # ------------------------------------------------------------------
    def _find_best_match(self, target_name: str, pages: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        검색된 페이지 목록(pages) 중에서 target_name과 가장 유사한 페이지를 찾습니다.
        사용자가 입력한 이름과 Notion 페이지 이름을 정확히 비교합니다.
        """
        if not pages:
            return None
        
        target_original = target_name.strip()
        target_norm = target_name.replace(" ", "").replace("_", "").replace("-", "").lower().strip()
        
        print(f"\n🔍 [매칭 시작] 사용자 입력: '{target_original}'")
        print(f"📋 [후보 페이지 수] {len(pages)}개")
        
        # 모든 후보 페이지 제목 출력 (디버깅용)
        print("📝 [후보 페이지 목록]:")
        for i, p in enumerate(pages[:20], 1):  # 최대 20개만 출력
            print(f"   {i}. '{p['title']}' (ID: {p['id'][:8]}...)")
        if len(pages) > 20:
            print(f"   ... 외 {len(pages) - 20}개 더")
        
        # 0. 정확한 이름 매칭 (최우선) - 원본 그대로 비교
        for p in pages:
            if target_original == p["title"]:
                print(f"✅ [정확 매칭 - 원본] '{target_original}' == '{p['title']}'")
                return p
        
        # 0-1. 정확한 이름 매칭 (대소문자 무시)
        for p in pages:
            if target_original.lower() == p["title"].lower():
                print(f"✅ [정확 매칭 - 대소문자 무시] '{target_original}' == '{p['title']}'")
                return p
        
        # 0-2. 정확한 이름 매칭 (공백, 언더스코어, 하이픈 무시)
        for p in pages:
            page_title_norm = p["title"].replace(" ", "").replace("_", "").replace("-", "").lower().strip()
            if target_norm == page_title_norm:
                print(f"✅ [정확 매칭 - 특수문자 무시] '{target_original}' == '{p['title']}'")
                return p
        
        # 1. 포함 여부 확인 (Substring Match) - 양방향 확인
        for p in pages:
            page_title_norm = p["title"].replace(" ", "").replace("_", "").replace("-", "").lower().strip()
            # 양방향 포함 확인
            if target_norm in page_title_norm or page_title_norm in target_norm:
                # 너무 짧은 단어는 제외 (예: "a", "the" 등)
                if len(target_norm) >= 2:
                    print(f"✅ [포함 매칭] '{target_original}' in '{p['title']}'")
                    return p
        
        # 2. 유사도 점수 확인 (Fuzzy Match using difflib) - 오타 허용
        best_page = None
        highest_ratio = 0.0
        
        for p in pages:
            page_title_norm = p["title"].replace(" ", "").replace("_", "").replace("-", "").lower().strip()
            ratio = difflib.SequenceMatcher(None, target_norm, page_title_norm).ratio()
            
            if ratio > highest_ratio:
                highest_ratio = ratio
                best_page = p
        
        # 유사도 임계값 조정 (0.7 이상이면 확실한 매칭)
        if highest_ratio >= 0.7:
            print(f"✅ [유사도 매칭] '{target_original}' ~ '{best_page['title']}' (ratio: {highest_ratio:.2f})")
            return best_page
        elif highest_ratio >= 0.5:
            # 0.5~0.7 사이는 경고와 함께 반환
            print(f"⚠️ [낮은 유사도 매칭] '{target_original}' ~ '{best_page['title']}' (ratio: {highest_ratio:.2f})")
            return best_page
        else:
            print(f"❌ [매칭 실패] '{target_original}' - 최고 유사도: {highest_ratio:.2f} (최고 후보: '{best_page['title'] if best_page else 'None'}')")
            return None

    # ------------------------------------------------------------------
    # 2. search (RAG) - 일반 검색 및 답변
    # ------------------------------------------------------------------
    async def _handle_search(
        self,
        query: str,
        user_id: str,
        max_pages_for_rag: int = 3,
    ) -> Dict[str, Any]:
        
        # 1. 노션 검색 API 호출
        result = await notion_tool.search_pages(user_id, query, page_size=max_pages_for_rag)
        if not result["success"]:
            return {"success": False, "answer": f"노션 검색 오류: {result['error']}", "agent_used": self.name}

        pages = result["data"]["pages"]
        if not pages:
            return {"success": True, "answer": "노션에서 관련 문서를 찾을 수 없습니다.", "agent_used": self.name}

        # 2. 검색된 페이지들의 내용(Markdown) 가져오기
        chunks = []
        for p in pages:
            res = await notion_tool.get_page_content(user_id, p["id"])
            if res["success"]:
                # 문서 제목과 내용을 합쳐서 컨텍스트로 구성
                chunks.append(f"### 문서제목: {res['data']['title']}\n{res['data']['markdown']}")

        # 3. LLM에게 답변 생성 요청
        context_text = "\n\n".join(chunks)[:20000] # 토큰 제한 고려하여 길이 자름
        answer_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", "Notion 검색 결과를 바탕으로 사용자의 질문에 답변하세요. 정보가 없으면 모른다고 하세요."),
                ("user", f"[검색된 노션 문서들]\n{context_text}\n\n[사용자 질문]\n{query}"),
            ]
        )
        chain = answer_prompt | self.llm | StrOutputParser()
        answer = await chain.ainvoke({})

        return {"success": True, "answer": answer, "agent_used": self.name}

    # ------------------------------------------------------------------
    # 3. create (저장) - [수정: 상위 페이지 지정 강제화 (Strict Mode)]
    # ------------------------------------------------------------------
    async def _create_page(
        self,
        query: str,
        user_id: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        
        # 0. 세션의 모든 대화 내용 가져오기 (context에서)
        full_conversation = ""
        if context and "conversation_history" in context:
            history = context["conversation_history"]
            if history:
                # 모든 대화를 형식화하여 저장
                conversation_parts = []
                for msg in history:
                    role = msg.get("role", "unknown")
                    msg_content = msg.get("content", "").strip()
                    if msg_content:
                        if role == "user":
                            conversation_parts.append(f"## 👤 사용자\n\n{msg_content}")
                        elif role == "assistant":
                            conversation_parts.append(f"## 🤖 AI 비서\n\n{msg_content}")
                
                if conversation_parts:
                    full_conversation = "\n\n---\n\n".join(conversation_parts)
                    print(f"📝 [전체 대화 내용 발견] {len(history)}개 메시지, {len(full_conversation)}자")
        
        # 1. 정보 추출 (전체 대화 내용 포함)
        extract_prompt = ChatPromptTemplate.from_messages([
            ("system", """
            [임무]
            사용자의 요청에서 '제목', '상위페이지', '내용'을 추출하세요.
            - 사용자가 상위페이지(저장 위치)를 명시하지 않았다면 "NONE"이라고 출력하세요.
            - 사용자가 "방금 답변해준 내용", "이전 답변", "위 내용", "대화 내용", "채팅 내역" 등을 언급하면, 제공된 [전체 대화 내용]을 사용하세요.
            - 내용이 명시되지 않았고 전체 대화 내용이 있으면, 그 내용을 사용하세요.
            - 사용자가 "전부 저장", "모두 저장", "대화 전부" 등을 요청하면 전체 대화 내용을 저장하세요.
            
            [출력 예시]
            제목: ...
            상위페이지: NONE
            내용: ...
            """),
            ("user", f"""{query}

[전체 대화 내용]
{full_conversation if full_conversation else "없음"}""")
        ])
        extracted = await (extract_prompt | self.llm | StrOutputParser()).ainvoke({})
        
        title = "새 페이지"
        parent_query = "NONE"
        content_lines = []
        mode_parser = None
        
        for line in extracted.splitlines():
            if line.startswith("제목:"): title = line.replace("제목:", "").strip()
            elif line.startswith("상위페이지:"): parent_query = line.replace("상위페이지:", "").strip()
            elif line.startswith("내용:"): 
                mode_parser = "content"
                temp = line.replace("내용:", "").strip()
                if temp: content_lines.append(temp)
            elif mode_parser == "content":
                content_lines.append(line)
        
        content = "\n".join(content_lines).strip() or "내용 없음"
        
        # 내용이 여전히 비어있거나 "내용 없음"이고 전체 대화 내용이 있으면 직접 사용
        if not content or content == "내용 없음" or len(content) < 10:
            if full_conversation:
                content = full_conversation
                print(f"✅ [전체 대화 내용 사용] {len(content)}자")
                
                # 제목이 기본값이면 대화 기반으로 제목 생성
                if title == "새 페이지":
                    title_prompt = ChatPromptTemplate.from_messages([
                        ("system", "사용자의 대화 내용을 바탕으로 적절한 페이지 제목을 생성하세요. 제목만 출력하세요."),
                        ("user", f"다음 대화 내용의 제목을 생성해주세요:\n\n{full_conversation[:500]}")
                    ])
                    title = (await (title_prompt | self.llm | StrOutputParser()).ainvoke({})).strip()
                    print(f"📝 [자동 생성 제목] '{title}'")

        # ---------------------------------------------------------
        # [Strict Logic] 상위 페이지 미지정 시 즉시 중단 및 질문
        # ---------------------------------------------------------
        if parent_query == "NONE" or not parent_query:
            # 사용자의 최근 편집 목록을 보여주며 선택 유도 (UX 편의성)
            recents = await notion_tool.search_pages(user_id, "", page_size=5)
            list_str = ""
            if recents["success"]:
                list_str = "\n".join([f"- {p['title']}" for p in recents["data"]["pages"]])
            
            return {
                "success": False,
                "answer": (
                    f"⛔ **어디에 저장할까요?**\n"
                    f"[최근 편집한 페이지]\n{list_str}\n\n"
                    f"예시: \"'{recents['data']['pages'][0]['title']}'에 저장해줘\""
                ),
                "agent_used": self.name
            }

        # ---------------------------------------------------------
        # [Verification] 지정된 페이지가 실제로 존재하는지 확인
        # ---------------------------------------------------------
        # 1. 자연어 쿼리에서 페이지 이름만 추출
        parent_page_name = await self._extract_page_name(parent_query)
        
        # 2. 전체 페이지 목록 가져오기 (정확한 매칭을 위해)
        print(f"🔍 [페이지 검색] 원본: '{parent_query}' → 추출: '{parent_page_name}'")
        print(f"📥 [전체 페이지 목록 가져오기] 시작...")
        candidates = await self._get_all_pages(user_id, max_pages=100)
        print(f"📋 [전체 페이지 목록] {len(candidates)}개 페이지 로드 완료")
        
        # 3. 추출한 페이지 이름과 모든 페이지 이름을 비교하여 정확히 매칭
        target_page = self._find_best_match(parent_page_name, candidates)
        
        # 4. 못 찾았으면 중단 (절대 추측 금지)
        if not target_page:
            if candidates:
                list_str = "\n".join([f"- {p['title']}" for p in candidates])
                return {
                    "success": False,
                    "answer": (
                        f"🤔 **'{parent_page_name}'**와 정확히 일치하는 페이지를 못 찾겠습니다.\n"
                        f"혹시 아래 목록 중 하나인가요?\n\n"
                        f"{list_str}\n\n"
                        "**목록에 있는 정확한 이름을 다시 말씀해 주세요.**"
                    ),
                    "agent_used": self.name
                }
            else:
                return {
                    "success": False,
                    "answer": f"⛔ **'{parent_page_name}'**라는 페이지를 찾을 수 없습니다. 이름이 정확한지 확인해주세요.",
                    "agent_used": self.name
                }

        # 4. 모든 조건 통과 -> 생성 진행
        markdown = f"# {title}\n\n{content}"
        result = await notion_tool.create_page_from_markdown(user_id, target_page["id"], title, markdown)

        if result["success"]:
            return {
                "success": True,
                "answer": f"✅ **[{target_page['title']}]** 페이지 안에 **'{title}'** 문서를 저장했습니다.",
                "agent_used": self.name,
                "data": {"url": result["data"]["url"]}
            }
        else:
            return {"success": False, "answer": f"API 오류: {result.get('error')}", "agent_used": self.name}

    # ------------------------------------------------------------------
    # 4. get (조회) 
    # ------------------------------------------------------------------
    async def _get_page_content(
        self,
        query: str,
        user_id: str,
    ) -> Dict[str, Any]:
        
        # 1. 자연어 쿼리에서 페이지 이름만 추출
        page_name = await self._extract_page_name(query)
        
        # 2. 전체 페이지 목록 가져오기 (정확한 매칭을 위해)
        print(f"🔍 [페이지 조회] 원본: '{query}' → 추출: '{page_name}'")
        print(f"📥 [전체 페이지 목록 가져오기] 시작...")
        candidates = await self._get_all_pages(user_id, max_pages=100)
        print(f"📋 [전체 페이지 목록] {len(candidates)}개 페이지 로드 완료")
        
        if not candidates:
            return {"success": False, "answer": "Notion에서 페이지를 가져올 수 없습니다.", "agent_used": self.name}
        
        # 3. 추출한 페이지 이름과 모든 페이지 이름을 비교하여 정확히 매칭
        target = self._find_best_match(page_name, candidates)
        
        # 4. 정확한 페이지를 못 찾았을 때 리스트 제공하고 중단
        if not target:
            candidate_list_str = "\n".join([f"- {p['title']}" for p in candidates])
            return {
                "success": False,
                "answer": (
                    f"🤔 **'{page_name}'**와 정확히 일치하는 페이지를 찾기 어렵습니다.\n"
                    f"혹시 찾으시는 페이지가 아래 목록에 있나요?\n\n"
                    f"{candidate_list_str}\n\n"
                    "정확한 이름을 다시 알려주시면 내용을 가져오겠습니다."
                ),
                "agent_used": self.name
            }
        
        # 3. 내용 가져오기 (매칭 성공 시)
        content_res = await notion_tool.get_page_content(user_id, target["id"])
        if not content_res["success"]:
             return {"success": False, "answer": "내용 로드 실패.", "agent_used": self.name}

        # 4. 결과 반환 (이메일 에이전트 등에서 쓰기 좋게 markdown 원문 반환)
        return {
            "success": True,
            "answer": content_res["data"]["markdown"], 
            "agent_used": self.name,
        }