# 일일보고서 Bulk Ingest 가이드

## 📋 개요

`Data/mock_reports/daily` 폴더에 있는 1년치 일일보고서 txt 파일을 PostgreSQL의 `daily_reports` 테이블에 일괄 저장하는 기능입니다.

**생성 일자**: 2025-11-19  
**담당**: AI Assistant

---

## 🎯 목적

1. 대량의 일일보고서를 빠르게 DB에 저장
2. Weekly/Monthly/Performance 보고서 생성을 위한 기반 데이터 구축
3. 실제 사용자 데이터 없이도 시스템 테스트 가능

---

## 📁 생성된 파일

### 메인 스크립트
- `backend/tools/bulk_daily_ingest.py` - Bulk ingest 메인 스크립트

### 유틸리티 스크립트
- `backend/tools/preview_daily_files.py` - 파일 미리보기
- `backend/tools/run_bulk_ingest_example.py` - 실행 예제

### 문서
- `backend/tools/README.md` - 상세 사용 가이드
- `backend/BULK_INGEST_GUIDE.md` - 이 파일

---

## 🚀 빠른 시작

### 1단계: 사전 준비

#### 1-1. PostgreSQL 확인
```bash
# PostgreSQL이 실행 중인지 확인
# .env 파일에 DATABASE_URL 설정 확인
```

#### 1-2. 마이그레이션 실행
```bash
cd backend
alembic upgrade head
```

### 2단계: 파일 미리보기 (선택사항)
```bash
# 어떤 파일들이 처리될지 미리 확인
python backend/tools/preview_daily_files.py
```

출력 예시:
```
📁 대상 디렉토리: .../backend/Data/mock_reports/daily
📄 발견된 txt 파일: 56개

📂 폴더별 파일 목록:
📁 2025년 1월
   ├─ 파일 수: 4개
   ├─ 보고서 수: 22개
   ...

📊 전체 통계:
   ├─ 폴더 수: 14개
   ├─ 파일 수: 56개
   └─ 총 보고서 수: 250개
```

### 3단계: Bulk Ingest 실행
```bash
# 방법 1: 직접 실행
python backend/tools/bulk_daily_ingest.py

# 방법 2: 예제 스크립트 사용
python backend/tools/run_bulk_ingest_example.py
```

### 4단계: 결과 확인
```bash
# PostgreSQL에 접속하여 확인
psql -d your_database

# daily_reports 테이블 확인
SELECT owner, COUNT(*) as count 
FROM daily_reports 
GROUP BY owner;
```

---

## 🔄 변환 규칙

### 원본 JSON 구조
```json
{
  "문서제목": "일일 업무 보고서",
  "상단정보": {
    "작성일자": "2025-01-02",
    "성명": "김보험"
  },
  "금일_진행_업무": "...",
  "세부업무": [
    {
      "시간": "09:00 - 10:00",
      "업무내용": "박** 고객 신년 실손 보장 점검",
      "비고": ""
    }
  ],
  "미종결_업무사항": "...",
  "익일_업무계획": "...",
  "특이사항": "..."
}
```

### CanonicalReport 변환

| 원본 필드 | CanonicalReport 필드 | 규칙 |
|----------|---------------------|------|
| 문서제목 | report_type | "daily" 고정 |
| 상단정보.작성일자 | period_start | YYYY-MM-DD 파싱 |
| 상단정보.작성일자 | period_end | period_start와 동일 |
| 상단정보.성명 | owner | 그대로 사용 |
| 세부업무[].시간 | tasks[].time_start, time_end | "09:00 - 10:00" → "09:00", "10:00" |
| 세부업무[].업무내용 | tasks[].description | 그대로 사용 |
| 세부업무[].비고 | tasks[].note | 그대로 사용 |
| - | tasks[].status | "완료" 고정 |
| - | tasks[].task_id | "time_1", "time_2", ... 자동 생성 |
| 미종결_업무사항 | issues[] | 배열로 변환 |
| 익일_업무계획 | metadata.next_plan | 메타데이터에 저장 |
| 특이사항 | metadata.notes | 메타데이터에 저장 |
| 금일_진행_업무 | metadata.summary | 메타데이터에 저장 |

---

## 📊 처리 흐름

```
┌─────────────────────────────────────────────┐
│  Data/mock_reports/daily/                   │
│  ├─ 2024년 11월/                            │
│  ├─ 2024년 12월/                            │
│  ├─ 2025년 1월/                             │
│  │  ├─ 2025년 1월 2일 ~ 1월 10일.txt       │
│  │  ├─ 2025년 1월 13일 ~ 1월 17일.txt      │
│  │  └─ ...                                  │
│  └─ ...                                     │
└────────────────┬────────────────────────────┘
                 │
                 v
┌─────────────────────────────────────────────┐
│  bulk_daily_ingest.py                       │
│  ├─ 1. txt 파일 탐색 (재귀)                │
│  ├─ 2. JSON 객체 추출                       │
│  ├─ 3. CanonicalReport 변환                │
│  └─ 4. PostgreSQL UPSERT                   │
└────────────────┬────────────────────────────┘
                 │
                 v
┌─────────────────────────────────────────────┐
│  PostgreSQL: daily_reports 테이블           │
│  ├─ owner: "김보험"                        │
│  ├─ date: 2025-01-02                       │
│  └─ report_json: {...}                     │
└─────────────────────────────────────────────┘
```

---

## 🔧 주요 함수

### 1. `parse_time_range(time_str)`
시간 범위를 파싱합니다.

```python
parse_time_range("09:00 - 10:00")
# → ("09:00", "10:00")
```

### 2. `parse_date(date_str)`
날짜 문자열을 date 객체로 변환합니다.

```python
parse_date("2025-01-02")
# → date(2025, 1, 2)
```

### 3. `convert_to_canonical_report(raw_json)`
Raw JSON을 CanonicalReport로 변환합니다.

```python
raw = {...}  # 원본 JSON
canonical = convert_to_canonical_report(raw)
# → CanonicalReport 객체
```

### 4. `read_json_objects_from_file(file_path)`
txt 파일에서 여러 JSON 객체를 읽습니다.

```python
objects = read_json_objects_from_file(Path("파일.txt"))
# → [json1, json2, json3, ...]
```

### 5. `bulk_ingest_daily_reports()`
메인 함수: 모든 처리를 수행합니다.

---

## ⚙️ UPSERT 동작

### UPSERT란?
- **존재하지 않으면** → 새로 생성 (INSERT)
- **이미 존재하면** → 업데이트 (UPDATE)

### 중복 판단 기준
- `owner` + `date` 조합

### 예시
```python
# 첫 실행: 생성
bulk_ingest_daily_reports()
# → 250개 생성

# 두 번째 실행: 업데이트
bulk_ingest_daily_reports()
# → 250개 업데이트 (중복 생성되지 않음)
```

---

## 📈 성능

### 처리 속도
- **파일 읽기**: ~1-2초/파일
- **JSON 파싱**: ~0.1초/객체
- **DB 저장**: ~0.05초/레코드
- **전체 (250개 보고서)**: ~30-60초

### 메모리 사용
- **파일당**: ~1-2MB
- **최대 메모리**: ~50-100MB

---

## ⚠️ 주의사항

### 1. 날짜 형식
- JSON의 `작성일자`는 반드시 `YYYY-MM-DD` 형식
- 잘못된 예: `2025/01/02`, `01-02-2025`

### 2. 시간 형식
- `시간` 필드는 `HH:MM - HH:MM` 형식
- 예: `"09:00 - 10:00"`

### 3. 인코딩
- txt 파일은 UTF-8 인코딩이어야 함

### 4. JSON 구조
- 각 JSON 객체는 완전한 형태여야 함
- 중괄호 짝이 맞아야 함

### 5. DB 연결
- PostgreSQL이 실행 중이어야 함
- `.env` 파일에 올바른 `DATABASE_URL` 설정 필요

---

## 🐛 트러블슈팅

### 문제: "디렉토리가 존재하지 않습니다"

**원인**: Data/mock_reports/daily 폴더가 없음

**해결**:
```bash
# 경로 확인
ls backend/Data/mock_reports/daily
```

### 문제: "데이터베이스 연결 오류"

**원인**: PostgreSQL 미실행 또는 .env 설정 오류

**해결**:
```bash
# PostgreSQL 상태 확인
# .env 파일의 DATABASE_URL 확인
```

### 문제: "테이블이 존재하지 않습니다"

**원인**: 마이그레이션 미실행

**해결**:
```bash
cd backend
alembic upgrade head
```

### 문제: "JSON 파싱 오류"

**원인**: txt 파일의 JSON 형식 오류

**해결**:
- 해당 파일을 텍스트 에디터로 열어 JSON 구조 확인
- 중괄호 짝 확인
- 콤마, 따옴표 확인

### 문제: "날짜 형식 오류"

**원인**: 작성일자가 YYYY-MM-DD 형식이 아님

**해결**:
- txt 파일의 작성일자 형식 확인
- 예: `"2025-01-02"` (O), `"2025/01/02"` (X)

---

## 📚 다음 단계

### 1. 주간 보고서 생성
```bash
python backend/debug/test_weekly_chain.py
```

### 2. 월간 보고서 생성
```bash
python backend/debug/test_monthly_chain.py
```

### 3. 실적 보고서 생성
```bash
python backend/debug/test_performance_chain.py
```

### 4. API 서버 시작
```bash
python assistant.py
```

### 5. API 테스트
- Swagger UI: http://localhost:8000/docs
- 주간 보고서 생성: `POST /api/v1/weekly/generate`
- 월간 보고서 생성: `POST /api/v1/monthly/generate`
- 실적 보고서 생성: `POST /api/v1/performance/generate`

---

## 📖 참고 문서

- `backend/tools/README.md` - 상세 사용 가이드
- `backend/REPORT_CHAINS_SETUP.md` - 보고서 체인 설정
- `backend/REPORT_CHAINS_IMPLEMENTATION_SUMMARY.md` - 구현 요약
- `backend/DAILY_FSM_INTEGRATION.md` - Daily FSM 가이드

---

## ✅ 체크리스트

실행 전 확인사항:

- [ ] PostgreSQL 실행 중
- [ ] .env 파일 설정 완료
- [ ] alembic upgrade head 실행 완료
- [ ] Data/mock_reports/daily 폴더 존재 확인
- [ ] txt 파일들이 UTF-8 인코딩인지 확인

실행 후 확인사항:

- [ ] 에러 없이 완료되었는지 확인
- [ ] PostgreSQL에서 데이터 확인
- [ ] 생성/업데이트 개수 확인
- [ ] 주간/월간 보고서 생성 테스트

---

## 🎉 완료!

모든 일일보고서가 DB에 저장되었습니다!

이제 Weekly/Monthly/Performance 보고서를 자동으로 생성할 수 있습니다.

Happy Coding! 🚀

