# Ingestion Pipeline 구현 가이드

## 📋 개요

Chroma Cloud에 문서를 임베딩하고 업로드하는 전체 파이프라인 구현

**구현 일자**: 2025-11-17  
**임베딩 모델**: OpenAI text-embedding-3-large (3072차원)  
**Vector DB**: Chroma Cloud

---

## 🏗️ 아키텍처

```
┌─────────────────┐
│  JSON 청크 파일  │
│  (output/*.json)│
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  load_chunks    │  ← 청크 데이터 로드
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  embed_texts    │  ← OpenAI 임베딩 생성
│ (text-embedding │     (배치 처리)
│   -3-large)     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Chroma Cloud   │  ← upsert
│  - reports      │     (ids, embeddings,
│  - kpi          │      documents, metadatas)
└─────────────────┘
```

---

## 📁 파일 구조

```
backend/
├── ingestion/
│   ├── __init__.py              # 모듈 export
│   ├── embed.py                 # 임베딩 생성 (OpenAI)
│   ├── chroma_client.py         # Chroma Cloud 클라이언트
│   ├── ingest_reports.py        # 보고서 ingestion
│   ├── ingest_kpi.py            # KPI ingestion
│   ├── init_ingest.py           # 전체 실행 스크립트
│   ├── test_query.py            # 검색 테스트
│   └── README.md                # 사용 가이드
│
├── test_ingestion_pipeline.py  # 통합 테스트
└── INGESTION_PIPELINE_GUIDE.md  # 이 문서
```

---

## 🔧 핵심 구성 요소

### 1. embed.py - 임베딩 생성

**주요 기능**:
- OpenAI `text-embedding-3-large` 모델 사용
- 단일/배치 임베딩 생성
- 배치 크기 조정 가능 (기본값: 100)

**클래스**: `EmbeddingService`

**메서드**:
- `embed_text(text)`: 단일 텍스트 임베딩
- `embed_texts(texts, batch_size=100)`: 배치 임베딩

**사용 예시**:
```python
from ingestion.embed import embed_text, embed_texts

# 단일 임베딩
vector = embed_text("주요 업무 성과")

# 배치 임베딩
texts = ["텍스트1", "텍스트2", "텍스트3"]
vectors = embed_texts(texts, batch_size=100)
```

---

### 2. chroma_client.py - Chroma Cloud 클라이언트

**고정 설정**:
```python
API_KEY = "ck-DHJSd4oXoeXytDsQKvgfqAf7MeWddhbovykybeJxXfRu"
TENANT = "87acc175-c5c2-44df-97ff-c0b914e35994"
DATABASE = "Virtual_Assistant"
```

**컬렉션**:
- `reports`: 보고서 문서
- `kpi`: KPI 문서

**클래스**: `ChromaCloudService`

**메서드**:
- `get_or_create_collection(name)`: 컬렉션 가져오기/생성
- `get_reports_collection()`: Reports 컬렉션
- `get_kpi_collection()`: KPI 컬렉션
- `get_collection_info(collection)`: 컬렉션 정보

**사용 예시**:
```python
from ingestion.chroma_client import get_reports_collection

collection = get_reports_collection()
print(f"총 문서 수: {collection.count()}")
```

---

### 3. ingest_reports.py - 보고서 Ingestion

**주요 함수**:

#### `ingest_reports(chunks, api_key, batch_size=100)`
보고서 청크를 Chroma Cloud에 업로드

**입력 형식**:
```json
[
  {
    "id": "chunk_001",
    "chunk_text": "주요 업무 성과...",
    "metadata": {
      "report_type": "daily",
      "date": "2024-01-15",
      "owner": "홍길동",
      "chunk_type": "task"
    }
  }
]
```

**반환값**:
```json
{
  "success": true,
  "collection": "reports",
  "uploaded": 10,
  "total_documents": 50
}
```

#### `query_reports(query_text, n_results=5, where=None)`
보고서 컬렉션 검색

**사용 예시**:
```python
from ingestion.ingest_reports import query_reports

# 기본 검색
results = query_reports("주요 업무 성과", n_results=5)

# 메타데이터 필터링
results = query_reports(
    "업무 성과",
    n_results=5,
    where={"report_type": "daily"}
)
```

---

### 4. ingest_kpi.py - KPI Ingestion

**주요 함수**:

#### `ingest_kpi(chunks, api_key, batch_size=100)`
KPI 청크를 Chroma Cloud에 업로드

**입력 형식**:
```json
[
  {
    "id": "kpi_001",
    "chunk_text": "KPI 이름: 손해율\n카테고리: 재무\n...",
    "metadata": {
      "kpi_name": "손해율",
      "category": "재무",
      "page_index": 3,
      "dataset": "kpi"
    }
  }
]
```

#### `query_kpi(query_text, n_results=5, where=None)`
KPI 컬렉션 검색

---

### 5. init_ingest.py - 전체 실행 스크립트

**처리 흐름**:
1. `.env`에서 `OPENAI_API_KEY` 로드
2. Chroma Cloud 연결 확인
3. `output/실적 보고서 양식_performance_chunks.json` 로드
4. Reports 컬렉션에 업로드
5. `output/KPI 자료_kpi_chunks.json` 로드
6. KPI 컬렉션에 업로드
7. 최종 컬렉션 정보 출력

**실행 방법**:
```bash
cd backend
python -m ingestion.init_ingest
```

---

## 🚀 사용 시나리오

### 시나리오 1: 보고서 파싱 후 업로드

```bash
# 1단계: 보고서 PDF 파싱
cd backend
python test_report_parser.py

# 출력: output/실적 보고서 양식_performance_chunks.json

# 2단계: Ingestion
python -m ingestion.init_ingest
```

### 시나리오 2: KPI 파싱 후 업로드

```bash
# 1단계: KPI PDF 파싱
cd backend
python test_kpi_pipeline.py

# 출력: output/KPI 자료_kpi_chunks.json

# 2단계: Ingestion
python -m ingestion.init_ingest
```

### 시나리오 3: 전체 파이프라인 테스트

```bash
cd backend
python test_ingestion_pipeline.py
```

**테스트 내용**:
1. ✅ Chroma Cloud 연결 확인
2. ✅ 보고서 ingestion
3. ✅ KPI ingestion
4. ✅ 검색 테스트 (보고서 + KPI)
5. ✅ 최종 컬렉션 현황 출력

---

## 📊 데이터 흐름

### 입력 데이터 (JSON)

```
output/
├── 실적 보고서 양식_performance_chunks.json
└── KPI 자료_kpi_chunks.json
```

### 처리 과정

```
JSON 파일
  ↓
load_chunks_from_json()
  ↓ (chunk_id → id, text → chunk_text 변환)
[
  {"id": "...", "chunk_text": "...", "metadata": {...}},
  ...
]
  ↓
embed_texts() → [vector1, vector2, ...]
  ↓
collection.upsert(
  ids=[...],
  embeddings=[...],
  documents=[...],
  metadatas=[...]
)
  ↓
Chroma Cloud 저장 완료
```

### Chroma Cloud 저장 구조

**Reports 컬렉션**:
```python
{
  "ids": ["chunk_001", "chunk_002", ...],
  "embeddings": [[0.1, 0.2, ...], [0.3, 0.4, ...], ...],  # 3072차원
  "documents": ["주요 업무 성과...", "영업 실적...", ...],
  "metadatas": [
    {"report_type": "daily", "date": "2024-01-15", ...},
    {"report_type": "weekly", "date": "2024-01-20", ...},
    ...
  ]
}
```

**KPI 컬렉션**:
```python
{
  "ids": ["kpi_001", "kpi_002", ...],
  "embeddings": [[0.5, 0.6, ...], [0.7, 0.8, ...], ...],  # 3072차원
  "documents": ["KPI 이름: 손해율...", "KPI 이름: 보험료 수입...", ...],
  "metadatas": [
    {"kpi_name": "손해율", "category": "재무", ...},
    {"kpi_name": "보험료 수입", "category": "영업", ...},
    ...
  ]
}
```

---

## 🔍 검색 API

### 기본 검색

```python
from ingestion import query_reports, query_kpi

# 보고서 검색
results = query_reports("주요 업무 성과", n_results=5)

# KPI 검색
results = query_kpi("손해율 지표", n_results=5)
```

### 메타데이터 필터링

```python
# 특정 날짜의 보고서만 검색
results = query_reports(
    "업무 성과",
    n_results=5,
    where={"date": "2024-01-15"}
)

# 특정 카테고리의 KPI만 검색
results = query_kpi(
    "손해율",
    n_results=5,
    where={"category": "재무"}
)
```

### 검색 결과 구조

```python
{
  "ids": [["chunk_001", "chunk_002", ...]],
  "documents": [["문서1 텍스트", "문서2 텍스트", ...]],
  "metadatas": [[{...}, {...}, ...]],
  "distances": [[0.1234, 0.2345, ...]]  # 거리 (낮을수록 유사)
}
```

---

## ⚙️ 설정 및 환경변수

### .env 파일

```bash
OPENAI_API_KEY=sk-proj-...
```

### Chroma Cloud 설정 (코드 내 고정)

```python
# ingestion/chroma_client.py
CHROMA_API_KEY = "ck-DHJSd4oXoeXytDsQKvgfqAf7MeWddhbovykybeJxXfRu"
CHROMA_TENANT = "87acc175-c5c2-44df-97ff-c0b914e35994"
CHROMA_DATABASE = "Virtual_Assistant"
```

### 임베딩 모델 설정 (코드 내 고정)

```python
# ingestion/embed.py
EMBEDDING_MODEL = "text-embedding-3-large"
EMBEDDING_DIMENSION = 3072
```

---

## 🐛 문제 해결

### 1. Chroma Cloud 연결 실패

**증상**:
```
chromadb.errors.InvalidCredentialsError
```

**해결**:
- `ingestion/chroma_client.py`의 API 키, tenant, database 확인
- 인터넷 연결 상태 확인

---

### 2. OpenAI API 오류

**증상**:
```
openai.error.AuthenticationError
```

**해결**:
- `.env` 파일의 `OPENAI_API_KEY` 확인
- API 키 유효성 및 잔액 확인

---

### 3. JSON 파일 로드 실패

**증상**:
```
FileNotFoundError: output/...chunks.json
```

**해결**:
- `output/` 폴더 존재 확인
- 청크 JSON 파일 생성 확인:
  ```bash
  python test_report_parser.py
  python test_kpi_pipeline.py
  ```

---

### 4. 임베딩 생성 느림

**증상**:
- 배치 처리가 느림

**해결**:
- `batch_size` 조정 (기본값: 100):
  ```python
  ingest_reports(chunks, batch_size=50)
  ```

---

### 5. 메타데이터 타입 오류

**증상**:
```
TypeError: Object of type date is not JSON serializable
```

**해결**:
- 메타데이터의 `date` 객체를 문자열로 변환:
  ```python
  metadata["date"] = str(metadata["date"])
  ```

---

## 📈 성능 최적화

### 배치 크기 조정

```python
# 빠른 업로드 (큰 배치)
ingest_reports(chunks, batch_size=200)

# 안정적인 업로드 (작은 배치)
ingest_reports(chunks, batch_size=50)
```

### 병렬 처리 (향후 구현 예정)

```python
# 멀티스레딩으로 임베딩 생성 속도 향상
# TODO: concurrent.futures 사용
```

---

## 🔐 보안 고려사항

1. **API 키 관리**
   - `.env` 파일을 `.gitignore`에 추가
   - 환경변수로 관리
   - 절대 코드에 하드코딩 금지

2. **Chroma Cloud 크레덴셜**
   - 현재 코드 내 하드코딩 (임시)
   - 향후 환경변수로 이동 권장

3. **데이터 검증**
   - 업로드 전 메타데이터 검증
   - 청크 ID 중복 체크

---

## 📝 다음 단계

### 단기 (1주)
- [ ] 메타데이터 스키마 검증 추가
- [ ] 에러 핸들링 강화
- [ ] 로깅 시스템 구축

### 중기 (1개월)
- [ ] FastAPI 엔드포인트 추가
- [ ] 청크 ID 관리 시스템
- [ ] 업로드 히스토리 추적

### 장기 (3개월)
- [ ] 멀티모달 임베딩 지원
- [ ] 하이브리드 검색 (키워드 + 벡터)
- [ ] 자동 재색인 파이프라인

---

## 📞 참고 자료

- **Chroma 공식 문서**: https://docs.trychroma.com/
- **OpenAI Embeddings**: https://platform.openai.com/docs/guides/embeddings
- **프로젝트 README**: `backend/ingestion/README.md`

---

**작성자**: AI Assistant  
**최종 업데이트**: 2025-11-17

