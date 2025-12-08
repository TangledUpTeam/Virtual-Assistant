"""
Report Main Router Agent

Single prompt entry point for all report-related workflows.
Routes user requests to planning, generation, or RAG logic while keeping
every LLM prompt centralized in this module.
"""

from typing import Any, Dict, Optional
from datetime import date, timedelta

from multi_agent.agents.report_base import ReportBaseAgent
from app.llm.client import LLMClient


class ReportPromptRegistry:
    """
    Central registry for all report-related LLM prompts.

    Unified structure:
    - SYSTEM_PROMPT: global guardrails
    - INTENT_PROMPT: classification instructions
    - DOMAIN_GUIDANCE: per-domain guidance (planning/report/rag)
    - ROUTING_INSTRUCTION: delegation guidance
    """

    SYSTEM_PROMPT = (
        "You are the routing brain for all report workflows. Follow the rules, keep outputs deterministic, "
        "and only use the provided tools or sub-agents. Do not invent new actions."
    )

    ROUTING_INSTRUCTION = (
        "Decide which report sub-agent to run (planning/report/rag), describe the rationale, "
        "and provide the minimal inputs required. Always keep context consistent."
    )

    INTENT_PROMPT = """당신은 사용자의 요청을 분석하여 적절한 에이전트로 라우팅하는 전문가입니다.

아래 3가지 에이전트 중 선택하세요:
1. **planning**: 업무 플래닝/오늘 할 일 추천, 일정 관련
2. **report**: 보고서 생성/작성 (일일/주간/월간)
3. **rag**: 과거 업무 이력 검색·조회 (보고서 기반 QA)

반드시 JSON 형식으로만 답변하세요:
{
  "intent": "planning|report|rag|unknown",
  "confidence": 0.0 ~ 1.0,
  "reason": "선택 이유"
}
"""
    INTENT_USER_TEMPLATE = "사용자 요청: {query}"

    TASK_PARSER_SYSTEM = """당신은 업무 기록을 구조화하는 AI입니다.

사용자의 자연어 업무 설명을 분석하여 다음을 추출하세요:
- title: 업무 제목 (간단명료)
- description: 상세 설명
- category: 업무 카테고리
- time_range: 시간대 (그대로 유지)

카테고리 분류 규칙:
- 고객과의 대화, 계약 관련 업무 ⇒ "고객 대화"
- 문서 처리, 자료 처리, CRM 관리 ⇒ "문서 업무"  
- 회의, 미팅, 교육 ⇒ "회의/교육"
- 분석, 리서치 ⇒ "기획"
- 협업, 공용, 행정 ⇒ "협업"

주의사항:
- 회사 기본 상품명이면 그대로 적지 말고, 업무와 직접적인 역할 기반으로 분류하세요.
- 형식/순서는 자유지만 최소 정보는 포함하세요.

반드시 JSON 형식으로만 답변하세요:
{
  "title": "업무 제목",
  "description": "상세 설명",
  "category": "카테고리",
  "time_range": "시간대"
}
"""
    TASK_PARSER_USER_TEMPLATE = """시간대: {time_range}
업무 내용: {text}

위 업무를 분석하여 JSON으로 변환해주세요."""

    PLAN_SYSTEM_PROMPT = """너는 AI 업무 플래너이다.

**우선순위 원서**:
1. **내일 완성해야 할 업무 계획(next_day_plan) - 최우선*** (내일 마감이라면 필수)
2. **미종결업무(unresolved)** (2순위)
3. **최근 5일간 미완료 업무(similar_tasks)에서 미완료된 업무** (3순위)

규칙:
1. **최소 3개 이상 업무를 반드시 작성** (매우 중요!)
2. **당일 업무 계획은최우선*: 내일 완성해야 할 업무 계획을반드시 포함 (내일 마감이라면 필수)
3. **미종결업무**: 내일 미종결업무가 있으면2순위로 포함
4. **미완료업무분석*: 최근 5일간 있었던 미종결업무 다음에 올릴 업무만을 포함하여 제공해야 함
5. **반복 업무 우선 추천*: 최근 5일간 여러 번 발생한 업무 유형/고객/카테고리
6. **긴급히 할 일 우선**: 
   - 고객 상담 관련 업무 (현재 진행 중인 고객)
   - 계약/보장 관련 업무
   - 마감이 임박한 업무
7. **우선순위가 높은 카테고리**: "고객 상담" > "계약 처리" > "문서 업무" > 기획
8. **오늘 배치 가능한 업무**: 구체적이어야 하고 계획 가능해야 함
9. 최근 업무 로그가 부족할 경우 부분적인 업무 추천:
   - 고객 연락 연락
   - 기존 고객 관계/계약 검토
   - 신규 고객 발견 연락 준비
   - 제품 정보 숙지 업무
   - 보고서 작성/문서 처리
10. 우선순위: high(긴급/중요), medium(보통), low(여유)
11. 예상 시간: "30분", "1시간", "2시간" 등
12. 카테고리: "고객 상담", "계약 처리", "문서 작업", "기획", "기술" 등

**중요**: 
- **내일 업무 계획은최우선*이며, 반드시반드시 포함해야 함(내일 마감이라면 필수)
- 활용된 최근 5일간 미완료 업무 텍스트만 포함하고, 그 외 다른 업무는 제외
- 미완료 반복, 긴급 우선순위 카테고리, 배치 가능성을 기준으로 추천
- 업무가 3개 미만이면 부족한 개수만큼 기본 업무를 채워야 합니다.

반드시 JSON 형식으로 답변:
{
  "tasks": [
    {
      "title": "업무 제목",
      "description": "업무 설명",
      "priority": "high|medium|low",
      "expected_time": "예상 시간",
      "category": "카테고리"
    }
  ],
  "summary": "오늘 일정 간단 요약 (1-2문장)"
}

중요: tasks 배열에는 최소 3개 이상의 작업을 포함해야 합니다.
"""

    PLAN_USER_TEMPLATE = """날짜: {today}
고객명: {owner}

이전날 수행업무(업무 로그):
{tasks_text}

이전날 내일 업무 계획(next_day_plan) - **최우선**
{next_day_plan_text}

이전날 미종결업무(unresolved) - **2순위**
{unresolved_text}

최근5일미완료업무(similar_tasks) (VectorDB) - **3순위**
{similar_tasks_text}

위 정보를 바탕으로 오늘 할 일 계획을 JSON 형식으로 작성하세요.

**출력조건**:
- 최소 3개 이상 업무를 반드시 작성
- 내일 업무 계획 포함 (내일 마감이라면 필수)
- 미종결/미완료 업무 우선 반영
- 반복/긴급/우선순위 카테고리 고려, 배치 가능성 고려"""

    RAG_SYSTEM_PROMPT = (
        "주어진일일 보고서 청크만 사용하여 사용자의 질문에 답변하세요. "
        "문장이 없는 경우 청크가 없다고 명시하세요."
    )
    RAG_USER_TEMPLATE = "질문: {query}\n\n청크:\n{context}"

    WEEKLY_REPORT_SYSTEM = """당신은 일일보고서를 기반으로 주간보고서를 작성하는 지시서입니다.

## 입력 데이터
ChromaDB에서 검색된 일일보고서 청크 배열이 주어집니다.
각 청크는 다음 형식입니다:
{
  "text": "[일일_SUMMARY] 2025-11-24\\n1. 업무1\\n2. 업무2...",
  "metadata": {
    "date": "2025-11-24",
    "level": "daily",
    "chunk_type": "summary | detail | pending | plan",
    "week": "2025-W48",
    "month": "2025-11",
    "owner": "작성자이름"
  }
}

검색조건: week = "{week_number}", level = "daily"
총 20개청크가 제공됩니다.

## 주간보고서 작성 규칙

### 1. 주간 업무 목표 (weekly_goals)
- chunk_type="summary"의 5개청크를 분석
- 반복되는 업무 방향/주제를 추천
- 3개의 주간 목표를 요약
- 각 목표는 구조적이고 간결하게 작성

예시:
- "이번 주 고객 상담에서 발생하는 보장이슈 5건을 기준으로 보장안을 5건구성하고, 고객에게 매칭하여 제안하도록 한다."
- "보험 리모델링 제안을 위해 고객 2곳진행하고, 이를 통해 고객에게 맞춤 서비스 제공한다."

### 2. 월요일~금요일 업무 (weekday_tasks)
- chunk_type="detail"의 5개청크를 date 기준으로 분류
- **반드시 해당 주의 월요일~금요일 5일 모두 포함** ("2025-11-03", "2025-11-04", "2025-11-05", "2025-11-06", "2025-11-07")
- 날짜는 YYYY-MM-DD 형식으로 통일
- 각 날짜별로 업무 3개이상을 요약 (배열이어도 무방)
- 시간 정보(예: [09:00-10:00])가 있으면 유지하고 업무 내용만 추출
- 업무 내용은 간결하고 구체적으로 작성

출력 형식:
{
  "2025-11-03": ["업무1", "업무2", "업무3"],
  "2025-11-04": ["업무1", "업무2", "업무3"],
  "2025-11-05": ["업무1", "업무2", "업무3"],
  "2025-11-06": ["업무1", "업무2", "업무3"],
  "2025-11-07": ["업무1", "업무2", "업무3"]
}

### 3. 주간 중요 업무 (weekly_highlights)
- chunk_type="pending"의 모든 청크를 분석
- 다음 키워드와 관련된 항목만 선별: "미종결", "지연", "콜백", "진행중", "미완료", "처리 못함"
- 반복적인 항목은 제거
- 3개이상 요약
- 각 항목은 구조화된 업무 문장으로 작성

### 4. 메모/비고 (notes)
- chunk_type="plan"의 청크 중 notes 성격 문장을 추출
- "메모:" 접두어를 활용
- 고객 반응, 컴플레인, 콜백 요청 사항을 중심으로 기록
- 여러 날짜의 메모를 하나로 합치지 말고 문단으로 구분

## 출력 형식
아래 JSON 형식으로만 출력하세요. 불필요한 텍스트는 넣지 마세요.

{
  "weekly_goals": [
    "목표1",
    "목표2",
    "목표3"
  ],
  "weekday_tasks": {
    "2025-11-03": ["업무1", "업무2", "업무3"],
    "2025-11-04": ["업무1", "업무2", "업무3"],
    "2025-11-05": ["업무1", "업무2", "업무3"],
    "2025-11-06": ["업무1", "업무2", "업무3"],
    "2025-11-07": ["업무1", "업무2", "업무3"]
  },
  "weekly_highlights": [
    "중요 업무1",
    "중요 업무2",
    "중요 업무3"
  ],
  "notes": "메모 문단"
}

## 중요 규칙
1. 제공된검색결과만을 근거로 작성하세요. 추측은 금지합니다.
2. JSON만 출력하세요. 다른 텍스트는 금지합니다.
3. 날짜는 YYYY-MM-DD 형식만 사용하세요.
4. 배열이나 문자열이어도 동일한 필드는 모두 반환하세요.
"""

    MONTHLY_REPORT_SYSTEM = """당신은 주간보고서와 일일보고서 청크를 기반으로 월간보고서를 작성하는 지시서입니다.

## 입력 데이터

### 1. 주간보고서 JSON (4개)
해당 월의 주간보고서 4개가 제공됩니다.
[
  {
    "weekly_goals": [...],
    "weekday_tasks": {...},
    "weekly_highlights": [...],
    "notes": "..."
  },
  ...
]

### 2. 일일보고서 청크 (선택)
해당 월의 일일보고서 청크 전체가 제공될 수 있습니다(4청크 × 날짜수).
각 청크는 다음 형식입니다:
{
  "text": "[일일_DETAIL] 2025-11-01\\n...",
  "metadata": {
    "date": "2025-11-01",
    "chunk_type": "summary | detail | pending | plan",
    "month": "2025-11"
  }
}

### 3. 월간 KPI 원시 JSON (선택)
PostgreSQL에서 조회한 월간 KPI 원시 데이터입니다.
{
  "total_customers": 10,
  "new_contracts": 5,
  "renewals": 3,
  ...
}

## 월간보고서 작성 규칙

### 1. 월간 핵심 지표
- KPI JSON의 숫자 값만 사용하세요. 별도 추론/보정 없이 작성합니다.
- 값이 없으면 필드를 생략합니다.
- 변화 추세, 원인 분석 등을 간결하게 작성합니다.
- 주간보고서의 weekly_highlights를 참고하여 업무 성과와 연결하세요.

출력 예시:
{
  "key_metrics": {
    "total_customers": 10,
    "new_contracts": 5,
    "renewals": 3,
    "analysis": "이번 주간 계약 5건을 달성하였고, 전월 대비 20% 증가했습니다. 주요 원인은..."
  }
}

### 2. 주차별 업무 요약 (weekly_summaries)
- 주간보고서 4개를 기반으로 "주차 요약" 중심으로 작성
- 일일 DETAIL 청크를 보강자료로만 사용 (필수는 아님)
- 각 주차별로 핵심 업무 흐름과 변화를 3~5줄 내외로 작성
- 날짜 기반으로 주차를 나누되, 1~4주차 키를 유지하세요.

출력 예시:
{
  "1주차": [
    "주요 업무 요약 1",
    "주요 업무 요약 2",
    "주요 업무 요약 3"
  ],
  "2주차": [...],
  "3주차": [...],
  "4주차": [...]
}

### 3. 차기 계획 (next_month_plan)
- 해당 월의 PLAN_NOTE 청크에서 미래지향 계획을 추출
- 다음 키워드를 우선 탐색: "다음 달", "향후", "내달", "리텐션", "계획", "예정"
- 반복되는 요약문이라도 3~5개의 계획으로 도출
- 각 계획은 구조적이고 실행 가능하도록 작성

출력 예시:
{
  "next_month_plan": "1. 다음 달 주요 고객 상담 10건 목표, 신규 고객 발굴 자동화 도구 적용\n2. 기존 고객 리텐션을 위한 패키지 제공 계획 수립\n3. 맞춤형 상담 스크립트 개편..."
}

## 출력 형식
아래 JSON 형식으로만 출력하세요. 불필요한 텍스트는 넣지 마세요.

{
  "key_metrics": {
    "total_customers": 10,
    "new_contracts": 5,
    "renewals": 3,
    "analysis": "분석 텍스트"
  },
  "weekly_summaries": {
    "1주차": ["요약1", "요약2", "요약3"],
    "2주차": ["요약1", "요약2", "요약3"],
    "3주차": ["요약1", "요약2", "요약3"],
    "4주차": ["요약1", "요약2", "요약3"]
  },
  "next_month_plan": "차기 계획 요약 텍스트"
}

## 중요 규칙
1. 제공된 데이터만을 근거로 작성하세요. 추측은 금지합니다.
2. JSON만 출력하세요. 다른 텍스트는 금지합니다.
3. KPI 숫자는 원본 값 그대로 사용하세요.
4. 주간보고서 중심으로 작성하고, 일일 청크는 보강 자료로만 사용하세요.
5. 배열/문자열 필드는 비어 있어도 반드시 포함하세요.
"""

    VISION_DETECT_SYSTEM = "너는 문서 종류별로 분류하는 AI야."
    VISION_DETECT_USER = """어떤 문서가 주어진 보고서인지 판단해라.
반드시 정해진 셋에서만 대답해라.

daily / weekly / monthly

위에서 택일해라.
"""

    VISION_EXTRACT_SYSTEM = "너는 PDF를 JSON 포맷으로 변환하는 도우미 AI야."
    VISION_EXTRACT_USER_TEMPLATE = """PDF 내용을 JSON 스키마에 정확히 채워 넣어.

규칙:
1) 필드 계층, 구조 유지
2) 값 누락 금지
3) 코드 블록 없음
4) OCR로 추출한 값만 채우기
5) JSON만 출력

스키마
{schema}
"""

    @classmethod
    def intent_system(cls) -> str:
        return f"{cls.SYSTEM_PROMPT}\n\n{cls.ROUTING_INSTRUCTION}\n\n{cls.INTENT_PROMPT}"

    @classmethod
    def intent_user(cls, query: str) -> str:
        return cls.INTENT_USER_TEMPLATE.format(query=query)

    @classmethod
    def task_parser_system(cls) -> str:
        return cls.TASK_PARSER_SYSTEM

    @classmethod
    def task_parser_user(cls, time_range: str, text: str) -> str:
        return cls.TASK_PARSER_USER_TEMPLATE.format(time_range=time_range, text=text)

    @classmethod
    def plan_system(cls) -> str:
        return cls.PLAN_SYSTEM_PROMPT

    @classmethod
    def plan_user(
        cls,
        today: date,
        owner: str,
        tasks_text: str,
        next_day_plan_text: str,
        unresolved_text: str,
        similar_tasks_text: str,
    ) -> str:
        return cls.PLAN_USER_TEMPLATE.format(
            today=today.isoformat(),
            owner=owner,
            tasks_text=tasks_text,
            next_day_plan_text=next_day_plan_text,
            unresolved_text=unresolved_text,
            similar_tasks_text=similar_tasks_text,
        )

    @classmethod
    def rag_system(cls) -> str:
        return cls.RAG_SYSTEM_PROMPT

    @classmethod
    def rag_user(cls, query: str, context: str) -> str:
        return cls.RAG_USER_TEMPLATE.format(query=query, context=context)

    @classmethod
    def weekly_system(cls, week_number: str) -> str:
        return cls.WEEKLY_REPORT_SYSTEM.format(week_number=week_number)

    @classmethod
    def weekly_user(cls, search_results_json: str, monday: date, friday: date) -> str:
        return (
            "다음은 ChromaDB에서 검색된 일일보고서 청크 데이터입니다:\n\n"
            f"{search_results_json}\n\n"
            "위 데이터를 기반으로 주간보고서를 생성해주세요.\n\n"
            f"중요:\n"
            f"- 주간 기간: {monday.isoformat()} ~ {friday.isoformat()}\n"
            "- weekday_tasks는 반드시 월~금 5일 모두 포함\n"
            f'- 날짜 키 예시: \"{monday.isoformat()}\", \"{(monday + timedelta(days=1)).isoformat()}\", '
            f'\"{(monday + timedelta(days=2)).isoformat()}\", \"{(monday + timedelta(days=3)).isoformat()}\", '
            f'\"{friday.isoformat()}\"\n'
            "- chunk_type='detail' 청크에서 업무를 3개 이상 추천\n"
            "- 업무가 없으면 빈 배열([])로 반환"
        )

    @classmethod
    def monthly_system(cls) -> str:
        return cls.MONTHLY_REPORT_SYSTEM

    @classmethod
    def monthly_user(
        cls,
        weekly_reports_json: str,
        daily_chunks_json: str,
        kpi_json: str,
        month_str: str,
    ) -> str:
        return (
            f"다음은 해당 월({month_str})의 데이터입니다:\n\n"
            f"### 주간보고서 JSON (4개):\n{weekly_reports_json}\n\n"
            f"### 일일보고서 청크:\n{daily_chunks_json}\n\n"
            f"### 월간 KPI 원시 JSON:\n{kpi_json}\n\n"
            "위 데이터를 기반으로 월간보고서를 JSON으로 작성하세요."
        )

    @classmethod
    def vision_detect_messages(cls, images_base64: list) -> list:
        return [
            {"role": "system", "content": [{"type": "text", "text": cls.VISION_DETECT_SYSTEM}]},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": cls.VISION_DETECT_USER},
                    *[{"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img}"}} for img in images_base64],
                ],
            },
        ]

    @classmethod
    def vision_extract_messages(cls, images_base64: list, schema: str) -> list:
        return [
            {"role": "system", "content": [{"type": "text", "text": cls.VISION_EXTRACT_SYSTEM}]},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": cls.VISION_EXTRACT_USER_TEMPLATE.format(schema=schema)},
                    *[{"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img}"}} for img in images_base64],
                ],
            },
        ]


class ReportMainRouterAgent(ReportBaseAgent):
    """ReportMainRouterAgent - Intent Classification + routing with centralized prompts."""

    INTENT_PLANNING = "planning"
    INTENT_REPORT = "report"
    INTENT_RAG = "rag"
    INTENT_UNKNOWN = "unknown"

    def __init__(self, llm_client: Optional[LLMClient] = None):
        super().__init__(
            name="ReportMainRouterAgent",
            description="사용자 요청을 분석하여 적절한 보고 관련 하위 에이전트로 라우팅하는 메인 에이전트입니다.",
            llm_client=llm_client,
        )
        self.prompt_registry = ReportPromptRegistry
        self._planning_agent = None
        self._report_agent = None
        self._rag_agent = None

    @property
    def planning_agent(self):
        if self._planning_agent is None:
            from multi_agent.agents.report_tools import get_planning_agent

            self._planning_agent = get_planning_agent()
            if hasattr(self._planning_agent, "configure_prompts"):
                self._planning_agent.configure_prompts(self.prompt_registry)
        return self._planning_agent

    @property
    def report_agent(self):
        if self._report_agent is None:
            from multi_agent.agents.report_tools import get_report_generation_agent

            self._report_agent = get_report_generation_agent()
            if hasattr(self._report_agent, "configure_prompts"):
                self._report_agent.configure_prompts(self.prompt_registry)
        return self._report_agent

    @property
    def rag_agent(self):
        if self._rag_agent is None:
            from multi_agent.agents.report_tools import get_report_rag_agent

            self._rag_agent = get_report_rag_agent()
            if hasattr(self._rag_agent, "configure_prompts"):
                self._rag_agent.configure_prompts(self.prompt_registry)
        return self._rag_agent

    def _classify_intent_by_rule(self, query: str) -> Optional[str]:
        query_lower = query.lower()

        planning_keywords = [
            "오늘",
            "업무",
            "플래닝",
            "계획",
            "일정",
            "추천",
            "조정",
            "today",
            "plan",
            "planning",
            "schedule",
            "todo",
        ]

        report_keywords = [
            "보고서",
            "작성",
            "생성",
            "일일",
            "주간",
            "월간",
            "report",
            "daily",
            "weekly",
            "monthly",
            "generate",
        ]

        rag_keywords = [
            "조회",
            "찾아",
            "검색",
            "있었",
            "미종결",
            "고객",
            "주소",
            "번주",
            "이번주",
            "지난주",
            "이번달",
            "지난달",
            "이번해",
            "last week",
            "last month",
            "last year",
            "unresolved",
        ]

        if any(kw in query_lower for kw in planning_keywords):
            if any(kw in query_lower for kw in ["추천", "계획", "플랜", "일정"]):
                return self.INTENT_PLANNING

        if any(kw in query_lower for kw in report_keywords):
            return self.INTENT_REPORT

        if any(kw in query_lower for kw in rag_keywords):
            return self.INTENT_RAG

        return None

    async def _classify_intent_by_llm(self, query: str) -> str:
        system_prompt = self.prompt_registry.intent_system()
        user_prompt = self.prompt_registry.intent_user(query)

        try:
            result = await self.llm.acomplete_json(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.3,
                max_tokens=200,
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
        intent = self._classify_intent_by_rule(query)

        if intent:
            print(f"[INFO] Rule-based Intent: {intent}")
            return intent

        intent = await self._classify_intent_by_llm(query)

        return intent

    async def process(self, query: str, context: Optional[Dict[str, Any]] = None) -> str:
        intent = await self.classify_intent(query)

        print(f"[INFO] ReportMainRouterAgent - Intent: {intent}, Query: {query}")

        enriched_context = context or {}
        enriched_context["prompt_registry"] = self.prompt_registry

        try:
            if intent == self.INTENT_PLANNING:
                return await self.planning_agent.process(query, enriched_context)

            if intent == self.INTENT_REPORT:
                return await self.report_agent.process(query, enriched_context)

            if intent == self.INTENT_RAG:
                return await self.rag_agent.process(query, enriched_context)

            return "죄송합니다. 요청을 이해하지 못했습니다. 업무 플래닝, 보고서 생성, 혹은 과거 업무 검색 중에서 말씀해 주세요."

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
        **kwargs,
    ) -> Dict[str, Any]:
        intent = await self.classify_intent(query)

        context = {
            "owner": owner,
            "target_date": target_date or date.today(),
            **kwargs,
        }

        response = await self.process(query, context)

        return {
            "intent": intent,
            "agent": intent,
            "response": response,
            "context": context,
        }
