# LangSmith 빠른 시작 가이드

## 현재 상태

✅ **코드 통합 완료**: RAG 시스템에 LangSmith 추적 코드가 이미 통합되어 있습니다.  
❌ **환경변수 미설정**: `.env` 파일에 LangSmith API 키가 설정되지 않았습니다.

## 5분 안에 설정하기

### 1단계: LangSmith API Key 발급 (2분)

1. https://smith.langchain.com 접속
2. 계정 생성/로그인 (GitHub 계정으로 간편 로그인 가능)
3. 우측 상단 프로필 → **Settings** → **API Keys**
4. **Create API Key** 클릭
5. API Key 복사 (예: `lsv2_pt_...`)

### 2단계: .env 파일 수정 (1분)

`backend/.env` 파일을 열고 다음 3줄을 찾아서 수정:

```bash
# 수정 전
LANGSMITH_API_KEY=your_langsmith_api_key_here
LANGSMITH_PROJECT=virtual-assistant-rag
LANGSMITH_TRACING=true

# 수정 후 (실제 API Key로 변경)
LANGSMITH_API_KEY=lsv2_pt_1234567890abcdef...
LANGSMITH_PROJECT=virtual-assistant-rag
LANGSMITH_TRACING=true
```

### 3단계: 테스트 (2분)

```bash
# 백엔드 디렉토리로 이동
cd backend

# 가상환경 활성화 (이미 활성화되어 있다면 생략)
conda activate virtual_assistant

# RAG 시스템 실행
python -m app.domain.rag.cli query
```

질문을 입력하고 답변을 받은 후:

1. https://smith.langchain.com 접속
2. 프로젝트 선택: `virtual-assistant-rag`
3. **Traces** 탭에서 방금 실행한 쿼리 확인

## 무엇을 볼 수 있나요?

### 실시간 추적

```
[Trace 1] rag_query_full
├─ [Input] 사용자 질문
├─ [Step 1] Document Retrieval
│  ├─ 검색된 문서 청크 (3개)
│  ├─ 유사도 점수
│  └─ 실행 시간
├─ [Step 2] Context Building
│  └─ LLM에 전달될 컨텍스트
├─ [Step 3] LLM Generation
│  ├─ 프롬프트 (전체)
│  ├─ 모델: gpt-4o
│  ├─ 토큰 사용량
│  └─ 비용
└─ [Output] 최종 답변
```

### 성능 분석

- **응답 시간**: 0.5초
- **토큰 사용량**: 입력 500, 출력 200
- **비용**: $0.015

### 디버깅

- 검색이 제대로 되었나?
- 프롬프트가 올바른가?
- LLM이 컨텍스트를 잘 활용했나?

## 비용

- **무료 플랜**: 월 5,000 traces
- **현재 사용량**: 개발 중에는 충분함

## 선택사항: 추적 비활성화

개발이 끝나고 프로덕션에서는 비활성화 가능:

```bash
LANGSMITH_TRACING=false
```

## 문제 해결

### API Key가 인식되지 않음

```bash
# .env 파일 위치 확인
ls backend/.env

# 환경변수 확인
python -c "from dotenv import load_dotenv; import os; load_dotenv(); print(os.getenv('LANGSMITH_API_KEY'))"
```

### 추적이 표시되지 않음

1. 인터넷 연결 확인
2. API Key가 올바른지 확인
3. 프로젝트 이름 확인 (`virtual-assistant-rag`)
4. 애플리케이션 재시작

## 더 알아보기

- 📚 [상세 가이드](./LANGSMITH_SETUP.md)
- 🌐 [LangSmith 공식 문서](https://docs.smith.langchain.com/)
- 💬 [LangChain Discord](https://discord.gg/langchain)

---

**요약**: `.env` 파일에 `LANGSMITH_API_KEY`만 설정하면 바로 사용 가능합니다! 🚀

