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
    Prompts are intentionally lightweight to avoid over-constraining the LLM.
    """

    # ========================================
    # 1. 라우팅 및 의도 분류 프롬프트
    # ========================================

    SYSTEM_PROMPT = (
        "You route user requests to one of the report agents. "
        "Use simple reasoning. Do not force rigid rules. "
        "Your job is to classify the user intent into one of: "
        "lookup (RAG search), report_write, planning, or other."
    )

    ROUTING_INSTRUCTION = (
        "Decide which report sub-agent to run (planning/report/rag), describe the rationale, "
        "and provide the minimal inputs required. Always keep context consistent."
    )

    INTENT_PROMPT = """사용자의 요청을 아래 네 가지 중 하나로 분류하세요:

1) lookup  
   - 과거 보고서 기반 조회  
   - '누구', '언제', '무엇을 했었는지', '미종결', '조회', '검색', '찾아' 등  
   - 날짜/고객/업무 내용 회상, 확인, 탐색

2) report_write  
   - 일일/주간/월간 보고서 생성 또는 수정  
   - '보고서 작성', '일일보고서', '주간보고서', '정리해줘'

3) planning  
   - 오늘 할 일 추천, 일정 계획  
   - '오늘 할 일', '업무 추천', '플랜', '계획', '일정'

4) other  
   - 위에 해당하지 않는 일반 대화

너무 엄격한 규칙을 적용하지 말고, 자연스럽고 직관적으로 판단하세요.

출력은 반드시 다음 JSON 형식:
{
  "intent": "lookup | report_write | planning | other",
  "confidence": 0.0 ~ 1.0,
  "reason": "왜 그렇게 판단했는지 간단히"
}
"""
    INTENT_USER_TEMPLATE = "사용자 요청: {query}"

    # ========================================
    # 2. 업무 플래닝 프롬프트
    # ========================================

    PLAN_SYSTEM_PROMPT = """당신은 사용자의 하루 업무 계획을 추천하는 AI 업무 플래너입니다.

당신의 목표는 "오늘 수행할 업무를 3개 추천"하는 것입니다.

사용 가능한 입력 데이터:
1) 익일(next_day_plan): 전날 보고서에서 사용자가 직접 적어둔 내일 할 일 (최우선)
2) 미종결(unresolved): 어제 처리되지 못한 업무 (2순위)
3) 최근 3일 세부 업무 기록(similar_tasks): 사용자의 반복 업무 패턴 (보조 자료)
4) 추가 업무 추천이 필요한 경우에만 ChromaDB 데이터를 사용

업무 추천 규칙:
- 반드시 3개 추천
- next_day_plan → unresolved → similar_tasks 우선순위
- 고객 이름 포함된 항목은 제외
- title/description/priority/category/expected_time 포함

출력은 반드시 JSON 형식:
{
  "tasks": [ {
      "title": "업무 제목",
      "description": "업무 설명",
      "priority": "high|medium|low",
      "expected_time": "예상 시간",
      "category": "카테고리"
    }],
  "summary": "오늘 일정 요약"
}
"""

    PLAN_USER_TEMPLATE = """날짜: {today}
고객명: {owner}

이전날 수행업무(업무 로그):
{tasks_text}

이전날 내일 업무 계획(next_day_plan) - **최우선**
{next_day_plan_text}

이전날 미종결업무(unresolved) - **2순위**
{unresolved_text}

최근3일업무기록(similar_tasks) (VectorDB) - **3순위**
{similar_tasks_text}

위 정보를 바탕으로 오늘 할 일 계획을 JSON 형식으로 작성하세요.
"""

    # ========================================
    # 3. 일일보고서 작성 프롬프트
    # ========================================

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

    # ========================================
    # 4. 보고서 검색 (RAG) 프롬프트
    # ========================================

    RAG_SYSTEM_PROMPT = """당신은 일일보고서 데이터를 기반으로 사용자의 질문에 답변하는 AI 어시스턴트입니다.

**답변 규칙:**
1. 주어진 청크(일일보고서 데이터)만 사용하여 답변하세요.
2. 청크에 관련 정보가 있으면 반드시 그 내용을 바탕으로 구체적으로 답변하세요.
3. 청크에 날짜 정보가 있으면 해당 날짜를 명시하세요.
4. 여러 청크가 있으면 모두 종합하여 답변하세요.
5. 청크에 정확한 정보가 없거나 관련성이 전혀 없을 때만 "해당 기간의 정보를 찾을 수 없습니다"라고 답변하세요.

**중요:** 청크가 제공되었으면 반드시 그 내용을 바탕으로 답변을 생성하세요. "청크가 없습니다"라고 답변하지 마세요."""
    RAG_USER_TEMPLATE = "질문: {query}\n\n청크:\n{context}"

    # ========================================
    # 5. 주간보고서 작성 프롬프트
    # ========================================

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

검색조건: week = "{week_number_placeholder}", level = "daily"
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
- **중요 규칙**:
  * 시간 정보(예: [09:00-10:00])는 **반드시 제거**하고 업무 내용만 추출
  * 고객 이름은 **반드시 제거**하고 업무 내용만 작성
  * 예: "[09:00-10:00] 박서연 고객 상담 자료 정리" → "상담 자료 정리"
  * 예: "[10:00-11:00] 김태은 고객 보장 점검" → "보장 점검"
- 업무 내용은 간결하고 구체적으로 작성 (고객명 없이)

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
- **중요 규칙**:
  * **고객 이름은 반드시 제거**하고 업무 내용만 작성
  * **반복적으로 나타나는 업무 패턴만 추출** (3개)
  * 예: "문은가 고객 추가 자료 대기" → "추가 자료 대기"
  * 예: "박이린 고객 상담 자료 정리 필요" → "상담 자료 정리"
  * 동일한 업무 패턴이 여러 고객에 대해 반복되면 하나로 통합
- 각 항목은 구조화된 업무 문장으로 작성 (고객명 없이)

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

    # ========================================
    # 6. 월간보고서 작성 프롬프트
    # ========================================

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
### [중요] 월간 KPI 자동 집계 규칙

주간보고서, 일일보고서(detail/pending/plan 청크)를 분석하여 아래 3가지 KPI를 계산하세요.
숫자 값은 반드시 청크에 존재하는 텍스트를 기반으로 “직접 카운트”해야 하며, 추론하거나 생성하면 안 됩니다.

1) 신규 계약 건수(new_contracts)
- 아래 키워드가 포함된 업무가 등장할 때마다 +1
  키워드: ["신규 리드", "신규 계약", "신규", "신규고객", "신규 리드 생성"]
- 고객 이름 포함 여부와 무관하게 키워드만으로 카운트

2) 유지 계약 건수(renewals)
- 아래 키워드가 포함된 업무가 등장할 때마다 +1
  키워드: ["유지 계약", "유지", "갱신", "리텐션"]
- 단순 “유지보수”, “유지 관리”와 같은 단어는 제외

3) 상담 진행 건수(consultations)
- 아래 키워드가 포함된 업무가 등장할 때마다 +1
  키워드: ["상담", "상담진행", "상담 진행", "상담 예약"]
- “콜백 요청”, “문의”는 상담으로 계산하지 않음

### KPI 출력 규칙
- 없는 데이터는 0으로 계산
- 계산 근거는 보고서 청크의 실제 텍스트만 사용
- 분석 결과는 아래와 같은 JSON에 포함:

{
  "key_metrics": {
    "new_contracts": <정수>,
    "renewals": <정수>,
    "consultations": <정수>,
    "analysis": "핵심 지표 요약 분석"
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

    # ========================================
    # 7. Vision (PDF 처리) 프롬프트
    # ========================================

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
        return cls.WEEKLY_REPORT_SYSTEM.replace("{week_number_placeholder}", week_number)

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
    INTENT_REPORT = "report_write"  # 프롬프트에서 사용하는 값과 일치
    INTENT_RAG = "lookup"  # 프롬프트에서 사용하는 값과 일치
    INTENT_UNKNOWN = "other"  # 프롬프트에서 사용하는 값과 일치

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
            from multi_agent.tools.report_tools import get_planning_agent

            self._planning_agent = get_planning_agent()
            if hasattr(self._planning_agent, "configure_prompts"):
                self._planning_agent.configure_prompts(self.prompt_registry)
        return self._planning_agent

    @property
    def report_agent(self):
        if self._report_agent is None:
            from multi_agent.tools.report_tools import get_report_generation_agent

            self._report_agent = get_report_generation_agent()
            if hasattr(self._report_agent, "configure_prompts"):
                self._report_agent.configure_prompts(self.prompt_registry)
        return self._report_agent

    @property
    def rag_agent(self):
        if self._rag_agent is None:
            from multi_agent.tools.report_tools import get_report_rag_agent

            self._rag_agent = get_report_rag_agent()
            if hasattr(self._rag_agent, "configure_prompts"):
                self._rag_agent.configure_prompts(self.prompt_registry)
        return self._rag_agent

    def _classify_intent_by_rule(self, query: str) -> Optional[str]:
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
            # intent 값 정규화 (공백 제거, 소문자 변환)
            intent_normalized = str(intent).strip().lower() if intent else ""
            
            # 디버깅: intent 값과 상수 값 확인
            print(f"[DEBUG] Intent 원본: '{intent}' (type: {type(intent)})")
            print(f"[DEBUG] Intent 정규화: '{intent_normalized}'")
            print(f"[DEBUG] INTENT_RAG 상수: '{self.INTENT_RAG}'")
            print(f"[DEBUG] INTENT_PLANNING 상수: '{self.INTENT_PLANNING}'")
            print(f"[DEBUG] INTENT_REPORT 상수: '{self.INTENT_REPORT}'")
            
            # RAG/lookup을 먼저 체크 (질문형 쿼리 우선)
            if (intent == self.INTENT_RAG or intent == "lookup" or 
                intent_normalized == "lookup" or intent_normalized == self.INTENT_RAG.lower()):
                print(f"[DEBUG] ✅ RAG 에이전트로 라우팅")
                return await self.rag_agent.process(query, enriched_context)

            # LLM이 반환한 intent를 내부 상수로 매핑 (프롬프트 값과 코드 값 호환)
            if (intent == self.INTENT_PLANNING or intent == "planning" or 
                intent_normalized == "planning" or intent_normalized == self.INTENT_PLANNING.lower()):
                print(f"[DEBUG] ✅ Planning 에이전트로 라우팅")
                return await self.planning_agent.process(query, enriched_context)

            if (intent == self.INTENT_REPORT or intent == "report_write" or 
                intent_normalized == "report_write" or intent_normalized == self.INTENT_REPORT.lower()):
                print(f"[DEBUG] ✅ Report 에이전트로 라우팅")
                return await self.report_agent.process(query, enriched_context)

            print(f"[DEBUG] ❌ 알 수 없는 인텐트: '{intent}' (정규화: '{intent_normalized}')")
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
