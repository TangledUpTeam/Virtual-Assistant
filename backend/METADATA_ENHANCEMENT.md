# 청크 메타데이터 자동 생성 기능 추가

## 변경 개요

`chunker.py`에 `build_chunk_metadata()` 함수를 추가하여 청크 메타데이터를 자동으로 생성하도록 개선했습니다.

## 주요 변경사항

### 1. 새로운 함수 추가: `build_chunk_metadata()`

**위치**: `backend/app/domain/report/chunker.py` (상단, 헬퍼 함수 전)

**시그니처**:
```python
def build_chunk_metadata(
    chunk_type: str,
    canonical: CanonicalReport,
    **kwargs
) -> Dict[str, Any]
```

**기능**:
- 청크 타입과 CanonicalReport를 기반으로 메타데이터 자동 생성
- 공통 필드 + 타입별 특화 필드 포함
- 확장 가능한 kwargs 구조

### 2. 공통 메타데이터 필드

모든 청크에 포함되는 필드:
```python
{
  "chunk_type": "task|kpi|issue|plan|summary",
  "report_id": "uuid",
  "report_type": "daily|weekly|monthly|performance",
  "owner": "작성자명",
  "period_start": "2024-01-15",  # ISO format
  "period_end": "2024-01-15"     # ISO format
}
```

### 3. 타입별 추가 필드

#### Task 청크
```python
{
  "task_id": "daily_1",
  "task_status": "완료",  # TaskItem.status
  "time_slot": "09:00~10:00"
}
```

#### KPI 청크
```python
{
  "kpi_name": "신규_계약_건수",
  "kpi_tags": ["계약"]  # KPIItem.category를 배열로 변환
}
```

#### Issue 청크
```python
{
  "issue_flag": true
}
```

#### Plan 청크
```python
{
  "plan_flag": true
}
```

#### Summary 청크
```python
{
  "task_count": 5,
  "kpi_count": 3,
  "issue_count": 1,
  "plan_count": 2
}
```

### 4. 함수 시그니처 변경

기존 청킹 함수들이 `report_id`, `report_type`를 개별 파라미터로 받던 것을 `canonical` 객체로 통합:

**변경 전**:
```python
def _chunk_task(task: TaskItem, report_id: str, report_type: str)
def _chunk_kpi(kpi: KPIItem, report_id: str, report_type: str)
def _chunk_issue(issue: str, report_id: str, report_type: str)
def _chunk_plan(plan: str, report_id: str, report_type: str)
```

**변경 후**:
```python
def _chunk_task(task: TaskItem, canonical: CanonicalReport)
def _chunk_kpi(kpi: KPIItem, canonical: CanonicalReport)
def _chunk_issue(issue: str, canonical: CanonicalReport)
def _chunk_plan(plan: str, canonical: CanonicalReport)
```

### 5. 메인 함수 호출 변경

`chunk_report()` 함수 내부:

**변경 전**:
```python
report_id = canonical_report.report_id
report_type = canonical_report.report_type

for task in canonical_report.tasks:
    task_chunks = _chunk_task(task, report_id, report_type)
```

**변경 후**:
```python
for task in canonical_report.tasks:
    task_chunks = _chunk_task(task, canonical_report)
```

## 메타데이터 생성 예시

### Task 청크 메타데이터

**입력**:
```python
task = TaskItem(
    task_id="daily_1",
    title="신규 고객 전화 상담",
    time_start="09:00",
    time_end="10:00",
    status="완료"
)

canonical = CanonicalReport(
    report_id="abc-123",
    report_type="daily",
    owner="홍길동",
    period_start=date(2024, 1, 15),
    period_end=date(2024, 1, 15)
)
```

**출력**:
```json
{
  "chunk_type": "task",
  "report_id": "abc-123",
  "report_type": "daily",
  "owner": "홍길동",
  "period_start": "2024-01-15",
  "period_end": "2024-01-15",
  "task_id": "daily_1",
  "task_status": "완료",
  "time_slot": "09:00~10:00"
}
```

### KPI 청크 메타데이터

**입력**:
```python
kpi = KPIItem(
    kpi_name="신규_계약_건수",
    value="10",
    unit="건",
    category="계약"
)
```

**출력**:
```json
{
  "chunk_type": "kpi",
  "report_id": "abc-123",
  "report_type": "monthly",
  "owner": "홍길동",
  "period_start": "2024-01-01",
  "period_end": "2024-01-31",
  "kpi_name": "신규_계약_건수",
  "kpi_tags": ["계약"]
}
```

### Issue 청크 메타데이터

**출력**:
```json
{
  "chunk_type": "issue",
  "report_id": "abc-123",
  "report_type": "daily",
  "owner": "홍길동",
  "period_start": "2024-01-15",
  "period_end": "2024-01-15",
  "issue_flag": true
}
```

## 분할 청크 메타데이터

1,000자를 초과하는 텍스트는 자동 분할되며, 추가 필드가 붙습니다:

```json
{
  "chunk_type": "task",
  "report_id": "abc-123",
  "report_type": "daily",
  "owner": "홍길동",
  "period_start": "2024-01-15",
  "period_end": "2024-01-15",
  "task_id": "daily_1",
  "task_status": "완료",
  "time_slot": "09:00~10:00",
  "part": 1,
  "total_parts": 2
}
```

## 장점

### 1. 일관성
- 모든 청크가 동일한 공통 필드 보유
- 메타데이터 생성 로직 중앙화

### 2. 확장성
- 새로운 필드 추가 시 `build_chunk_metadata()` 한 곳만 수정
- kwargs로 유연한 확장 가능

### 3. 유지보수성
- 중복 코드 제거
- 메타데이터 생성 로직 명확화

### 4. 검색 효율성
- 공통 필드로 모든 청크 대상 쿼리 가능
- 타입별 특화 필드로 정확한 필터링

## 사용 예시

### Vector DB 검색

```python
# 특정 작성자의 모든 청크 검색
results = collection.query(
    query_texts=["업무"],
    where={"owner": "홍길동"}
)

# 특정 기간의 Task 청크만 검색
results = collection.query(
    query_texts=["상담"],
    where={
        "chunk_type": "task",
        "period_start": {"$gte": "2024-01-01"},
        "period_end": {"$lte": "2024-01-31"}
    }
)

# 완료된 작업만 검색
results = collection.query(
    query_texts=["계약"],
    where={
        "chunk_type": "task",
        "task_status": "완료"
    }
)

# 특정 시간대 작업 검색
results = collection.query(
    query_texts=["고객"],
    where={
        "chunk_type": "task",
        "time_slot": {"$regex": "^09:"}  # 9시대 작업
    }
)

# 특정 카테고리 KPI 검색
results = collection.query(
    query_texts=["계약"],
    where={
        "chunk_type": "kpi",
        "kpi_tags": {"$contains": "계약"}
    }
)

# 이슈만 검색
results = collection.query(
    query_texts=["문제"],
    where={"issue_flag": true}
)
```

## 코드 변경 라인 수

- **추가**: 약 80줄 (`build_chunk_metadata()` 함수)
- **수정**: 약 100줄 (함수 시그니처 및 호출 부분)
- **삭제**: 약 50줄 (중복 메타데이터 생성 코드)
- **순 증가**: 약 130줄

## 테스트 방법

```bash
cd backend
python test_report_parser.py "Data/일일 업무 보고서.pdf"
```

**확인 사항**:
1. 청크 샘플 출력에서 메타데이터 필드 확인
2. `output/*_chunks.json` 파일에서 전체 메타데이터 확인
3. 공통 필드 (report_id, owner, period_start 등) 존재 확인
4. 타입별 특화 필드 (task_id, kpi_tags, issue_flag 등) 확인

## 하위 호환성

- ✅ 기존 API 시그니처 유지 (`chunk_report()`)
- ✅ 반환 구조 동일 (List[Dict])
- ✅ 기존 메타데이터 필드 모두 포함
- ✅ 추가 필드만 확장

---

**변경 완료일**: 2025-11-17  
**상태**: ✅ 완료 및 테스트 가능

