# RAG 시스템 사용 가이드

## 빠른 시작

### 1. 설치

```bash
# 1. 디렉토리 이동
cd Virtual-Assistant/backend

# 2. 패키지 설치
pip install -r rag_requirements.txt

# 3. 환경변수 설정 (.env 파일에 추가)
# OPENAI_API_KEY=your_key_here
```

# internal_docs/uploads 폴더의 모든 파일 처리
python -m app.domain.rag.cli upload internal_docs/uploads

#단일 파일 처리할 때
# PDF 파일
python -m app.domain.rag.cli upload 파일경로.pdf

# 텍스트 파일
python -m app.domain.rag.cli upload 파일경로.txt

# 마크다운 파일
python -m app.domain.rag.cli upload 파일경로.md

#질의응답 시작
python -m app.domain.rag.cli query

### 2. PDF 업로드

```bash
# Windows
python -m app.domain.rag.cli upload "C:\Users\301\Documents\manual.pdf"

# 또는 상대 경로
python -m app.domain.rag.cli upload "../documents/manual.pdf"
```

### 3. 질의응답

```bash
# 대화형 모드
python -m app.domain.rag.cli query

# 단일 질문
python -m app.domain.rag.cli query "회사의 비전은 무엇인가요?"
```

### 4. 통계 확인

```bash
python -m app.domain.rag.cli stats
```

## 상세 기능

### CLI 명령어

#### upload - PDF 업로드 및 처리
```bash
python -m app.domain.rag.cli upload <pdf_path>
```

**처리 과정:**
1. PDF 파싱 (텍스트, 표, 이미지 추출)
2. 이미지는 GPT-4 Vision으로 설명 생성
3. 마크다운 형식으로 변환
4. 300~500 토큰 단위로 청킹
5. KoSentenceBERT로 임베딩
6. ChromaDB에 저장
7. 처리 결과를 `internal_docs/processed/` 에 JSON 저장

**출력 예시:**
```
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
```

#### query - 질의응답
```bash
# 대화형 모드
python -m app.domain.rag.cli query

# 단일 질문
python -m app.domain.rag.cli query "질문 내용"

# Top-K 지정
python -m app.domain.rag.cli query "질문 내용" --top-k 5
```

**대화형 모드:**
- 연속적으로 질문 가능
- `exit` 또는 `quit` 입력 시 종료
- Ctrl+C로도 종료 가능

**출력 예시:**
```
질문> 회사의 비전은 무엇인가요?

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
답변

[문서 1]에 따르면, 회사의 비전은...

참고 문서 (3개):
  1. manual.pdf (페이지 5) - 유사도: 0.87
  2. manual.pdf (페이지 12) - 유사도: 0.82
  3. manual.pdf (페이지 8) - 유사도: 0.78

처리 시간: 2.34초
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

#### stats - 시스템 통계
```bash
python -m app.domain.rag.cli stats
```

**출력 예시:**
```
RAG 시스템 통계
┏━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ 항목          ┃ 값                         ┃
┡━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ 저장된 청크 수│ 120                        │
│ 컬렉션 이름   │ rag_documents              │
│ 임베딩 모델   │ jhgan/ko-sroberta-multitask│
│ LLM 모델      │ gpt-4o                     │
│ Top-K         │ 3                          │
└───────────────┴────────────────────────────┘
```

## API 사용 (선택사항)

### 라우터 등록

`Virtual-Assistant/backend/app/api/v1/router.py` 파일을 열고 다음을 추가:

```python
from app.api.v1.endpoints.rag import router as rag_router

# 기존 라우터 등록 아래에 추가
api_router.include_router(
    rag_router,
    prefix="/rag",
    tags=["RAG"]
)
```

### API 엔드포인트

#### 1. PDF 업로드
```http
POST http://localhost:8000/api/v1/rag/upload
Content-Type: multipart/form-data

file: (PDF 파일)
```

**응답:**
```json
{
  "success": true,
  "message": "PDF 처리 완료",
  "filename": "manual.pdf",
  "total_pages": 50,
  "total_chunks": 120,
  "processed_file_path": "./internal_docs/processed/manual.json"
}
```

#### 2. 질의응답
```http
POST http://localhost:8000/api/v1/rag/query
Content-Type: application/json

{
  "query": "회사의 비전은 무엇인가요?",
  "top_k": 3
}
```

**응답:**
```json
{
  "query": "회사의 비전은 무엇인가요?",
  "answer": "[문서 1]에 따르면, 회사의 비전은...",
  "retrieved_chunks": [
    {
      "text": "...",
      "metadata": {
        "filename": "manual.pdf",
        "page_number": 5,
        "content_type": "text"
      },
      "score": 0.87
    }
  ],
  "processing_time": 2.34,
  "model_used": "gpt-4o"
}
```

#### 3. 통계 조회
```http
GET http://localhost:8000/api/v1/rag/stats
```

#### 4. 문서 삭제
```http
DELETE http://localhost:8000/api/v1/rag/document/{filename}
```

#### 5. 컬렉션 초기화
```http
POST http://localhost:8000/api/v1/rag/reset
```

## 설정 커스터마이징

`Virtual-Assistant/backend/app/domain/rag/config.py` 파일에서 설정 변경:

```python
class RAGConfig(BaseSettings):
    # 청크 설정
    RAG_CHUNK_SIZE: int = 400          # 변경 가능
    RAG_CHUNK_OVERLAP: int = 50        # 변경 가능
    
    # 검색 설정
    RAG_TOP_K: int = 3                 # 변경 가능 (1~10)
    
    # 모델 설정
    KOREAN_EMBEDDING_MODEL: str = "jhgan/ko-sroberta-multitask"
    OPENAI_MODEL: str = "gpt-4o"
    OPENAI_TEMPERATURE: float = 0.7    # 변경 가능 (0~1)
```

## 문제 해결

### Q: "No module named 'fitz'" 오류
```bash
pip install PyMuPDF
```

### Q: "sentence_transformers not found" 오류
```bash
pip install sentence-transformers
```

### Q: OPENAI_API_KEY 오류
`.env` 파일에 API 키 추가:
```env
OPENAI_API_KEY=sk-your-key-here
```

### Q: 한국어 임베딩 모델 다운로드 느림
첫 실행 시 약 500MB 모델이 다운로드됩니다. 인터넷 연결을 확인하세요.

### Q: PDF에서 한글이 깨짐
PyMuPDF가 한글을 지원하지만, 일부 PDF는 인코딩 문제가 있을 수 있습니다.
다른 PDF로 테스트해보세요.

## 팁

### 1. 여러 문서 업로드
```bash
for %%f in (C:\docs\*.pdf) do python -m app.domain.rag.cli upload "%%f"
```

### 2. 질문 스크립트 작성
```bash
python -m app.domain.rag.cli query "질문 1"
python -m app.domain.rag.cli query "질문 2"
python -m app.domain.rag.cli query "질문 3"
```

### 3. 로그 확인
Python 로깅이 활성화되어 있어 처리 과정을 확인할 수 있습니다.

## 다음 단계

1. ✅ CLI로 PDF 업로드 및 테스트
2. ✅ CLI로 질의응답 테스트
3. (선택) API 라우터 등록
4. (선택) 프론트엔드 연동

## 지원

문제가 발생하면 이슈를 남겨주세요!

