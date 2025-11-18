# ✅ KPI 파이프라인 구현 완료

## 개요

보험사 KPI 자료 PDF를 Vision API로 구조화하여 RAG용 청크로 변환하는 전용 파이프라인을 구현했습니다.

**핵심 특징:**
- ✅ Report 모듈과 완전 분리
- ✅ GPT-4o Vision 사용
- ✅ 페이지별 구조화
- ✅ Raw → Canonical → Chunks 파이프라인
- ✅ 풍부한 메타데이터
- ✅ Vector DB 준비 완료

## 파일 구조

```
backend/app/domain/kpi/
├── __init__.py              # 모듈 export (38줄)
├── schemas.py               # Pydantic 스키마 (90줄)
├── vision_service.py        # PDF → Vision → Raw JSON (180줄)
├── normalize_service.py     # Raw → Canonical 변환 (160줄)
├── chunker.py              # Canonical → 청크 (180줄)
├── metadata.py             # 메타데이터 생성 (120줄)
└── README.md               # 사용 가이드 (200줄)

backend/
└── test_kpi_pipeline.py    # E2E 테스트 (220줄)
```

**총 코드 라인 수**: 약 1,188줄

## 파이프라인 플로우

```
┌─────────────────┐
│  KPI PDF 파일   │
│  (12 페이지)    │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────┐
│ KPIVisionService            │
│ - pdf_to_images()           │
│ - extract_page() × N        │
│ - GPT-4o Vision 호출        │
└────────┬────────────────────┘
         │
         ▼
┌─────────────────────────────┐
│ KPIRawDocument              │
│ {                           │
│   "문서제목": "...",        │
│   "총페이지수": 12,         │
│   "pages": [...]            │
│ }                           │
└────────┬────────────────────┘
         │
         ▼
┌─────────────────────────────┐
│ normalize_kpi_document()    │
│ - KPI 항목 펼치기           │
│ - 표 데이터 연결            │
│ - UUID 생성                 │
└────────┬────────────────────┘
         │
         ▼
┌─────────────────────────────┐
│ List[CanonicalKPI]          │
│ [                           │
│   {kpi_id, kpi_name, ...},  │
│   {...},                    │
│   ...                       │
│ ]                           │
└────────┬────────────────────┘
         │
         ▼
┌─────────────────────────────┐
│ build_kpi_chunks()          │
│ - 텍스트 구성               │
│ - 표 flatten                │
│ - 태그 생성                 │
└────────┬────────────────────┘
         │
         ▼
┌─────────────────────────────┐
│ List[Dict] (청크)           │
│ [                           │
│   {chunk_id, text, tags},   │
│   {...},                    │
│   ...                       │
│ ]                           │
└────────┬────────────────────┘
         │
         ▼
┌─────────────────────────────┐
│ enhance_chunks_with_        │
│ metadata()                  │
│ - 메타데이터 생성           │
│ - 키워드 추출               │
└────────┬────────────────────┘
         │
         ▼
┌─────────────────────────────┐
│ 최종 청크 (메타데이터 포함) │
│ [                           │
│   {                         │
│     chunk_id,               │
│     text,                   │
│     metadata: {...}         │
│   }                         │
│ ]                           │
└─────────────────────────────┘
```

## 주요 컴포넌트

### 1. schemas.py - 데이터 구조

**Raw 스키마 (Vision 출력)**:
```python
class KPIRawItem:
    kpi_name: str
    category: str
    unit: str
    values: str
    delta: str
    설명: str

class KPIPage:
    page_index: int
    kpi_items: List[KPIRawItem]
    tables: List[Dict]
    text_summary: str
    error: Optional[str]

class KPIRawDocument:
    title: str
    total_pages: int
    pages: List[KPIPage]
```

**Canonical 스키마 (정규화)**:
```python
class CanonicalKPI:
    kpi_id: str               # UUID
    page_index: int
    kpi_name: str
    category: str
    unit: str
    values: str
    delta: str
    description: str
    table: Optional[Dict | List]
    raw_text_summary: str
    metadata: Dict
```

### 2. vision_service.py - Vision 처리

**주요 함수**:
```python
class KPIVisionService:
    def pdf_to_images(pdf_path, dpi=200) -> List[bytes]
    def extract_page(img_bytes, page_index) -> KPIPage
    def process_pdf(pdf_path, title) -> KPIRawDocument
```

**특징**:
- PyMuPDF로 페이지별 이미지 변환
- GPT-4o Vision으로 구조화
- response_format={"type": "json_object"} 사용
- 오류 페이지 Fallback 처리

### 3. normalize_service.py - 정규화

**주요 함수**:
```python
def normalize_kpi_document(raw_doc) -> List[CanonicalKPI]
def _normalize_kpi_item(...) -> CanonicalKPI
def _create_table_kpi(...) -> CanonicalKPI
def get_normalization_stats(canonical_kpis) -> dict
```

**처리 로직**:
- 페이지별 KPI 항목 펼치기
- 표 데이터 연결
- 설명 + 요약 결합
- UUID 자동 생성

### 4. chunker.py - 청킹

**주요 함수**:
```python
def build_kpi_chunks(kpis) -> List[Dict]
def _create_kpi_chunk(kpi) -> Dict
def _flatten_table(table) -> str
def get_chunk_statistics(chunks) -> Dict
```

**청크 구조**:
```python
{
  "chunk_id": "uuid",
  "kpi_id": "uuid",
  "page_index": 0,
  "text": "[KPI] 신규계약률\n카테고리: 영업\n값: 85.2 (%)\n...",
  "source": "kpi_pdf",
  "tags": ["신규계약률", "영업", "%"],
  "metadata": {}
}
```

### 5. metadata.py - 메타데이터

**주요 함수**:
```python
def build_kpi_metadata(chunk) -> Dict
def enhance_chunks_with_metadata(chunks) -> List[Dict]
def get_metadata_summary(chunks) -> Dict
```

**메타데이터 구조**:
```python
{
  "dataset": "kpi",
  "source": "kpi_pdf",
  "kpi_id": "uuid",
  "kpi_name": "신규계약률",
  "category": "영업",
  "unit": "%",
  "page_index": 0,
  "keywords": ["신규계약률", "영업", "%"]
}
```

## 사용 방법

### CLI 테스트

```bash
cd backend
python test_kpi_pipeline.py "Data/보험사_KPI_자료.pdf"
```

**출력**:
```
🚀 KPI 파이프라인 테스트 시작
📂 파일: Data/보험사_KPI_자료.pdf

⏳ Step 1: Vision API로 PDF 처리 중...
✅ PDF를 12개 페이지로 변환했습니다.
⏳ 페이지 1 처리 중...
✅ 페이지 1 완료 (KPI 3개)
...

⏳ Step 2: Canonical KPI 변환 중...
✅ 정규화 완료: 45개 CanonicalKPI 생성
📊 총 KPI 수: 45
📊 카테고리별:
   - 영업: 15개
   - 재무: 12개
   - 운영: 18개

⏳ Step 3: 청킹 생성 중...
✅ 청킹 완료: 45개 청크 생성

⏳ Step 4: 메타데이터 추가 중...
✅ 메타데이터 추가 완료: 45개 청크

📋 청크 샘플 (처음 3개)
...

💾 결과 파일 저장 중...
1. Raw JSON: output/보험사_KPI_자료_kpi_raw.json
2. Canonical KPI: output/보험사_KPI_자료_kpi_canonical.json
3. 최종 청크: output/보험사_KPI_자료_kpi_chunks.json
```

### Python 코드

```python
from app.domain.kpi import (
    KPIVisionService,
    normalize_kpi_document,
    build_kpi_chunks,
    enhance_chunks_with_metadata
)

# Step 1: Vision
service = KPIVisionService(api_key="your_key")
raw_doc = service.process_pdf("Data/KPI.pdf")

# Step 2: Normalize
canonical_kpis = normalize_kpi_document(raw_doc)

# Step 3: Chunk
chunks = build_kpi_chunks(canonical_kpis)

# Step 4: Metadata
final_chunks = enhance_chunks_with_metadata(chunks)

print(f"총 {len(final_chunks)}개 청크 생성")
```

## Vector DB 통합 예시

```python
import chromadb
from chromadb.utils import embedding_functions

# ChromaDB 초기화
client = chromadb.Client()
openai_ef = embedding_functions.OpenAIEmbeddingFunction(
    api_key="your_key",
    model_name="text-embedding-3-large"
)

collection = client.create_collection(
    name="kpi_documents",
    embedding_function=openai_ef
)

# 청크 추가
for chunk in final_chunks:
    collection.add(
        ids=[chunk["chunk_id"]],
        documents=[chunk["text"]],
        metadatas=[chunk["metadata"]]
    )

# 검색
results = collection.query(
    query_texts=["신규계약"],
    n_results=5,
    where={"category": "영업"}
)
```

## Report vs KPI 비교

| 항목 | Report 모듈 | KPI 모듈 |
|------|------------|----------|
| **대상** | 일일/주간/월간/실적 보고서 | KPI 자료 (다페이지) |
| **파일 수** | 4가지 타입, 1페이지 | 1가지 타입, 다페이지 |
| **스키마** | 타입별 고정 스키마 | 유연한 KPI 스키마 |
| **처리** | 페이지 전체 한번에 | 페이지별 순차 처리 |
| **Canonical** | CanonicalReport (단일) | List[CanonicalKPI] (다수) |
| **청킹** | task/kpi/issue/plan/summary | KPI 항목 단위 |

## 기술 스택

- **Vision**: GPT-4o (gpt-4o)
- **PDF**: PyMuPDF (fitz)
- **Schema**: Pydantic v2
- **Chunking**: Python (LLM 미사용)
- **Vector DB**: ChromaDB 준비 완료

## 장점

### 1. 완전 분리
- Report 모듈과 독립적
- 코드 충돌 없음
- 확장 용이

### 2. 페이지별 처리
- 대용량 문서 지원
- 병렬 처리 가능
- 오류 격리

### 3. 풍부한 메타데이터
- 페이지 인덱스
- 카테고리/단위
- 키워드 자동 추출

### 4. Vector DB 준비
- 청크 ID 관리
- 메타데이터 검색
- 필터링 지원

## 다음 단계

### Phase 1: Vector DB 통합
```python
# backend/app/infrastructure/vectordb/kpi_store.py
class KPIVectorStore:
    def add_chunks(self, chunks)
    def search(self, query, filters)
    def delete_by_kpi_id(self, kpi_id)
```

### Phase 2: API 엔드포인트
```python
# backend/app/api/v1/endpoints/kpi.py
@router.post("/kpi/parse")
async def parse_kpi_document(file: UploadFile)

@router.get("/kpi/search")
async def search_kpi(query: str, category: str)
```

### Phase 3: 배치 처리
```python
# backend/app/services/kpi_batch.py
async def process_kpi_directory(directory_path)
async def update_all_embeddings()
```

## 출력 파일

테스트 실행 시 `backend/output/` 폴더에 3개 파일 생성:

1. **`{filename}_kpi_raw.json`**: Vision API 원본 출력
2. **`{filename}_kpi_canonical.json`**: 정규화된 KPI 리스트
3. **`{filename}_kpi_chunks.json`**: 최종 청크 (메타데이터 포함)

## 트러블슈팅

### Q: Vision API 오류
```
AuthenticationError: Incorrect API key
```
**해결**: `.env` 파일에 `OPENAI_API_KEY` 설정 확인

### Q: 페이지 파싱 오류
```
페이지 5 처리 오류: ...
```
**해결**: 해당 페이지는 `error` 필드로 기록되고 건너뜀 (Fallback 처리)

### Q: 표 flatten 오류
```
표 flatten 오류: ...
```
**해결**: 표는 문자열로 변환되어 text에 포함됨

## 문서

- **사용 가이드**: `backend/app/domain/kpi/README.md`
- **구현 요약**: `backend/KPI_PIPELINE_IMPLEMENTATION.md`
- **테스트 스크립트**: `backend/test_kpi_pipeline.py`

---

**구현 완료일**: 2025-11-17  
**총 코드 라인**: 약 1,188줄  
**상태**: ✅ 완료 및 테스트 가능

모든 요구사항을 충족하며 구현이 완료되었습니다! 🎉

