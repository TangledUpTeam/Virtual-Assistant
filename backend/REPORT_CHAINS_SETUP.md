# 보고서 자동 생성 체인 설정 가이드

## 개요

주간(Weekly), 월간(Monthly), 실적(Performance) 보고서 자동 생성 기능이 추가되었습니다.
일일보고서(Daily)를 기반으로 각 보고서를 자동으로 집계하여 생성합니다.

## 구현된 기능

### 1. Weekly Report (주간 보고서)
- **입력**: owner, target_date
- **기간 계산**: target_date가 속한 주의 월~금 (5일)
- **출력**: CanonicalReport (weekly)
- **DB**: weekly_reports 테이블

### 2. Monthly Report (월간 보고서)
- **입력**: owner, target_date
- **기간 계산**: target_date가 속한 달의 1일~말일
- **출력**: CanonicalReport (monthly)
- **DB**: monthly_reports 테이블

### 3. Performance Report (실적 보고서)
- **입력**: owner, period_start, period_end
- **기간**: 사용자 지정 범위
- **특징**: KPI 관련 업무만 필터링 + KPI 문서 자동 로드
- **출력**: CanonicalReport (performance)
- **DB**: performance_reports 테이블

## 설치 및 설정

### 1. 데이터베이스 마이그레이션 실행

```bash
cd backend
alembic upgrade head
```

이 명령은 다음 테이블을 생성합니다:
- `weekly_reports`
- `monthly_reports`
- `performance_reports`

각 테이블은 다음 구조를 가집니다:
- `id` (UUID, PK)
- `owner` (TEXT)
- `period_start` (DATE)
- `period_end` (DATE)
- `report_json` (JSONB) - CanonicalReport
- `created_at` (TIMESTAMP)
- `updated_at` (TIMESTAMP)
- UNIQUE 제약: (owner, period_start, period_end)

### 2. 서버 시작

```bash
cd ..
python assistant.py
```

서버가 시작되면 다음 엔드포인트가 활성화됩니다:
- `http://localhost:8000/docs` - API 문서

## API 엔드포인트

### Weekly Report

#### 주간 보고서 생성
```
POST /api/v1/weekly/generate
Content-Type: application/json

{
  "owner": "김보험",
  "target_date": "2025-01-20"
}
```

#### 주간 보고서 목록 조회
```
GET /api/v1/weekly/list/{owner}?skip=0&limit=100
```

### Monthly Report

#### 월간 보고서 생성
```
POST /api/v1/monthly/generate
Content-Type: application/json

{
  "owner": "김보험",
  "target_date": "2025-01-20"
}
```

#### 월간 보고서 목록 조회
```
GET /api/v1/monthly/list/{owner}?skip=0&limit=100
```

### Performance Report

#### 실적 보고서 생성
```
POST /api/v1/performance/generate
Content-Type: application/json

{
  "owner": "김보험",
  "period_start": "2025-01-01",
  "period_end": "2025-01-31"
}
```

#### 실적 보고서 목록 조회
```
GET /api/v1/performance/list/{owner}?skip=0&limit=100
```

## 테스트

### 테스트 스크립트 실행

```bash
cd backend

# 주간 보고서 테스트
python debug/test_weekly_chain.py

# 월간 보고서 테스트
python debug/test_monthly_chain.py

# 실적 보고서 테스트
python debug/test_performance_chain.py
```

**주의**: 테스트를 실행하기 전에 먼저 일일보고서(daily_reports)가 있어야 합니다.

### 일일보고서 생성 (테스트용)

일일보고서가 없는 경우, Daily FSM을 통해 생성하거나 다음과 같이 직접 생성할 수 있습니다:

```python
from app.domain.daily.repository import DailyReportRepository
from app.domain.daily.schemas import DailyReportCreate
from app.infrastructure.database.session import SessionLocal
from datetime import date

db = SessionLocal()

# 예시 일일보고서 생성
report_create = DailyReportCreate(
    owner="김보험",
    report_date=date(2025, 1, 20),
    report_json={
        "report_id": "test-001",
        "report_type": "daily",
        "owner": "김보험",
        "period_start": "2025-01-20",
        "period_end": "2025-01-20",
        "tasks": [
            {
                "title": "영업 미팅",
                "description": "고객 상담",
                "status": "완료"
            }
        ],
        "plans": ["다음 주 계약 체결"],
        "issues": [],
        "kpis": [],
        "metadata": {}
    }
)

DailyReportRepository.create(db, report_create)
db.close()
```

## 디렉토리 구조

```
backend/
├── app/
│   ├── domain/
│   │   ├── weekly/
│   │   │   ├── __init__.py
│   │   │   ├── models.py       # SQLAlchemy 모델
│   │   │   ├── schemas.py      # Pydantic 스키마
│   │   │   ├── repository.py   # CRUD
│   │   │   └── chain.py        # 주간 보고서 생성 로직
│   │   ├── monthly/
│   │   │   └── ... (동일 구조)
│   │   └── performance/
│   │       └── ... (동일 구조)
│   └── api/v1/endpoints/
│       ├── weekly_report.py
│       ├── monthly_report.py
│       └── performance_report.py
├── alembic/versions/
│   └── 20251119_1200_add_weekly_monthly_performance_tables.py
└── debug/
    ├── test_weekly_chain.py
    ├── test_monthly_chain.py
    └── test_performance_chain.py
```

## 주요 기능

### 1. 자동 집계
- 지정된 기간의 모든 일일보고서를 조회
- tasks, plans, issues, kpis를 자동으로 집계
- 완료율(completion_rate) 자동 계산

### 2. UPSERT 지원
- 동일한 owner + period 조합이 존재하면 업데이트
- 없으면 새로 생성

### 3. CanonicalReport 준수
- 모든 보고서는 CanonicalReport 스키마를 따름
- report_type으로 구분 (weekly, monthly, performance)

### 4. KPI 특별 처리 (Performance)
- KPI 관련 키워드로 task 필터링
- `backend/output/KPI 자료_kpi_canonical.json` 자동 로드
- KPI 문서와 일일보고서 KPI 통합

## 트러블슈팅

### 1. "해당 기간에 일일보고서가 없습니다"
- 먼저 Daily FSM을 통해 일일보고서를 생성하세요
- `/api/v1/daily/start`와 `/api/v1/daily/answer` 사용

### 2. 마이그레이션 실패
```bash
# 현재 마이그레이션 상태 확인
alembic current

# 강제로 최신 버전으로 업그레이드
alembic upgrade head
```

### 3. KPI 파일 로드 실패 (Performance)
- `backend/output/KPI 자료_kpi_canonical.json` 파일이 있는지 확인
- 파일 경로가 올바른지 확인

## 다음 단계

1. ✅ 데이터베이스 마이그레이션 실행
2. ✅ 일일보고서 생성 (Daily FSM 사용)
3. ✅ 테스트 스크립트로 각 체인 테스트
4. ✅ API를 통해 프론트엔드 연동

## 참고

- Daily FSM 구현: `DAILY_FSM_INTEGRATION.md`
- 데이터베이스 설정: `DAILY_REPORT_DB_IMPLEMENTATION.md`
- API 문서: http://localhost:8000/docs

