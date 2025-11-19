# Daily Report 운영 DB 저장 기능 구현 완료

## 📋 개요

Daily FSM이 생성한 CanonicalReport(JSON)를 PostgreSQL 운영 DB에 저장하는 기능이 성공적으로 구현되었습니다.

- **VectorDB (ChromaDB)**: 검색용 (기존)
- **PostgreSQL**: 운영 데이터 저장소 (신규)

## 🎯 구현 내용

### 1. 데이터베이스 테이블 생성

#### 테이블 구조: `daily_reports`

| 컬럼명 | 타입 | 설명 | 제약조건 |
|--------|------|------|----------|
| id | UUID | 보고서 ID | PRIMARY KEY |
| owner | String(100) | 작성자 | NOT NULL, INDEX |
| date | Date | 보고서 날짜 (YYYY-MM-DD) | NOT NULL, INDEX |
| report_json | JSONB | CanonicalReport 전체 저장 | NOT NULL |
| created_at | DateTime(TZ) | 생성일시 | DEFAULT now() |
| updated_at | DateTime(TZ) | 수정일시 | DEFAULT now() |

#### UNIQUE 제약조건

```sql
UNIQUE (owner, date)  -- owner + date 조합은 중복 불가
```

### 2. 파일 구조

```
backend/app/domain/daily/
├── models.py          # SQLAlchemy 모델 (DailyReport)
├── schemas.py         # Pydantic 스키마 (DailyReportCreate, DailyReportResponse)
└── repository.py      # CRUD 로직 (DailyReportRepository)

backend/app/api/v1/endpoints/
└── daily_report.py    # API 엔드포인트

backend/alembic/versions/
└── 20251119_1154_4fc9c8e54619_add_daily_reports_table.py  # 마이그레이션
```

### 3. 주요 컴포넌트

#### 3.1 SQLAlchemy 모델 (`models.py`)

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

#### 3.2 Repository (CRUD) (`repository.py`)

주요 메서드:
- `get_by_owner_and_date()`: 작성자와 날짜로 조회
- `list_by_owner()`: 작성자의 모든 보고서 조회 (최신순)
- `count_by_owner()`: 작성자의 보고서 개수
- `create()`: 보고서 생성
- `update()`: 보고서 수정
- **`create_or_update()`**: UPSERT 로직 (중복 시 자동 업데이트)

#### 3.3 API 엔드포인트 (`daily_report.py`)

| 엔드포인트 | 메서드 | 설명 |
|-----------|--------|------|
| `/api/v1/daily-report` | POST | 보고서 저장 (생성/업데이트) |
| `/api/v1/daily-report/{owner}/{date}` | GET | 특정 보고서 조회 |
| `/api/v1/daily-report/list/{owner}` | GET | 작성자 보고서 목록 (페이징) |
| `/api/v1/daily-report/{owner}/{date}` | DELETE | 보고서 삭제 |
| `/api/v1/daily-report/health` | GET | Health check |

### 4. FSM 자동 저장 연동

**위치**: `backend/app/api/v1/endpoints/daily.py` (Line 181-196)

FSM이 완료되면 자동으로 PostgreSQL에 저장:

```python
# FSM 완료 시
if result["finished"]:
    # 보고서 생성
    report = build_daily_report(...)
    
    # 🔥 운영 DB에 저장 (PostgreSQL)
    try:
        report_dict = report.model_dump(mode='json')
        report_create = DailyReportCreate(
            owner=report.owner,
            date=report.period_start,
            report_json=report_dict
        )
        db_report, is_created = DailyReportRepository.create_or_update(db, report_create)
        action = "생성" if is_created else "업데이트"
        print(f"💾 운영 DB 저장 완료 ({action}): {report.owner} - {report.period_start}")
    except Exception as db_error:
        print(f"⚠️  운영 DB 저장 실패 (계속 진행): {str(db_error)}")
        # DB 저장 실패해도 보고서는 반환
```

**특징**:
- UPSERT 로직: 같은 날짜에 재작성하면 자동으로 업데이트
- Fail-safe: DB 저장 실패해도 보고서는 사용자에게 반환
- 로깅: 생성/업데이트 여부를 명확히 표시

## 🔧 마이그레이션

### 생성

```bash
cd backend
conda activate jk
alembic revision --autogenerate -m "Add daily_reports table"
```

### 적용

```bash
alembic upgrade head
```

### 롤백 (필요 시)

```bash
alembic downgrade -1
```

### 마이그레이션 파일

```
backend/alembic/versions/20251119_1154_4fc9c8e54619_add_daily_reports_table.py
```

## 📊 데이터 흐름

```
사용자 답변
    ↓
Daily FSM
    ↓
CanonicalReport 생성 (daily_builder.py)
    ↓
┌─────────────────────────────────────┐
│  PostgreSQL (운영 DB)               │
│  - daily_reports 테이블             │
│  - UNIQUE(owner, date) 제약         │
│  - UPSERT 로직 (중복 시 업데이트)   │
└─────────────────────────────────────┘
    ↓
사용자에게 최종 보고서 반환
```

## ✅ 검증 방법

### 1. API 테스트

```bash
# 보고서 저장
curl -X POST http://localhost:8000/api/v1/daily-report \
  -H "Content-Type: application/json" \
  -d '{
    "report_id": "...",
    "report_type": "daily",
    "owner": "홍길동",
    "period_start": "2025-11-19",
    "period_end": "2025-11-19",
    "tasks": [...],
    "kpis": [],
    "issues": [],
    "plans": [...],
    "metadata": {...}
  }'

# 보고서 조회
curl http://localhost:8000/api/v1/daily-report/홍길동/2025-11-19

# 보고서 목록
curl http://localhost:8000/api/v1/daily-report/list/홍길동
```

### 2. DB 직접 확인

```sql
-- 테이블 구조 확인
\d daily_reports

-- 데이터 조회
SELECT id, owner, date, created_at, updated_at 
FROM daily_reports 
ORDER BY date DESC;

-- JSONB 내용 확인
SELECT owner, date, report_json->'tasks' as tasks
FROM daily_reports
WHERE owner = '홍길동';
```

### 3. FSM 전체 플로우 테스트

```bash
# 1. 금일 진행 업무 선택
POST /api/v1/daily/select_main_tasks

# 2. 일일보고서 작성 시작
POST /api/v1/daily/start

# 3. 시간대별 답변 입력 (반복)
POST /api/v1/daily/answer

# 4. 완료 시 자동으로 DB에 저장됨 ✅
```

## 🚨 주의사항

### 1. UNIQUE 제약조건

- **owner + date 조합은 중복 불가**
- 같은 날짜에 재작성하면 자동으로 기존 데이터가 업데이트됨
- 실수로 덮어쓰지 않도록 주의

### 2. JSONB 컬럼

- CanonicalReport 전체가 JSON으로 저장됨
- PostgreSQL의 JSONB 타입 사용 (검색 가능)
- 필드 추가/변경 시 스키마 마이그레이션 불필요

### 3. 타임존

- `created_at`, `updated_at`은 timezone-aware
- `date`는 YYYY-MM-DD 형식 (날짜만)

### 4. 의존성

- `email-validator` 패키지 필요 (Alembic 실행 시)
  ```bash
  pip install email-validator
  ```

## 🔄 기존 시스템과의 통합

| 구분 | VectorDB (ChromaDB) | PostgreSQL (운영 DB) |
|------|---------------------|---------------------|
| 용도 | 검색 (RAG) | 운영 데이터 저장 |
| 저장 방식 | 임베딩 벡터 + 메타데이터 | CanonicalReport 원본 JSON |
| 중복 허용 | 허용 (버전 관리 가능) | 불가 (UNIQUE 제약) |
| 조회 방식 | 시맨틱 검색 | SQL 쿼리 |
| 백업 | ChromaDB 디렉토리 | PostgreSQL 덤프 |

**두 시스템은 독립적으로 동작**:
- VectorDB 저장 실패 ≠ 운영 DB 저장 실패
- 각각 별도의 에러 처리

## 📝 향후 개선 사항

1. **버전 관리**: 같은 날짜의 여러 버전 저장 (history 테이블)
2. **감사 로그**: 수정 이력 추적
3. **백업/복원**: 자동 백업 스케줄러
4. **통계**: 작성률, 평균 작성 시간 등
5. **알림**: 미작성 시 알림 기능

## 🎉 완료

✅ PostgreSQL 테이블 생성  
✅ SQLAlchemy 모델 생성  
✅ Pydantic 스키마 생성  
✅ Repository (CRUD) 생성  
✅ API 엔드포인트 생성  
✅ FSM 자동 저장 연동  
✅ Alembic 마이그레이션 생성 및 적용  
✅ 문서화 완료  

---

**작성일**: 2025-11-19  
**버전**: 1.0.0  
**작성자**: AI Assistant

