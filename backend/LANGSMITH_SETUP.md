# LangSmith 설정 가이드

LangSmith는 LangChain 애플리케이션을 모니터링하고 디버깅하는 강력한 도구입니다.

## 🎯 LangSmith란?

- **추적(Tracing)**: LangChain 체인의 각 단계를 시각화
- **디버깅**: 프롬프트, 입력, 출력을 실시간으로 확인
- **성능 분석**: 응답 시간, 토큰 사용량 등을 모니터링
- **평가**: 모델 성능을 평가하고 개선

## 📋 설정 방법

### 1. LangSmith 계정 생성

1. [https://smith.langchain.com](https://smith.langchain.com) 접속
2. 계정 생성 (무료 플랜 사용 가능)
3. API Key 발급

### 2. API Key 발급

1. LangSmith 대시보드 접속
2. 우측 상단 프로필 → **Settings**
3. **API Keys** 탭 클릭
4. **Create API Key** 버튼 클릭
5. API Key 복사

### 3. 환경변수 설정

`backend/.env` 파일을 생성하고 다음 내용을 추가:

```bash
# LangSmith Configuration
LANGSMITH_API_KEY=your_actual_langsmith_api_key_here
LANGSMITH_PROJECT=virtual-assistant-rag
LANGSMITH_TRACING=true
```

**주의**: `.env` 파일이 없다면 `env.example`을 복사하여 생성:

```bash
cd backend
cp ../env.example .env
# 그 다음 .env 파일을 열어서 LANGSMITH_API_KEY를 실제 값으로 변경
```

### 4. 설정 확인

현재 RAG 시스템은 이미 LangSmith 통합이 완료되어 있습니다:

```python
# app/domain/rag/retriever.py
from langsmith import traceable

class RAGRetriever:
    def __init__(self):
        # LangSmith 설정
        if self.config.LANGSMITH_TRACING and self.config.LANGSMITH_API_KEY:
            os.environ["LANGCHAIN_TRACING_V2"] = "true"
            os.environ["LANGCHAIN_API_KEY"] = self.config.LANGSMITH_API_KEY
            os.environ["LANGCHAIN_PROJECT"] = self.config.LANGSMITH_PROJECT
    
    @traceable(name="rag_query_full")
    def query(self, request: QueryRequest) -> QueryResponse:
        # RAG 쿼리 실행
        ...
```

## 🚀 사용 방법

### 1. RAG 시스템 실행

```bash
cd backend
python -m app.domain.rag.cli query
```

### 2. LangSmith 대시보드 확인

1. [https://smith.langchain.com](https://smith.langchain.com) 접속
2. 프로젝트 선택: `virtual-assistant-rag`
3. **Traces** 탭에서 실시간 추적 확인

### 3. 추적 정보 확인

각 쿼리마다 다음 정보를 확인할 수 있습니다:

- **입력**: 사용자 질문
- **검색 결과**: 검색된 문서 청크
- **프롬프트**: LLM에 전달된 최종 프롬프트
- **출력**: 생성된 답변
- **성능**: 실행 시간, 토큰 사용량
- **오류**: 발생한 에러 (있는 경우)

## 📊 주요 기능

### 1. 체인 시각화

```
Query Input
  ↓
Document Retrieval (Vector Search)
  ↓
Context Building
  ↓
LLM Generation
  ↓
Final Answer
```

### 2. 성능 모니터링

- **응답 시간**: 각 단계별 소요 시간
- **토큰 사용량**: 입력/출력 토큰 수
- **비용**: API 호출 비용 추정

### 3. 디버깅

- **프롬프트 확인**: LLM에 전달된 정확한 프롬프트
- **검색 결과**: 벡터 검색으로 찾은 문서들
- **유사도 점수**: 각 문서의 유사도 점수

## 🔧 고급 설정

### 프로젝트별 추적

여러 프로젝트를 관리하는 경우:

```bash
# 개발 환경
LANGSMITH_PROJECT=virtual-assistant-rag-dev

# 프로덕션 환경
LANGSMITH_PROJECT=virtual-assistant-rag-prod
```

### 선택적 추적

특정 환경에서만 추적을 활성화:

```bash
# 개발 환경: 추적 활성화
LANGSMITH_TRACING=true

# 프로덕션 환경: 추적 비활성화
LANGSMITH_TRACING=false
```

### 커스텀 메타데이터 추가

코드에서 추가 메타데이터를 기록:

```python
@traceable(
    name="custom_query",
    metadata={"user_id": "123", "version": "1.0"}
)
def custom_query(query: str):
    # 쿼리 처리
    pass
```

## 🎓 학습 자료

- [LangSmith 공식 문서](https://docs.smith.langchain.com/)
- [LangSmith 튜토리얼](https://docs.smith.langchain.com/tutorials)
- [LangChain 추적 가이드](https://python.langchain.com/docs/langsmith/walkthrough)

## 🐛 문제 해결

### API Key 오류

```
Error: Invalid API key
```

**해결**: `.env` 파일의 `LANGSMITH_API_KEY`가 올바른지 확인

### 추적이 표시되지 않음

```
No traces found in LangSmith
```

**해결**:
1. `LANGSMITH_TRACING=true` 확인
2. 인터넷 연결 확인
3. LangSmith 대시보드에서 올바른 프로젝트 선택

### 환경변수 로드 안됨

```
LANGSMITH_API_KEY not found
```

**해결**:
1. `.env` 파일이 `backend/` 디렉토리에 있는지 확인
2. 애플리케이션 재시작
3. `python-dotenv` 패키지 설치 확인

## 💡 팁

1. **개발 중에만 사용**: 프로덕션에서는 비용과 성능을 고려하여 선택적으로 사용
2. **민감 정보 주의**: 프롬프트에 민감한 정보가 포함되지 않도록 주의
3. **정기적인 검토**: 대시보드를 정기적으로 확인하여 성능 병목 지점 파악
4. **A/B 테스트**: 다른 프롬프트나 모델을 테스트하고 비교

## 📞 지원

- LangSmith 지원: [support@langchain.com](mailto:support@langchain.com)
- LangChain Discord: [https://discord.gg/langchain](https://discord.gg/langchain)

