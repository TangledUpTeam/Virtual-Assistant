# Backend 파일 구조 및 경로 연결 상태

## 📁 전체 폴더 구조

```
backend/
├── app/                                    # 메인 애플리케이션
│   ├── api/v1/                            # API 엔드포인트
│   │   ├── endpoints/
│   │   │   ├── report/                    # 📊 보고서 관련 엔드포인트 (정리됨)
│   │   │   │   ├── __init__.py
│   │   │   │   ├── daily.py              # 일일 보고서 FSM
│   │   │   │   ├── daily_report.py       # 일일 보고서 CRUD
│   │   │   │   ├── weekly_report.py      # 주간 보고서
│   │   │   │   ├── monthly_report.py     # 월간 보고서
│   │   │   │   ├── pdf_export.py         # PDF 내보내기
│   │   │   │   ├── plan.py               # 업무 플래닝
│   │   │   │   ├── report_chat.py        # 보고서 RAG 챗봇
│   │   │   │   └── reports.py            # 보고서 처리
│   │   │   ├── auth.py                   # 인증
│   │   │   ├── users.py                  # 사용자
│   │   │   ├── rag.py                    # RAG (HR/Insurance)
│   │   │   ├── brainstorming.py          # 브레인스토밍
│   │   │   ├── chatbot.py                # 챗봇
│   │   │   ├── therapy.py                # 심리상담
│   │   │   ├── multi_agent.py            # 멀티 에이전트
│   │   │   └── agent_router.py           # 보고서 Agent 시스템
│   │   └── router.py                      # ✅ 모든 엔드포인트 라우팅
│   │
│   ├── core/                              # 핵심 설정
│   │   ├── config.py                      # ✅ 설정 (extra="ignore" 추가됨)
│   │   └── security.py                    # 보안 (JWT)
│   │
│   ├── domain/                            # 비즈니스 로직
│   │   ├── auth/                          # 인증
│   │   ├── user/                          # 사용자
│   │   ├── report/                        # 📊 보고서 도메인 (핵심)
│   │   │   ├── core/                      # 공통 기능
│   │   │   │   ├── canonical_converter.py
│   │   │   │   ├── canonical_models.py    # Canonical 스키마
│   │   │   │   ├── chunker.py             # 청킹 (4개 청크)
│   │   │   │   ├── embedding_pipeline.py
│   │   │   │   ├── rag_chain.py
│   │   │   │   ├── rag_prompts.py
│   │   │   │   ├── rag_service.py
│   │   │   │   ├── schemas.py
│   │   │   │   ├── service.py
│   │   │   │   └── utils_text.py
│   │   │   ├── daily/                     # 일일 보고서
│   │   │   │   ├── daily_builder.py
│   │   │   │   ├── daily_fsm.py          # FSM 로직
│   │   │   │   ├── fsm_state.py
│   │   │   │   ├── main_tasks_store.py
│   │   │   │   ├── models.py             # DB 모델
│   │   │   │   ├── repository.py
│   │   │   │   ├── schemas.py
│   │   │   │   ├── session_manager.py
│   │   │   │   ├── task_parser.py
│   │   │   │   └── time_slots.py
│   │   │   ├── weekly/                    # 주간 보고서
│   │   │   │   ├── chain.py
│   │   │   │   ├── models.py
│   │   │   │   ├── repository.py
│   │   │   │   └── schemas.py
│   │   │   ├── monthly/                   # 월간 보고서
│   │   │   │   ├── chain.py
│   │   │   │   ├── models.py
│   │   │   │   ├── repository.py
│   │   │   │   └── schemas.py
│   │   │   ├── planner/                   # 업무 플래닝
│   │   │   │   ├── schemas.py
│   │   │   │   ├── today_plan_chain.py
│   │   │   │   └── tools.py
│   │   │   └── search/                    # 검색 & RAG
│   │   │       ├── hybrid_search.py       # ✅ 하이브리드 검색
│   │   │       ├── intent_router.py
│   │   │       ├── retriever.py           # ✅ Unified Retriever
│   │   │       └── service.py
│   │   ├── rag/                           # RAG (HR/Insurance)
│   │   ├── brainstorming/                 # 브레인스토밍
│   │   ├── chatbot/                       # 챗봇
│   │   ├── therapy/                       # 심리상담
│   │   ├── slack/                         # Slack 연동
│   │   └── common/                        # 공통
│   │
│   ├── infrastructure/                    # 인프라
│   │   ├── database/
│   │   │   ├── __init__.py               # ✅ Circular import 방지
│   │   │   ├── base.py                   # ✅ Alembic용 (지연 import)
│   │   │   └── session.py                # SQLAlchemy 세션
│   │   ├── oauth/                        # OAuth (Google, Kakao, Naver, Notion)
│   │   ├── vector_store.py               # Vector DB (일반)
│   │   └── vector_store_report.py        # Vector DB (보고서)
│   │
│   ├── llm/                              # LLM 클라이언트
│   │   └── client.py
│   │
│   ├── reporting/                        # 보고서 렌더링
│   │   ├── html_generator/               # HTML 생성
│   │   ├── pdf_generator/                # PDF 생성
│   │   ├── html_renderer.py
│   │   └── service/
│   │       └── report_export_service.py
│   │
│   └── main.py                           # FastAPI 앱
│
├── debug/                                # 🧪 디버그 & 테스트
│   └── report/                           # 📊 보고서 테스트 (정리됨)
│       ├── __init__.py
│       ├── test_daily_fsm.py            # ✅ 일일 보고서 FSM
│       ├── test_weekly_chain.py         # ✅ 주간 보고서
│       ├── test_monthly_chain.py        # ✅ 월간 보고서
│       ├── test_today_plan_chain.py     # ✅ 업무 플래닝
│       ├── test_main_tasks_flow.py      # ✅ 메인 업무 플로우
│       ├── test_unified_search.py       # ✅ 통합 검색
│       ├── test_pdf_export.py           # ⚠️ PDF 내보내기 (PyPDF2 필요)
│       ├── check_daily_reports.py       # ✅ 일일 보고서 확인
│       ├── check_weekly_data.py         # ✅ 주간 데이터 확인
│       ├── check_yesterday_data.py      # ✅ 전날 데이터 확인
│       └── clear_daily_reports.py       # ✅ 일일 보고서 삭제
│
├── ingestion/                            # 데이터 수집
│   ├── embed.py                          # ✅ 임베딩 서비스 (HF/OpenAI)
│   ├── chroma_client.py
│   ├── auto_ingest.py
│   └── ingest_mock_reports.py
│
├── multi_agent/                          # 멀티 에이전트 시스템
├── tools/                                # 유틸리티 도구
├── Data/                                 # 데이터
├── output/                               # 출력 파일
└── alembic/                              # DB 마이그레이션
```

## ✅ Import 경로 연결 상태

### 1. API 엔드포인트 → Domain (정상)
```python
# endpoints/report/daily.py
from app.domain.report.daily.fsm_state import DailyFSMContext
from app.domain.report.daily.daily_fsm import DailyReportFSM
from app.domain.report.daily.daily_builder import build_daily_report

# endpoints/report/weekly_report.py
from app.domain.report.weekly.chain import generate_weekly_report
from app.domain.report.weekly.repository import WeeklyReportRepository

# endpoints/report/monthly_report.py
from app.domain.report.monthly.chain import generate_monthly_report
```

### 2. Domain → Infrastructure (정상)
```python
# domain/report/daily/models.py
from app.infrastructure.database.session import Base

# domain/report/search/retriever.py
from ingestion.embed import get_embedding_service  # ✅

# domain/report/search/hybrid_search.py
from ingestion.embed import get_embedding_service  # ✅
```

### 3. Debug → Domain (정상)
```python
# debug/report/test_daily_fsm.py
from app.domain.report.daily.fsm_state import DailyFSMContext
from app.domain.report.daily.daily_fsm import DailyReportFSM

# debug/report/test_weekly_chain.py
from app.domain.report.weekly.chain import generate_weekly_report

# debug/report/test_unified_search.py
from app.domain.report.search.retriever import UnifiedRetriever
from app.domain.report.search.service import UnifiedSearchService
```

### 4. Router 연결 (정상)
```python
# api/v1/router.py
from app.api.v1.endpoints.report.reports import router as reports_router
from app.api.v1.endpoints.report.plan import router as plan_router
from app.api.v1.endpoints.report.daily import router as daily_router
from app.api.v1.endpoints.report.daily_report import router as daily_report_router
from app.api.v1.endpoints.report.weekly_report import router as weekly_report_router
from app.api.v1.endpoints.report.monthly_report import router as monthly_report_router
from app.api.v1.endpoints.report.pdf_export import router as pdf_export_router
from app.api.v1.endpoints.report.report_chat import router as report_chat_router
```

## 🔧 수정된 사항

### 1. Circular Import 해결
- **위치**: `app/infrastructure/database/base.py`, `__init__.py`
- **문제**: `base.py` ↔ `daily.models.py` 순환 참조
- **해결**: 지연 import 및 try-except 사용

### 2. Embedding Service 연결
- **위치**: `app/domain/report/search/retriever.py`, `hybrid_search.py`
- **수정**: `ingestion.embed.get_embedding_service` 사용
- **기능**: HF (sentence-transformers) 또는 OpenAI 선택 가능

### 3. Import 경로 통일
- 모든 보고서 도메인: `app.domain.report.*`
- 모든 테스트 파일: `debug.report.*`

### 4. Config 수정
- **위치**: `app/core/config.py`
- **수정**: `extra="ignore"` 추가 (미정의 환경변수 무시)

## 📊 보고서 시스템 구조

### 보고서 타입
1. **Daily Report** (일일 보고서)
   - FSM 기반 대화형 입력
   - 4개 청크 생성 (summary, detail, pending, plan_note)
   - 시간대별 업무 기록

2. **Weekly Report** (주간 보고서)
   - 일일 보고서 기반 자동 생성
   - LLM Chain 사용

3. **Monthly Report** (월간 보고서)
   - 주간 보고서 기반 자동 생성
   - LLM Chain 사용

### Canonical Report
- 표준화된 보고서 데이터 구조
- 모든 보고서 타입을 통일된 형식으로 변환
- Vector DB 저장 및 검색에 사용

### Vector DB
- **Collection**: `reports`
- **Embedding**: HF (all-MiniLM-L12-v2, 384차원) 또는 OpenAI (text-embedding-3-large, 3072차원)
- **청킹**: 4개 청크 (summary, detail, pending, plan_note) + 메타데이터

## ⚠️ 주의사항

### 테스트 실행 방법
```bash
cd backend

# 일일 보고서 FSM 테스트
python -m debug.report.test_daily_fsm

# 주간 보고서 테스트
python -m debug.report.test_weekly_chain

# 월간 보고서 테스트
python -m debug.report.test_monthly_chain

# 업무 플래닝 테스트
python -m debug.report.test_today_plan_chain

# 통합 검색 테스트
python -m debug.report.test_unified_search
```

### 의존성
- **필수**: `sentence-transformers`, `chromadb`, `openai`, `pydantic`, `fastapi`, `sqlalchemy`
- **선택**: `PyPDF2` (PDF 내보내기용)

## ✅ 검증 완료
- ✅ 모든 API 엔드포인트 경로 연결
- ✅ 모든 Domain 모듈 경로 연결
- ✅ 모든 테스트 파일 import 성공 (PDF 제외)
- ✅ Circular import 해결
- ✅ Embedding service 연결
- ✅ Router 설정 완료

