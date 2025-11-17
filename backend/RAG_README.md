# RAG 문서 처리 시스템

PDF 문서를 처리하여 ChromaDB에 저장하고 RAG 기반 질의응답을 수행하는 모듈입니다.

## 📁 구조

```
backend/
├── app/
│   ├── domain/
│   │   └── rag/                      # 🆕 RAG 모듈
│   │       ├── __init__.py
│   │       ├── config.py             # RAG 전용 설정
│   │       ├── schemas.py            # Pydantic 스키마
│   │       ├── pdf_processor.py      # PDF 처리
│   │       ├── document_converter.py # 마크다운 변환
│   │       ├── vector_store.py       # 벡터 저장소
│   │       ├── retriever.py          # RAG 검색
│   │       └── cli.py                # CLI 인터페이스
│   └── api/
│       └── v1/
│           └── endpoints/
│               └── rag.py            # API 엔드포인트
├── internal_docs/                    # 🆕 내부 문서 디렉토리
│   ├── uploads/                      # 업로드된 PDF
│   ├── processed/                    # 처리된 JSON
│   └── chroma/                       # ChromaDB 저장소
└── rag_requirements.txt              # 추가 패키지
```

## 🚀 설치

### 1. 의존성 설치

```bash
cd Virtual-Assistant/backend
pip install -r rag_requirements.txt
```

### 2. 환경변수 설정

`.env` 파일에 다음 변수가 필요합니다:

```env
OPENAI_API_KEY=your_openai_api_key_here
```

## 📖 사용법

### CLI 사용

#### 1. PDF 업로드 및 처리

```bash
cd Virtual-Assistant/backend
python -m app.domain.rag.cli upload path/to/document.pdf
```

예시:
```bash
python -m app.domain.rag.cli upload "C:\Users\301\Documents\company_manual.pdf"
```

#### 2. 대화형 질의응답

```bash
python -m app.domain.rag.cli query
```

대화형 모드에서 질문을 입력하고 답변을 받을 수 있습니다.
종료하려면 `exit` 또는 `quit`를 입력하세요.

#### 3. 단일 질문

```bash
python -m app.domain.rag.cli query "회사의 비전은 무엇인가요?"
```

#### 4. 시스템 통계 확인

```bash
python -m app.domain.rag.cli stats
```

### API 사용 (선택사항)

#### API 엔드포인트 등록

`backend/app/api/v1/router.py` 파일에 다음 코드를 추가하세요:

```python
from app.api.v1.endpoints.rag import router as rag_router

api_router.include_router(
    rag_router,
    prefix="/rag",
    tags=["RAG"]
)
```

#### API 엔드포인트

1. **PDF 업로드**
   ```
   POST /api/v1/rag/upload
   Content-Type: multipart/form-data
   Body: file (PDF)
   ```

2. **질의응답**
   ```
   POST /api/v1/rag/query
   Content-Type: application/json
   Body: {
     "query": "질문 내용",
     "top_k": 3
   }
   ```

3. **통계 조회**
   ```
   GET /api/v1/rag/stats
   ```

4. **문서 삭제**
   ```
   DELETE /api/v1/rag/document/{document_id}
   ```

5. **컬렉션 초기화**
   ```
   POST /api/v1/rag/reset
   ```

## 🔧 설정

RAG 시스템의 설정은 `app/domain/rag/config.py`에서 관리됩니다:

```python
# 청크 설정
RAG_CHUNK_SIZE: int = 400          # 청크 크기 (토큰)
RAG_CHUNK_OVERLAP: int = 50        # 청크 오버랩 (토큰)

# 검색 설정
RAG_TOP_K: int = 3                 # 검색할 문서 수

# 모델 설정
KOREAN_EMBEDDING_MODEL = "jhgan/ko-sroberta-multitask"
OPENAI_MODEL = "gpt-4o"
```

## 📊 처리 흐름

### PDF → 벡터DB

1. **PDF 파싱** (PyMuPDF + pdfplumber)
   - 텍스트 추출
   - 표 구조 인식 및 JSON 변환
   - 이미지/차트 추출

2. **이미지 분석** (GPT-4 Vision)
   - 차트, 그래프 설명 생성

3. **문서 변환**
   - 마크다운 형식으로 변환
   - 시맨틱 청킹 (300~500 토큰)

4. **임베딩** (KoSentenceBERT)
   - 한국어 특화 임베딩 생성

5. **저장** (ChromaDB)
   - 벡터 데이터베이스에 저장

### 질의응답

1. **쿼리 임베딩**
   - 질문을 벡터로 변환

2. **유사도 검색**
   - ChromaDB에서 Top-K 검색

3. **답변 생성**
   - OpenAI GPT-4o로 답변 생성

4. **결과 반환**
   - 답변 + 참고 문서 정보

## 🎯 특징

✅ **완전히 독립적인 모듈**: 기존 코드를 수정하지 않음
✅ **한국어 최적화**: KoSentenceBERT 임베딩 사용
✅ **다양한 컨텐츠 지원**: 텍스트, 표, 이미지/차트
✅ **시맨틱 청킹**: LangChain을 활용한 의미 단위 분할
✅ **CLI & API**: 터미널과 API 모두 지원

## 🔍 예시

### CLI 사용 예시

```bash
# 1. PDF 업로드
$ python -m app.domain.rag.cli upload manual.pdf

처리 결과
┏━━━━━━━━━━━━━━━┳━━━━━━━━━━┓
┃ 항목          ┃ 값       ┃
┡━━━━━━━━━━━━━━━╇━━━━━━━━━━┩
│ 파일명        │ manual.pdf│
│ 총 페이지     │ 50       │
│ 추출된 컨텐츠 │ 85       │
│ 생성된 청크   │ 120      │
│ 저장된 청크   │ 120      │
└───────────────┴──────────┘

✓ 문서 처리 완료!

# 2. 질의응답
$ python -m app.domain.rag.cli query

질문> 회사의 비전은 무엇인가요?

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
답변

[문서 1]에 따르면, 회사의 비전은 "AI 기술로 
세상을 더 나은 곳으로 만든다"입니다...

참고 문서 (3개):
  1. manual.pdf (페이지 5) - 유사도: 0.87
  2. manual.pdf (페이지 12) - 유사도: 0.82
  3. manual.pdf (페이지 8) - 유사도: 0.78

처리 시간: 2.34초
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

## ⚠️ 주의사항

1. **OPENAI_API_KEY 필수**: `.env` 파일에 설정 필요
2. **첫 실행 시 모델 다운로드**: KoSentenceBERT 모델이 자동으로 다운로드됨 (~500MB)
3. **PDF 품질**: 스캔된 PDF는 텍스트 추출이 제한될 수 있음
4. **API Key 비용**: OpenAI API 호출 시 비용 발생

## 🐛 문제 해결

### 1. 모듈을 찾을 수 없음 오류

```bash
pip install -r rag_requirements.txt
```

### 2. OPENAI_API_KEY 오류

`.env` 파일에 API 키가 설정되어 있는지 확인:

```env
OPENAI_API_KEY=sk-...
```

### 3. 한국어 임베딩 모델 다운로드 오류

인터넷 연결을 확인하고 재시도:

```python
from sentence_transformers import SentenceTransformer
model = SentenceTransformer("jhgan/ko-sroberta-multitask")
```

### 4. PDF 처리 오류

PDF 파일이 손상되지 않았는지 확인하고, 다른 PDF 뷰어에서 열리는지 테스트

## 📝 라이선스

기존 프로젝트와 동일 (MIT License)

