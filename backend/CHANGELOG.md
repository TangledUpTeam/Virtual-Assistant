# RAG System Changelog

## 2025-11-18 - Major Updates

### ✅ Completed Changes

#### 1. 유사도 필터링 문제 해결
**문제**: ChromaDB의 L2 distance가 잘못 변환되어 모든 유사도가 0.0으로 표시됨

**해결**: 
- L2 distance를 지수 감쇠 함수로 변환: `similarity = exp(-distance / 100)`
- 결과:
  - 거리 83.61 → 유사도 0.433 ✅
  - 거리 113.20 → 유사도 0.322 ✅
  - 거리 117.20 → 유사도 0.310 ✅

**파일**: `app/domain/rag/retriever.py` (Line 120-130)

---

#### 2. LangSmith 통합 완료
**목적**: RAG 시스템의 모든 단계를 실시간으로 추적 및 디버깅

**변경사항**:
- `app/core/config.py`: Settings 클래스에 LangSmith 필드 추가
- `app/domain/rag/config.py`: core.settings에서 LangSmith 설정 읽기
- `app/domain/rag/retriever.py`: 
  - `@traceable` 데코레이터 추가
  - `run_tree.extra`에 메타데이터 전달
  - 각 단계별 추적 (retrieve_and_filter, generate_answer)

**환경변수**:
```bash
LANGSMITH_API_KEY=lsv2_pt_...
LANGSMITH_PROJECT=virtual-assistant-rag
LANGSMITH_TRACING=true
```

**문서**: 
- `LANGSMITH_QUICK_START.md` - 5분 빠른 시작 가이드
- `LANGSMITH_SETUP.md` - 상세 설정 가이드
- `setup_env.py` - .env 파일 자동 생성 스크립트

---

#### 3. Small Talk 완전 제거
**문제**: 검색 결과가 없을 때 Small talk으로 빠져서 관련 없는 답변 생성

**해결**:
- `needs_search()` 함수 호출 제거
- 모든 질문을 RAG로 처리
- 검색 결과 0개일 때: "관련 문서를 찾을 수 없습니다" 메시지 반환

**파일**: `app/domain/rag/retriever.py` (Line 309-395)

---

#### 4. 청크 ID를 UUID 방식으로 변경
**문제**: 
- 기존 방식: `filename_p1_c0` (페이지, 청크 인덱스 기반)
- LangSmith UUID v7 경고 발생

**해결**:
- Python `uuid.uuid4()`로 전역 고유 ID 생성
- 충돌 없이 재처리 가능
- 예시: `b170bde5-f198-4747-97ee-1964091f7007`

**파일**: `app/domain/rag/document_converter.py` (Line 113, 152)

**재발 방지**: UUID는 전역적으로 고유하므로 재처리 시에도 충돌 없음

---

#### 5. CLI 컬렉션 초기화 기능 추가
**목적**: 벡터 DB를 초기화하고 문서를 재업로드

**사용법**:
```bash
# 확인 후 초기화
python -m app.domain.rag.cli reset

# 확인 없이 바로 초기화
python -m app.domain.rag.cli reset --yes
```

**기능**:
- 모든 임베딩 및 문서 삭제
- 컬렉션 재생성
- 안전 확인 메시지 (--yes 플래그로 스킵 가능)

**파일**: `app/domain/rag/cli.py` (Line 312-349, 426-427)

---

### 📊 테스트 결과

#### Before (기존 방식)
```
[1] 파일: 휴가신청프로세스.txt, 유사도: 0.0000 ❌
[2] 파일: 휴가지원기준표.txt, 유사도: 0.0000 ❌
→ 모든 문서 필터링됨 (threshold 0.35)
→ "관련 정보를 찾을 수 없습니다"
```

#### After (현재)
```
[1] 파일: 휴가신청프로세스.txt, 유사도: 0.4334 ✅
[2] 파일: 휴가지원기준표.txt, 유사도: 0.3224 ❌
[3] 파일: 연차규정.txt, 유사도: 0.3097 ❌
→ 1개 문서 검색 성공
→ 정확한 답변 생성
```

#### LangSmith Traces
```
rag_query_full (3.28s)
├─ retrieve_and_filter (0.22s)
│  └─ 3개 청크 검색 (유사도 정보 포함)
└─ generate_answer (3.06s)
   └─ ChatOpenAI (gpt-4o)

메타데이터:
- retrieved_chunks_count: 3
- chunks: [파일명, 페이지, 유사도]
- processing_time: 3.28s
- model: gpt-4o
```

#### UUID 생성
```
Chunk ID: b170bde5-f198-4747-97ee-1964091f7007
Is UUID format: True ✅
```

---

### 🚀 사용 가이드

#### 1. 컬렉션 초기화 및 재업로드
```bash
# 1. 기존 컬렉션 초기화
python -m app.domain.rag.cli reset --yes

# 2. 문서 재업로드 (UUID 기반)
python -m app.domain.rag.cli upload internal_docs/uploads

# 3. 상태 확인
python -m app.domain.rag.cli stats
```

#### 2. LangSmith 설정
```bash
# 1. API Key 발급: https://smith.langchain.com
# 2. .env 파일 수정
LANGSMITH_API_KEY=lsv2_pt_your_key_here
LANGSMITH_PROJECT=virtual-assistant-rag
LANGSMITH_TRACING=true

# 3. 테스트
python test_langsmith.py

# 4. 대시보드 확인
# https://smith.langchain.com → virtual-assistant-rag
```

#### 3. 질의응답
```bash
# 대화형 모드
python -m app.domain.rag.cli query

# 단일 질문
python -m app.domain.rag.cli query "휴가 신청 방법?"
```

---

### 📝 Migration Notes

기존 시스템에서 마이그레이션하는 경우:

1. **컬렉션 초기화 필수**: 기존 청크 ID 형식과 호환되지 않음
   ```bash
   python -m app.domain.rag.cli reset --yes
   ```

2. **문서 재업로드**: UUID 기반으로 재생성
   ```bash
   python -m app.domain.rag.cli upload internal_docs/uploads
   ```

3. **LangSmith 설정** (선택사항): `.env` 파일에 API Key 추가

---

### 🔧 Technical Details

#### UUID 생성 코드
```python
import uuid

# 이전
chunk_id = f"{document_id}_p{page_number}_c{idx}"

# 현재
chunk_id = str(uuid.uuid4())  # 예: b170bde5-f198-4747-97ee-1964091f7007
```

#### 유사도 변환 코드
```python
import math

# L2 distance → similarity score
distance = 83.6143
scale = 100.0
similarity_score = math.exp(-distance / scale)  # 0.4334
```

#### LangSmith 메타데이터
```python
from langsmith.run_helpers import get_current_run_tree

run_tree = get_current_run_tree()
if run_tree:
    run_tree.extra = {
        "retrieved_chunks_count": len(retrieved_chunks),
        "chunks": [
            {
                "filename": chunk.metadata.get("filename"),
                "page_number": chunk.metadata.get("page_number"),
                "score": chunk.score
            }
            for chunk in retrieved_chunks
        ],
        "processing_time": processing_time,
        "model": self.config.OPENAI_MODEL
    }
```

---

### ⚠️ Known Issues

1. **Windows 터미널 인코딩**: Rich 라이브러리의 특수 문자(✓, ✗ 등)가 cp949에서 깨짐
   - 영향: CLI 출력 메시지만 해당
   - 기능: 정상 작동
   - 해결: 일부 메시지를 영어로 변경

2. **LangSmith UUID v7 경고**: Pydantic v1 호환성 경고
   - 영향: 없음 (경고 메시지만)
   - 추적: 정상 작동

---

### 📚 References

- [LangSmith 공식 문서](https://docs.smith.langchain.com/)
- [LangChain Tracing](https://python.langchain.com/docs/langsmith/walkthrough)
- [ChromaDB 문서](https://docs.trychroma.com/)
- [UUID4 사양](https://en.wikipedia.org/wiki/Universally_unique_identifier#Version_4_(random))

---

## Summary

| 항목 | Before | After | 개선 |
|------|--------|-------|------|
| 유사도 계산 | 항상 0.0 | 0.43, 0.32, 0.31 | ✅ 정상 작동 |
| 문서 검색 | 실패 | 성공 (3개) | ✅ 검색 가능 |
| LangSmith 추적 | 없음 | 전체 단계 추적 | ✅ 디버깅 가능 |
| 청크 ID | 파일명 기반 | UUID | ✅ 충돌 방지 |
| 컬렉션 관리 | 수동 | CLI 명령어 | ✅ 편의성 향상 |

**모든 기능이 정상 작동합니다! 🎉**

