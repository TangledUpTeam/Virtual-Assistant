# 보고서 작성 AI Agent 구현 요약

## 완료된 작업

### 1. 프로젝트 구조 분석 ✅
- FastAPI 기반 백엔드 아키텍처
- Domain-Driven Design 구조
- OAuth 인증 시스템 (Google, Kakao, Naver)
- PostgreSQL + SQLAlchemy ORM
- OpenAI API 통합

### 2. 보고서 처리 모듈 구현 ✅

#### 디렉토리 구조
```
backend/
├── app/
│   └── domain/
│       └── report/                    # 새로 생성됨
│           ├── __init__.py
│           ├── schemas.py             # Pydantic 스키마 정의
│           ├── service.py             # PDF → JSON 변환 서비스
│           └── README.md
├── api/
│   └── v1/
│       └── endpoints/
│           └── reports.py             # 새로 생성됨 - API 엔드포인트
├── Data/                              # 보고서 양식 PDF 저장
├── output/                            # 파싱 결과 JSON 저장
├── test_report_parser.py              # CLI 테스트 스크립트
├── quick_test.py                      # 빠른 테스트 스크립트
├── REPORT_PARSING_GUIDE.md            # 사용 가이드
└── requirements.txt                   # pymupdf 추가됨
```

### 3. 구현된 기능

#### A. PDF → JSON 구조화 (ChatGPT-4 Vision 사용)
- **PDF 이미지 변환**: PyMuPDF 사용
- **자동 문서 타입 감지**: GPT-4o Vision으로 보고서 종류 식별
- **정보 추출**: 사전 정의된 JSON 스키마에 맞춰 데이터 추출

#### B. 지원 보고서 타입 (4종)
1. **일일 업무 보고서** (daily)
   - 상단 정보 (작성일자, 성명)
   - 금일 진행 업무
   - 시간별 세부 업무 (09:00~18:00)
   - 미종결 업무사항
   - 익일 업무계획
   - 특이사항

2. **주간 업무 보고서** (weekly)
   - 주간 업무 목표
   - 요일별 세부 업무 (월~금)
   - 주간 중요 업무
   - 특이사항

3. **월간 업무 보고서** (monthly)
   - 월간 핵심 지표 (신규계약, 유지계약, 상담진행)
   - 주차별 세부 업무 (1~5주)
   - 익월 계획

4. **분기별 실적 보고서** (performance)
   - 주요 지표 (신계약, 유지계약, 소멸계약)
   - 고객 그래프 (분기별)
   - 달력 데이터 (월별)
   - 이슈 및 계획

#### C. API 엔드포인트
- `POST /api/v1/reports/parse` - 보고서 파싱
- `POST /api/v1/reports/detect-type` - 문서 타입 감지
- `GET /api/v1/reports/templates/{type}` - 템플릿 조회

#### D. 테스트 도구
- `test_report_parser.py` - 상세한 CLI 테스트 스크립트
- `quick_test.py` - 간단한 대화형 테스트 도구

## 테스트 실행 방법

### 옵션 1: 빠른 테스트 (추천)
```bash
cd backend
python quick_test.py
```
1. OpenAI API 키 입력
2. PDF 파일 선택
3. 결과 확인 (콘솔 + JSON 파일)

### 옵션 2: CLI 직접 실행
```bash
cd backend
python test_report_parser.py "Data/일일 업무 보고서.pdf"
```

### 옵션 3: API 서버 실행
```bash
cd backend
uvicorn app.main:app --reload
```
- Swagger UI: http://localhost:8000/docs
- `/api/v1/reports/parse` 엔드포인트에서 테스트

## 기술 스택

### 백엔드
- **FastAPI**: 웹 프레임워크
- **Pydantic**: 데이터 검증 및 스키마
- **SQLAlchemy**: ORM
- **PostgreSQL**: 데이터베이스

### AI/ML
- **OpenAI GPT-4o**: Vision API (OCR + 구조화)
- **PyMuPDF (fitz)**: PDF 처리
- **ChromaDB**: 벡터 데이터베이스 (기존)

### 인증
- **OAuth 2.0**: Google, Kakao, Naver
- **JWT**: 토큰 기반 인증

## 다음 단계: Phase 2 구현 계획

### 1. 데이터베이스 모델 설계
```python
# backend/app/domain/report/models.py

class Report(Base):
    """보고서 테이블"""
    id: int
    user_id: int
    report_type: ReportType
    report_date: date
    data: JSON
    created_at: datetime
    updated_at: datetime

class ActivityLog(Base):
    """활동 로그 테이블"""
    id: int
    user_id: int
    timestamp: datetime
    activity: str
    raw_input: str  # 사용자 원본 입력
    formatted_text: str  # AI가 포맷한 내용
    
class KPI(Base):
    """KPI 데이터 테이블"""
    id: int
    user_id: int
    date: date
    신규_계약_건수: int
    유지_계약_건수: int
    상담_진행_건수: int
```

### 2. AI Agent 서비스 구현
```python
# backend/app/domain/report/agent.py

class ReportAgent:
    """보고서 작성 AI Agent"""
    
    async def ask_hourly_activity(self, user_id: int):
        """매시간 사용자에게 활동 질문"""
        
    async def format_activity(self, raw_input: str) -> str:
        """사용자 답변을 보고서 형식으로 변환"""
        # "땡땡이 쳤어" -> "잡무 처리"
        # "고객이랑 전화상담" -> "고객 전화 상담 진행"
        
    async def generate_daily_report(self, user_id: int, date: date):
        """일일 보고서 자동 생성"""
        
    async def recommend_tasks(self, user_id: int):
        """전날 보고서 기반 오늘의 추천 계획"""
        
    async def generate_weekly_report(self, user_id: int):
        """주간 보고서 생성 (금요일)"""
        
    async def generate_monthly_report(self, user_id: int):
        """월간 보고서 생성 (30일)"""
```

### 3. 챗봇 통합
```python
# backend/app/domain/chat/service.py

class ChatService:
    """챗봇 서비스"""
    
    async def process_message(self, user_id: int, message: str):
        """사용자 메시지 처리"""
        # 투두 입력 감지
        # 활동 보고 처리
        # 일반 대화
        
    async def handle_todo_input(self, user_id: int, todos: list):
        """투두 리스트를 보고서에 반영"""
        
    async def handle_activity_report(self, user_id: int, activity: str):
        """활동 보고를 보고서에 기록"""
```

### 4. 스케줄러 구현
```python
# backend/app/services/scheduler.py

from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler()

# 매시간 활동 질문
@scheduler.scheduled_job('cron', hour='*')
async def ask_activity():
    """매시간 사용자에게 활동 질문"""
    
# 금요일 저녁 주간 보고서
@scheduler.scheduled_job('cron', day_of_week='fri', hour=18)
async def generate_weekly_reports():
    """주간 보고서 자동 생성"""
    
# 매월 30일 월간 보고서
@scheduler.scheduled_job('cron', day=30, hour=18)
async def generate_monthly_reports():
    """월간 보고서 자동 생성"""
```

### 5. 프론트엔드 연동
- Electron 앱의 챗 패널 확장
- 보고서 편집 UI
- 활동 타임라인 표시
- 알림 시스템

## WorkFlow 구현 체크리스트

- [x] **Step 1**: 보고서 양식 PDF → JSON 구조화
- [ ] **Step 2**: 전날 보고서 기반 추천 계획 제공
- [ ] **Step 3**: AI 챗봇에 투두 입력 → 보고서 반영
- [ ] **Step 4**: 매시간 활동 질문 (스케줄러)
- [ ] **Step 5**: 사용자 답변 → 보고서 형식 변환
- [ ] **Step 6**: 시간별 일정 작성
- [ ] **Step 7**: 일일 보고서 전체 자동 작성
- [ ] **Step 8**: 주간/월간/실적 보고서 자동 생성

## 필요한 추가 패키지

```txt
# Scheduler
apscheduler==3.10.4

# Background Tasks
celery==5.3.4
redis==5.2.1  # 이미 있음

# Notification
python-telegram-bot==20.7  # 선택사항
```

## 예상 비용 (OpenAI API)

### 현재 구현 (PDF → JSON)
- 모델: GPT-4o Vision
- 페이지당 약 $0.01-0.05
- 보고서 1개: $0.01-0.05

### Phase 2 예상 (일일 사용)
- 시간별 활동 변환: 9회/일 × $0.001 = $0.009
- 일일 보고서 생성: 1회/일 × $0.01 = $0.01
- 주간 보고서: 1회/주 × $0.02 = $0.003/일
- **총 예상**: 약 $0.02-0.05/일/사용자

## 참고 문서

- `backend/REPORT_PARSING_GUIDE.md` - 상세 사용 가이드
- `backend/app/domain/report/README.md` - 모듈 문서
- FastAPI Docs: http://localhost:8000/docs

## 문의 및 다음 작업

현재 **Phase 1 완료**: 보고서 양식 JSON 구조화

다음 구현을 원하시면 말씀해주세요:
1. 데이터베이스 모델 생성
2. AI Agent 서비스 구현
3. 챗봇 통합
4. 스케줄러 설정
5. 프론트엔드 UI

