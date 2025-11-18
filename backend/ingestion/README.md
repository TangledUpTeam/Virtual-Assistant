# Ingestion Pipeline

Chroma Cloud에 문서를 임베딩하고 업로드하는 파이프라인

## 📁 구조

```
ingestion/
├── __init__.py           # 모듈 export
├── embed.py              # OpenAI 임베딩 생성
├── chroma_client.py      # Chroma Cloud 클라이언트
├── ingest_reports.py     # 보고서 ingestion
├── ingest_kpi.py         # KPI ingestion
├── init_ingest.py        # 전체 실행 스크립트
├── test_query.py         # 검색 테스트
└── README.md             # 이 파일
```

## 🚀 사용법

### 1. 의존성 설치

```bash
cd backend
pip install -r requirements.txt
```

필요한 패키지:
- `openai==1.57.0` - 임베딩 생성
- `chromadb==0.5.23` - Chroma Cloud 연동

### 2. 환경변수 설정

`.env` 파일에 OpenAI API 키 추가:

```bash
OPENAI_API_KEY=sk-proj-...
```

### 3. 전체 파이프라인 실행

```bash
cd backend
python -m ingestion.init_ingest
```

이 스크립트는:
1. `output/실적 보고서 양식_performance_chunks.json` 로드
2. `output/KPI 자료_kpi_chunks.json` 로드
3. Reports 컬렉션에 업로드
4. KPI 컬렉션에 업로드

### 4. 검색 테스트

```bash
cd backend
python -m ingestion.test_query
```

## 🔧 개별 사용법

### 보고서 Ingestion

```python
from ingestion import ingest_reports

chunks = [
    {
        "id": "chunk_001",
        "chunk_text": "주요 업무 성과...",
        "metadata": {
            "report_type": "daily",
            "date": "2024-01-15",
            "owner": "홍길동"
        }
    },
    ...
]

result = ingest_reports(chunks, api_key="sk-...")
```

### KPI Ingestion

```python
from ingestion import ingest_kpi

chunks = [
    {
        "id": "kpi_001",
        "chunk_text": "KPI 이름: 손해율...",
        "metadata": {
            "kpi_name": "손해율",
            "category": "재무",
            "page_index": 3
        }
    },
    ...
]

result = ingest_kpi(chunks, api_key="sk-...")
```

### 검색

```python
from ingestion import query_reports, query_kpi

# 보고서 검색
results = query_reports("주요 업무 성과", n_results=5)

# KPI 검색
results = query_kpi("손해율 지표", n_results=5)

# 메타데이터 필터링
results = query_reports(
    "업무 성과",
    n_results=5,
    where={"report_type": "daily"}
)
```

## 📊 데이터 구조

### 입력 청크 형식

```json
{
  "id": "unique_chunk_id",
  "chunk_text": "청크 텍스트 내용",
  "metadata": {
    "report_type": "daily",
    "date": "2024-01-15",
    "owner": "홍길동",
    ...
  }
}
```

### Chroma Cloud 저장 형식

- `ids`: 청크 ID 리스트
- `embeddings`: 임베딩 벡터 리스트 (3072차원)
- `documents`: 청크 텍스트 리스트
- `metadatas`: 메타데이터 딕셔너리 리스트

## 🔑 설정 정보

### Chroma Cloud

- **API Key**: `ck-DHJSd4oXoeXytDsQKvgfqAf7MeWddhbovykybeJxXfRu`
- **Tenant**: `87acc175-c5c2-44df-97ff-c0b914e35994`
- **Database**: `Virtual_Assistant`

### 컬렉션

- **reports**: 보고서 문서 컬렉션
- **kpi**: KPI 문서 컬렉션

### 임베딩 모델

- **모델**: `text-embedding-3-large`
- **차원**: 3072
- **제공자**: OpenAI

## 🛠️ API 참조

### embed.py

- `embed_text(text, api_key)`: 단일 텍스트 임베딩
- `embed_texts(texts, api_key, batch_size)`: 배치 임베딩
- `get_embedding_service(api_key)`: 임베딩 서비스 인스턴스

### chroma_client.py

- `get_chroma_service()`: Chroma Cloud 서비스 인스턴스
- `get_reports_collection()`: Reports 컬렉션
- `get_kpi_collection()`: KPI 컬렉션

### ingest_reports.py

- `ingest_reports(chunks, api_key, batch_size)`: 보고서 업로드
- `delete_reports_by_ids(ids)`: 보고서 삭제
- `query_reports(query_text, n_results, where)`: 보고서 검색

### ingest_kpi.py

- `ingest_kpi(chunks, api_key, batch_size)`: KPI 업로드
- `delete_kpi_by_ids(ids)`: KPI 삭제
- `query_kpi(query_text, n_results, where)`: KPI 검색

## 📝 예제 워크플로우

### 1. 보고서 파싱 → Ingestion

```bash
# 1. 보고서 파싱 (이미 구현됨)
cd backend
python test_report_parser.py

# 2. Ingestion
python -m ingestion.init_ingest
```

### 2. KPI 파싱 → Ingestion

```bash
# 1. KPI 파싱 (이미 구현됨)
cd backend
python test_kpi_pipeline.py

# 2. Ingestion
python -m ingestion.init_ingest
```

### 3. 검색 테스트

```bash
cd backend
python -m ingestion.test_query
```

## ⚠️ 주의사항

1. **API 키 보안**: `.env` 파일을 `.gitignore`에 추가하세요
2. **배치 크기**: 기본값 100개, 필요시 조정 가능
3. **임베딩 비용**: text-embedding-3-large는 유료 모델입니다
4. **네트워크**: Chroma Cloud 연결에 안정적인 인터넷 필요
5. **중복 처리**: `upsert` 사용으로 동일 ID는 자동 업데이트

## 🐛 문제 해결

### Chroma Cloud 연결 실패

```python
chromadb.errors.InvalidCredentialsError
```

→ API 키, tenant, database 정보 확인

### OpenAI API 오류

```python
openai.error.AuthenticationError
```

→ `.env` 파일의 `OPENAI_API_KEY` 확인

### 임베딩 생성 느림

→ `batch_size` 조정 (기본값: 100)

```python
ingest_reports(chunks, batch_size=50)
```

## 📞 문의

문제가 발생하면 로그를 확인하고 다음을 체크하세요:
- `.env` 파일 존재 및 API 키 설정
- `output/` 폴더에 청크 JSON 파일 존재
- 인터넷 연결 상태

