# Daily Report 운영 DB 저장 기능 구현 완료 ✅

## 📋 개요

FSM 기반 일일보고서를 PostgreSQL에 **운영 데이터**로 저장하는 기능을 구현했습니다.

- **VectorDB (ChromaDB)**: 검색용
- **PostgreSQL**: 운영 데이터 저장 (날짜 중복 불가)

---

## 🗄️ 데이터베이스 스키마

### `daily_reports` 테이블

| 컬럼 | 타입 | 제약조건 | 설명 |
|------|------|---------|------|
| `id` | UUID | PRIMARY KEY | 보고서 ID |
| `owner` | VARCHAR(100) | NOT NULL, INDEX | 작성자 |
| `date` | DATE | NOT NULL, INDEX | 보고서 날짜 |
| `report_json` | JSONB | NOT NULL | CanonicalReport 전체 |
| `created_at` | TIMESTAMP | DEFAULT NOW() | 생성일시 |
| `updated_at` | TIMESTAMP | DEFAULT NOW() | 수정일시 |

**UNIQUE 제약조건**: `UNIQUE(owner, date)`
- 동일 작성자가 같은 날짜에 여러 보고서 생성 불가
- UPSERT 로직으로 자동 처리

---

## 📁 생성된 파일

### 1. SQLAlchemy 모델
**파일**: `backend/app/domain/daily/models.py`
```python
class DailyReport(Base):
    __tablename__ = "daily_reports"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner = Column(String(100), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    report_json = Column(JSONB, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    __table_args__ = (
        UniqueConstraint('owner', 'date', name='uq_daily_report_owner_date'),
    )
```

### 2. Pydantic 스키마
**파일**: `backend/app/domain/daily/schemas.py`
- `DailyReportCreate`: 생성 요청
- `DailyReportUpdate`: 수정 요청
- `DailyReportResponse`: 응답
- `DailyReportListResponse`: 목록 응답

### 3. Repository (CRUD)
**파일**: `backend/app/domain/daily/repository.py`

**주요 메서드**:
- `get_by_owner_and_date(db, owner, date)`: 조회
- `list_by_owner(db, owner, skip, limit)`: 목록 (최신순)
- `create(db, report_create)`: 생성
- `update(db, db_report, report_update)`: 수정
- `create_or_update(db, report_create)`: UPSERT
- `delete(db, db_report)`: 삭제

**UPSERT 로직**:
```python
existing = get_by_owner_and_date(db, owner, date)
if existing:
    # 업데이트
    return (update(db, existing, update_data), False)
else:
    # 생성
    return (create(db, report_create), True)
```

### 4. API 엔드포인트
**파일**: `backend/app/api/v1/endpoints/daily_report.py`

| Method | Endpoint | 설명 |
|--------|----------|------|
| POST | `/api/v1/daily-report` | 보고서 저장 (UPSERT) |
| GET | `/api/v1/daily-report/{owner}/{date}` | 보고서 조회 |
| GET | `/api/v1/daily-report/list/{owner}` | 보고서 목록 |
| DELETE | `/api/v1/daily-report/{owner}/{date}` | 보고서 삭제 |

### 5. 자동 저장 통합
**파일**: `backend/app/api/v1/endpoints/daily.py`

FSM 완료 시 (`/daily/answer` 엔드포인트):
```python
if result["finished"]:
    # 보고서 생성
    report = build_daily_report(...)
    
    # 🔥 운영 DB 저장
    report_create = DailyReportCreate(
        owner=report.owner,
        date=report.period_start,
        report_json=report.model_dump(mode='json')
    )
    db_report, is_created = DailyReportRepository.create_or_update(db, report_create)
    print(f"💾 운영 DB 저장 완료: {report.owner} - {report.period_start}")
```

---

## 🚀 설정 방법

### 1. 데이터베이스 마이그레이션

**Alembic 마이그레이션 생성**:
```bash
cd backend
alembic revision --autogenerate -m "Add daily_reports table"
```

**마이그레이션 적용**:
```bash
alembic upgrade head
```

### 2. 테이블 확인

PostgreSQL에 접속하여 확인:
```sql
\d daily_reports

-- UNIQUE 제약조건 확인
SELECT constraint_name, constraint_type 
FROM information_schema.table_constraints 
WHERE table_name = 'daily_reports';
```

---

## 📊 API 사용 예시

### 1. 보고서 저장 (FSM 완료 시 자동)

FSM이 완료되면 자동으로 DB에 저장됩니다:
```
👤 "일일보고서 입력할래"
🤖 "09:00~10:00 무엇을 했나요?"
... (계속 입력)
🤖 "모든 시간대 입력이 완료되었습니다!"

💾 운영 DB 저장 완료: 김보험 - 2025-11-19
```

### 2. 보고서 수동 저장 (API 직접 호출)

```bash
POST /api/v1/daily-report
Content-Type: application/json

{
  "report_id": "abc123...",
  "report_type": "daily",
  "owner": "김보험",
  "period_start": "2025-11-19",
  "period_end": "2025-11-19",
  "tasks": [...],
  "plans": [...],
  "issues": [...],
  "metadata": {...}
}
```

### 3. 보고서 조회

```bash
GET /api/v1/daily-report/김보험/2025-11-19
```

**응답**:
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "owner": "김보험",
  "date": "2025-11-19",
  "report_json": {
    "report_id": "abc123...",
    "report_type": "daily",
    "tasks": [...],
    "plans": [...],
    "issues": [...]
  },
  "created_at": "2025-11-19T10:30:00Z",
  "updated_at": "2025-11-19T10:30:00Z"
}
```

### 4. 보고서 목록 조회

```bash
GET /api/v1/daily-report/list/김보험?skip=0&limit=10
```

**응답**:
```json
{
  "total": 25,
  "reports": [
    {
      "id": "...",
      "owner": "김보험",
      "date": "2025-11-19",
      "report_json": {...},
      "created_at": "...",
      "updated_at": "..."
    },
    ...
  ]
}
```

---

## 🔒 UNIQUE 제약조건 처리

### 문제: owner + date 중복

**시나리오**:
1. 오전에 일일보고서 작성 (김보험, 2025-11-19)
2. 오후에 추가 내용 입력 (김보험, 2025-11-19)

**해결**: UPSERT 로직
```python
existing = get_by_owner_and_date(db, "김보험", "2025-11-19")
if existing:
    # 업데이트 (기존 보고서 덮어쓰기)
    update(db, existing, new_data)
else:
    # 생성
    create(db, new_data)
```

**결과**:
- 중복 오류 없음
- 자동으로 최신 내용으로 업데이트
- 사용자는 신경 쓸 필요 없음

---

## 🧪 테스트

### 수동 테스트

```python
# backend/test_daily_report_db.py
import requests
from datetime import date

BASE_URL = "http://localhost:8000/api/v1"

# 1. FSM으로 보고서 생성 (자동 저장)
# → 프론트엔드에서 "일일보고서 입력할래" 입력

# 2. 저장된 보고서 조회
owner = "김보험"
report_date = date.today().isoformat()

response = requests.get(f"{BASE_URL}/daily-report/{owner}/{report_date}")
print(response.json())

# 3. 보고서 목록 조회
response = requests.get(f"{BASE_URL}/daily-report/list/{owner}")
print(f"총 {response.json()['total']}개 보고서")
```

---

## ⚙️ 운영 고려사항

### 1. 백업

PostgreSQL의 JSONB 필드에 전체 CanonicalReport가 저장됩니다.
정기적으로 백업:
```bash
pg_dump -t daily_reports -U postgres virtual_assistant > daily_reports_backup.sql
```

### 2. 인덱스 최적화

자주 조회하는 패턴:
- `(owner, date)`: 이미 UNIQUE 인덱스 자동 생성 ✅
- `(owner, created_at)`: 필요 시 추가

### 3. JSON 쿼리

JSONB 필드는 쿼리 가능:
```sql
-- plans에 특정 업무가 있는 보고서 찾기
SELECT * FROM daily_reports 
WHERE report_json @> '{"plans": ["암보험 회신 확인"]}';

-- 특정 카테고리 작업이 있는 보고서
SELECT * FROM daily_reports 
WHERE report_json->'tasks' @> '[{"category": "업무"}]';
```

### 4. 용량 관리

JSONB는 압축되어 저장되지만, 오래된 보고서는 아카이빙 고려:
```sql
-- 1년 이상 된 보고서 아카이빙
DELETE FROM daily_reports 
WHERE date < CURRENT_DATE - INTERVAL '1 year';
```

---

## ✅ 완료 체크리스트

- [x] SQLAlchemy 모델 생성 (`models.py`)
- [x] Pydantic 스키마 생성 (`schemas.py`)
- [x] Repository (CRUD) 생성 (`repository.py`)
- [x] API 엔드포인트 생성 (`daily_report.py`)
- [x] Router에 엔드포인트 추가
- [x] Base.py에 모델 import 추가
- [x] FSM 완료 시 자동 저장 로직 추가
- [x] UNIQUE 제약조건 및 UPSERT 처리
- [x] 문서 작성

---

## 🔄 다음 단계

### 1. 마이그레이션 실행
```bash
cd backend
alembic revision --autogenerate -m "Add daily_reports table"
alembic upgrade head
```

### 2. 백엔드 재시작
```bash
python assistant.py
```

### 3. 테스트
프론트엔드에서 일일보고서 입력 후 DB 확인:
```sql
SELECT * FROM daily_reports ORDER BY date DESC LIMIT 5;
```

---

**작성일**: 2025-11-19  
**작성자**: AI Assistant

