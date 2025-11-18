# RAG 시스템 개선 작업 내역

## 📅 작업 일시
2025년 작업 세션

## 🎯 주요 작업 목표
- LangChain & LangSmith 통합
- Threshold 기반 거리도 측정
- LLM Guardrails 구현 (후 제거)
- Small talk vs RAG 자동 분기
- 코드 정리 및 최적화

---

## ✅ 완료된 작업

### 1. LangChain & LangSmith 통합
- **파일**: `retriever.py`
- **변경사항**:
  - LangChain의 파이프 연산자(`|`)를 사용한 RAG 체인 구성
  - LangSmith 추적 활성화 (`@traceable` 데코레이터)
  - LangChain 1.0.x 버전 사용
- **체인 구조**:
  ```python
  chain = (
      RunnablePassthrough()
      | RunnableLambda(retrieve_and_filter)  # 검색 + threshold 필터링
      | RunnableLambda(generate_answer)      # LLM 답변 생성
  )
  ```

### 2. Threshold 기반 거리도 측정
- **파일**: `config.py`, `retriever.py`, `vector_store.py`
- **변경사항**:
  - `RAG_SIMILARITY_THRESHOLD` 설정 추가 (기본값: 0.35)
  - Cosine distance를 similarity score로 변환: `similarity = 1 - (distance / 2.0)`
  - 검색 결과를 threshold 기반으로 필터링
- **현재 설정**: `RAG_SIMILARITY_THRESHOLD = 0.35` (distance 1.3 이하)

### 3. ChromaDB 직접 사용 (LangChain 통합 제거)
- **파일**: `vector_store.py`
- **변경사항**:
  - LangChain Chroma 통합 제거
  - ChromaDB `PersistentClient` 직접 사용
  - Cosine distance metric 명시적 지정
- **이유**: LangChain Chroma가 deprecated되어 직접 사용으로 변경

### 4. Cosine Distance Metric 지정
- **파일**: `vector_store.py`
- **변경사항**:
  - ChromaDB 컬렉션 생성 시 `distance_function="cosine"` 지정
  - 기존 컬렉션의 metric 확인 로직 추가

### 5. Small talk vs RAG 자동 분기
- **파일**: `retriever.py`
- **변경사항**:
  - `needs_search()` 메서드 추가: 질문이 문서 검색이 필요한지 판단
  - Small talk 감지 시 LLM만 사용 (검색 없음)
  - 문서 검색 필요 시 RAG 실행
- **판단 로직**:
  1. 키워드 기반 1차 판단
  2. 애매한 경우 LLM으로 2차 판단

### 6. Similarity Score 터미널 출력
- **파일**: `retriever.py`, `cli.py`
- **변경사항**:
  - 검색 과정에서 모든 score를 `logger.info`로 출력
  - CLI에서 유사도 점수를 색상으로 구분하여 표시
    - 녹색: ≥ 0.7
    - 노란색: ≥ 0.5
    - 빨간색: < 0.5
  - 유사도를 4자리 소수점으로 표시

### 7. Guardrails 완전 제거
- **파일**: `guardrails.py` (삭제), `retriever.py`, `config.py`
- **변경사항**:
  - `guardrails.py` 파일 삭제
  - `retriever.py`에서 Guardrails 관련 코드 제거
  - RAG 체인에서 Guardrails 검증 단계 제거
- **이유**: 버전 충돌로 패키지 설치 불가, 직접 구현했지만 사용하지 않음

### 8. 사용하지 않는 코드 정리
- **제거된 파일**:
  - `test_rag.py` (삭제, `debug_rag.py`로 대체)
- **제거된 메서드** (`retriever.py`):
  - `retrieve()` - 중복 (내부 체인에서 처리)
  - `generate_answer()` - 중복 (내부 체인에서 처리)
  - `query_simple()` - 사용되지 않음
- **제거된 import**:
  - `MessagesPlaceholder` (사용되지 않음)

### 9. RAG API Router 등록
- **파일**: `router.py`
- **변경사항**:
  - RAG 엔드포인트를 `/api/v1/rag` 경로로 등록
  - 누락되어 있던 라우터 등록 추가

### 10. Threshold 조정
- **파일**: `config.py`
- **변경사항**:
  - `RAG_SIMILARITY_THRESHOLD`: 0.5 → 0.35로 변경
  - 더 많은 검색 결과 포함 (distance 1.3 이하)

---

## 📁 파일 구조 변경

### 추가된 파일
- `debug_rag.py` - RAG 시스템 디버깅 유틸리티

### 삭제된 파일
- `guardrails.py` - Guardrails 모듈 (완전 제거)
- `test_rag.py` - 테스트 파일 (debug_rag.py로 대체)

### 주요 수정 파일
- `retriever.py` - LangChain 체인으로 리팩토링, Small talk 분기 추가
- `vector_store.py` - ChromaDB 직접 사용, cosine metric 지정
- `config.py` - Threshold 설정, Guardrails 설정 제거
- `router.py` - RAG 엔드포인트 등록
- `cli.py` - Score 출력 개선

---

## 🔧 설정 변경

### Threshold
```python
RAG_SIMILARITY_THRESHOLD: float = 0.35
```

### ChromaDB Distance Metric
```python
distance_function="cosine"  # 컬렉션 생성 시 지정
```

### LangSmith (선택적)
- 환경변수: `LANGSMITH_API_KEY`, `LANGSMITH_PROJECT`, `LANGSMITH_TRACING`

---

## 📦 패키지 변경

### 추가된 패키지
- `langchain==1.0.7`
- `langchain-core==1.0.5`
- `langchain-community==0.4.1`
- `langchain-text-splitters==1.0.0`
- `langchain-openai==1.0.3`
- `langsmith==0.4.43`
- `rich==13.9.4` (버전 통일)

### 제거된 패키지
- `guardrails-ai` (버전 충돌로 설치하지 않음)
- `langchain-chroma` (ChromaDB 직접 사용으로 변경)

---

## 🎨 주요 기능

### 1. 자동 질문 분류
- Small talk → LLM만 사용
- 문서 검색 필요 → RAG 실행

### 2. Threshold 기반 필터링
- Cosine distance를 similarity score로 변환
- Threshold 미만 결과 자동 필터링

### 3. 상세한 Score 출력
- 검색 과정에서 모든 score 로그 출력
- CLI에서 색상으로 구분된 유사도 표시

---

## 📝 참고사항

### 사용하지 않는 폴더
- `backend/data/uploads` - 비어있음, 사용하지 않음
- `backend/data/chroma` - 이전 설정으로 보임

### 실제 사용 중인 경로
- 업로드: `backend/internal_docs/uploads`
- ChromaDB: `backend/internal_docs/chroma`
- 처리된 파일: `backend/internal_docs/processed`

---

## 🚀 다음 단계 (선택사항)

1. 사용하지 않는 `data/` 폴더 정리
2. Guardrails 기능 재구현 (필요시)
3. 성능 모니터링 및 최적화

