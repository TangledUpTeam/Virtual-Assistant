"""
Today Plan Chain

LangChain 기반 오늘의 추천 일정 생성 체인

Author: AI Assistant
Created: 2025-11-18
"""
from typing import Optional, List
from datetime import date

from app.llm.client import LLMClient
from app.domain.planner.tools import YesterdayReportTool
from app.domain.search.retriever import UnifiedRetriever, UnifiedSearchResult
from app.domain.planner.schemas import (
    TodayPlanRequest,
    TodayPlanResponse,
    TaskItem
)


class TodayPlanGenerator:
    """오늘의 추천 일정 생성기"""
    
    SYSTEM_PROMPT = """너는 보험 설계사의 AI 업무 플래너이다.

전날의 미종결 업무(unresolved)와 익일 계획(next_day_plan)을 우선 참고하고,
미종결 업무가 적거나 없으면 과거 유사 업무 패턴(similar_tasks)을 참고하여
오늘 하루 동안 수행할 추천 일정을 JSON 형식으로 구성해라.

규칙:
1. 미종결 업무가 있으면 우선순위를 높게 설정하고 반드시 포함
2. 미종결 업무가 1개 이하이거나 없으면 과거 유사 업무 패턴을 참고하여 추천
3. 익일 계획을 바탕으로 구체적인 작업 생성
4. 각 작업은 실행 가능하고 명확해야 함
5. 우선순위: high(긴급/중요), medium(보통), low(여유)
6. 예상 시간: "30분", "1시간", "2시간" 등
7. 카테고리: "고객 상담", "계약 처리", "문서 작업", "학습", "기타" 등

반드시 다음 JSON 형식으로만 응답:
{
  "tasks": [
    {
      "title": "작업 제목",
      "description": "작업 설명",
      "priority": "high|medium|low",
      "expected_time": "예상 시간",
      "category": "카테고리"
    }
  ],
  "summary": "오늘 일정 전체 요약 (1-2문장)"
}
"""
    
    def __init__(
        self,
        retriever_tool: YesterdayReportTool,
        llm_client: LLMClient,
        vector_retriever: Optional[UnifiedRetriever] = None
    ):
        """
        초기화
        
        Args:
            retriever_tool: 전날 보고서 검색 도구 (PostgreSQL)
            llm_client: LLM 클라이언트
            vector_retriever: VectorDB 검색기 (과거 업무 패턴 검색용, 선택적)
        """
        self.retriever_tool = retriever_tool
        self.llm_client = llm_client
        self.vector_retriever = vector_retriever
    
    async def generate(
        self,
        request: TodayPlanRequest
    ) -> TodayPlanResponse:
        """
        오늘의 추천 일정 생성
        
        Args:
            request: 일정 생성 요청
            
        Returns:
            생성된 일정
        """
        # Step 1: 전날 보고서 가져오기
        yesterday_data = self.retriever_tool.get_yesterday_report(
            owner=request.owner,
            target_date=request.target_date
        )
        
        unresolved = yesterday_data["unresolved"]
        next_day_plan = yesterday_data["next_day_plan"]
        tasks = yesterday_data.get("tasks", [])
        found = yesterday_data["found"]
        
        print(f"[DEBUG] TodayPlanGenerator.generate (async): found={found}, unresolved={len(unresolved)}, next_day_plan={len(next_day_plan)}, tasks={len(tasks)}, search_date={yesterday_data.get('search_date')}")
        
        # Step 2: VectorDB에서 유사 업무 패턴 검색 (미종결 업무가 적거나 없을 때)
        similar_tasks: List[UnifiedSearchResult] = []
        if self.vector_retriever and (not unresolved or len(unresolved) <= 1):
            # 미종결 업무가 1개 이하이거나 없으면 VectorDB에서 유사 업무 검색
            try:
                search_query = f"{request.owner} 업무 일정"
                if unresolved:
                    search_query += f" {unresolved[0]}"
                
                similar_tasks = self.vector_retriever.search_daily(
                    query=search_query,
                    owner=request.owner,
                    n_results=10  # 과거 유사 업무 패턴 가져오기
                )
                print(f"[INFO] VectorDB에서 {len(similar_tasks)}개의 유사 업무 패턴 발견")
            except Exception as e:
                print(f"[WARNING] VectorDB 검색 실패: {e}")
                similar_tasks = []
        
        # 데이터가 없고 VectorDB 결과도 없으면 기본 응답
        if not found and not similar_tasks and (not unresolved and not next_day_plan and not tasks):
            return TodayPlanResponse(
                tasks=[
                    TaskItem(
                        title="일일 업무 계획 수립",
                        description="오늘의 업무 목표와 일정을 계획합니다.",
                        priority="high",
                        expected_time="30분",
                        category="기획"
                    )
                ],
                summary="전날 데이터가 없어 기본 일정을 생성했습니다.",
                source_date=yesterday_data["search_date"],
                owner=request.owner
            )
        
        # Step 3: LLM 프롬프트 구성
        user_prompt = self._build_user_prompt(
            today=request.target_date,
            owner=request.owner,
            unresolved=unresolved,
            next_day_plan=next_day_plan,
            similar_tasks=similar_tasks
        )
        
        # Step 4: LLM 호출 (JSON 응답)
        llm_response = await self.llm_client.acomplete_json(
            system_prompt=self.SYSTEM_PROMPT,
            user_prompt=user_prompt,
            temperature=0.7,
            max_tokens=1500
        )
        
        # Step 4: 응답 파싱 및 검증
        tasks = []
        for task_dict in llm_response.get("tasks", []):
            try:
                task = TaskItem(**task_dict)
                tasks.append(task)
            except Exception as e:
                print(f"[WARNING] Task parsing error: {e}")
                continue
        
        summary = llm_response.get("summary", "오늘의 추천 일정입니다.")
        
        return TodayPlanResponse(
            tasks=tasks,
            summary=summary,
            source_date=yesterday_data["search_date"],
            owner=request.owner
        )
    
    def generate_sync(
        self,
        request: TodayPlanRequest
    ) -> TodayPlanResponse:
        """
        동기 버전: 오늘의 추천 일정 생성
        
        Args:
            request: 일정 생성 요청
            
        Returns:
            생성된 일정
        """
        # Step 1: 전날 보고서 가져오기
        yesterday_data = self.retriever_tool.get_yesterday_report(
            owner=request.owner,
            target_date=request.target_date
        )
        
        unresolved = yesterday_data["unresolved"]
        next_day_plan = yesterday_data["next_day_plan"]
        tasks = yesterday_data.get("tasks", [])
        found = yesterday_data["found"]
        
        print(f"[DEBUG] TodayPlanGenerator.generate_sync: found={found}, unresolved={len(unresolved)}, next_day_plan={len(next_day_plan)}, tasks={len(tasks)}, search_date={yesterday_data.get('search_date')}")
        
        # Step 2: VectorDB에서 유사 업무 패턴 검색 (미종결 업무가 적거나 없을 때)
        similar_tasks: List[UnifiedSearchResult] = []
        if self.vector_retriever and (not unresolved or len(unresolved) <= 1):
            try:
                search_query = f"{request.owner} 업무 일정"
                if unresolved:
                    search_query += f" {unresolved[0]}"
                
                similar_tasks = self.vector_retriever.search_daily(
                    query=search_query,
                    owner=request.owner,
                    n_results=10
                )
                print(f"[INFO] VectorDB에서 {len(similar_tasks)}개의 유사 업무 패턴 발견")
            except Exception as e:
                print(f"[WARNING] VectorDB 검색 실패: {e}")
                similar_tasks = []
        
        # 데이터가 없고 VectorDB 결과도 없으면 기본 응답
        if not found and not similar_tasks and (not unresolved and not next_day_plan and not tasks):
            return TodayPlanResponse(
                tasks=[
                    TaskItem(
                        title="일일 업무 계획 수립",
                        description="오늘의 업무 목표와 일정을 계획합니다.",
                        priority="high",
                        expected_time="30분",
                        category="기획"
                    )
                ],
                summary="전날 데이터가 없어 기본 일정을 생성했습니다.",
                source_date=yesterday_data["search_date"],
                owner=request.owner
            )
        
        # Step 3: LLM 프롬프트 구성
        user_prompt = self._build_user_prompt(
            today=request.target_date,
            owner=request.owner,
            unresolved=unresolved,
            next_day_plan=next_day_plan,
            tasks=tasks,
            similar_tasks=similar_tasks
        )
        
        # Step 4: LLM 호출 (JSON 응답) - 동기
        llm_response = self.llm_client.complete_json(
            system_prompt=self.SYSTEM_PROMPT,
            user_prompt=user_prompt,
            temperature=0.7,
            max_tokens=1500
        )
        
        # Step 5: 응답 파싱 및 검증
        tasks = []
        for task_dict in llm_response.get("tasks", []):
            try:
                task = TaskItem(**task_dict)
                tasks.append(task)
            except Exception as e:
                print(f"[WARNING] Task parsing error: {e}")
                continue
        
        summary = llm_response.get("summary", "오늘의 추천 일정입니다.")
        
        return TodayPlanResponse(
            tasks=tasks,
            summary=summary,
            source_date=yesterday_data["search_date"],
            owner=request.owner
        )
    
    def _build_user_prompt(
        self,
        today: date,
        owner: str,
        unresolved: list,
        next_day_plan: list,
        tasks: list = None,
        similar_tasks: List[UnifiedSearchResult] = None
    ) -> str:
        """
        사용자 프롬프트 구성
        
        Args:
            today: 오늘 날짜
            owner: 작성자
            unresolved: 미종결 업무 목록 (PostgreSQL에서)
            next_day_plan: 익일 계획 목록 (PostgreSQL에서)
            tasks: 전날 수행한 작업 목록 (PostgreSQL에서)
            similar_tasks: 유사 업무 패턴 (VectorDB에서, 선택적)
            
        Returns:
            구성된 프롬프트
        """
        # 미종결 업무 포맷팅
        unresolved_text = "\n".join([f"- {item}" for item in unresolved]) if unresolved else "없음"
        
        # 익일 계획 포맷팅
        next_day_plan_text = "\n".join([f"- {item}" for item in next_day_plan]) if next_day_plan else "없음"
        
        # 전날 작업 포맷팅
        tasks_text = "\n".join([f"- {item}" for item in (tasks or [])]) if tasks else "없음"
        
        # 🔥 VectorDB에서 가져온 유사 업무 패턴 포맷팅
        similar_tasks_text = "없음"
        if similar_tasks:
            # task 타입 청크만 필터링하여 업무 패턴 추출
            task_patterns = []
            for result in similar_tasks[:5]:  # 상위 5개만
                if result.chunk_type == "task":
                    task_patterns.append(f"- {result.text}")
            
            if task_patterns:
                similar_tasks_text = "\n".join(task_patterns)
        
        prompt = f"""날짜: {today.isoformat()}
작성자: {owner}

【전날 수행한 작업】 (PostgreSQL)
{tasks_text}

【전날 미종결 업무】 (PostgreSQL)
{unresolved_text}

【전날 익일 계획】 (PostgreSQL)
{next_day_plan_text}

【과거 유사 업무 패턴】 (VectorDB 참고용)
{similar_tasks_text}

위 정보를 바탕으로 오늘 하루 추천 일정을 JSON 형식으로 생성해주세요.
- 전날 미종결 업무가 있으면 우선적으로 포함
- 미종결 업무가 적거나 없으면 과거 유사 업무 패턴을 참고하여 추천
- 전날 수행한 작업의 연속성과 익일 계획을 고려하여 구체적인 일정을 만들어주세요.
"""
        
        return prompt

