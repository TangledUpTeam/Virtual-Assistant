# 🧠 데스크톱 버튜버 비서 프로젝트 기획 (AI RAG + Agent 버전)

## 🎯 프로젝트 개요
**프로젝트명:** Virtual Desk Assistant  
**목표:** 바탕화면 우측 하단에 상주하는 캐릭터가 사용자의 활동을 감지하고, 회사 매뉴얼을 RAG 기반으로 답변하며, Idle 시 잔소리하는 AI 비서 앱을 개발한다.

---

## ⚙️ 전체 아키텍처
```
Desktop App (Electron)
 ├─ Renderer (React)
 │   ├─ 캐릭터 렌더러 (Live2D 또는 투명 비디오)
 │   ├─ 대화창 + 말풍선
 │   └─ 설정/로그
 ├─ Agent / Intent Router
 │   ├─ 도구 호출 (queryManual, idleStatus, scold 등)
 │   └─ 페르소나 / 정책 엔진
 ├─ RAG Stack
 │   ├─ 문서 Ingestion (PDF/MD → Text → Chunk → Embed)
 │   ├─ Vector DB (Chroma → pgvector)
 │   └─ Retrieval + Answer Format (출처 포함)
 ├─ Activity Detector
 │   ├─ Idle / 활성 앱 감지
 │   └─ 업무시간 규칙 / 잔소리 정책
 ├─ Speech Layer (선택)
 │   ├─ STT Adapter
 │   └─ TTS Adapter
 └─ Logging & Packaging
     ├─ electron-store, Sentry
     └─ electron-builder (.dmg/.exe)
```

---

## 🧩 기술 스택 (유료/무료 포함 전체 옵션)

| 기능 | 사용 기술 | 비고 |
|------|------------|------|
| **데스크톱 셸** | Electron | 투명·항상위·드래그 가능 |
| **UI 프레임워크** | React + Tailwind | 간결한 UI 구성 |
| **캐릭터 렌더러** | Live2D Cubism SDK / PixiJS + pixi-live2d-display / WebM(알파 비디오) | 기성 모델 또는 투명 비디오 |
| **AI 대화 엔진** | OpenAI GPT-4o / GPT-4.1 / GPT-mini | 시스템 프롬프트로 페르소나 제어 |
| **벡터DB** | Chroma (로컬) → pgvector (확장) | 문서 검색 |
| **임베딩 모델** | OpenAI embedding-3-large / bge-m3 | RAG 인덱싱 |
| **에이전트 실행** | OpenAI Tool Calling / LangGraph | 도구 호출 기반 |
| **문서 파이프라인** | pdfminer / unstructured / LangChain text splitter | 전처리 자동화 |
| **Idle 감지** | electron-idle / iohook / active-win | 무활동 및 앱 감지 |
| **음성 (선택)** | whisper.cpp / OpenAI STT / Azure Speech / macOS `say` / Polly | 나중에 플러그인 추가 |
| **로깅/배포** | Sentry / electron-builder | 배포 및 오류 추적 |

---

## 🧱 개발 단계별 플로우

### 1️⃣ 캐릭터 표시
- 기성 Live2D 모델 또는 투명 비디오를 불러와 표시
- 상태(Idle / 말하기 / 화남) 3단계 전환 구현

### 2️⃣ 패키징
- electron-builder로 macOS `.dmg` / Windows `.exe` 생성
- 트레이/자동실행 옵션 추가

### 3️⃣ 대화 기능
- OpenAI Chat API 연동
- 시스템 프롬프트로 캐릭터 페르소나 조정
- 말풍선 UI + 입력창 구현

### 4️⃣ 문서 RAG
- PDF/MD → 텍스트 추출 → 임베딩 → Chroma 저장
- 검색 + LLM 응답 + 출처 표시

### 5️⃣ 활동 감지 / 잔소리 모드
- Idle 5분 이상: 부드러운 경고
- 블랙리스트 앱 실행 시 업무시간 내 경고
- 설정에서 민감도, OFF 모드 토글 가능

### 6️⃣ 배포 / QA
- 설정 저장, 로그 수집, `.dmg` 릴리즈
- RAG 품질 테스트 (정확근거율 ≥ 70%)

---

## 🧭 4주 로드맵

| 주차 | 목표 |
|------|------|
| 1주차 | Electron UI + 캐릭터 표시 + 드래그/리사이즈 |
| 2주차 | 대화 엔진 + RAG 인덱싱/검색 구현 |
| 3주차 | Idle 감지 + 잔소리 정책/설정 패널 |
| 4주차 | 패키징/배포 + QA + 데모 영상 제작 |

---

## 🧰 폴더 구조 (요약)
```
app/
  main/        # Electron main process
  renderer/    # React UI
    components/
    hooks/
    rag/
    agents/
  tools/
    character/
    activity/
    speech/
  assets/
  store/
scripts/
  ingest/      # 문서 임베딩 파이프라인
  eval/        # 품질 평가
```

---

## 🚀 실행 흐름 요약
1. **사용자 질문 입력**
2. **의도 분류 (Agent)** → “매뉴얼 질문”이면 RAG 실행
3. **RAG** → VectorDB 검색 → 문서 근거 포함 답변
4. **LLM 응답 → 말풍선 표시**
5. **Idle/활성앱 감지 루프** → 잔소리 정책 트리거
6. **TTS/STT (후속 플러그인)** 로 음성화

---

## 🎮 확장 아이디어
- 감정 상태별 표정 (happy/sad/angry)
- 업무 리마인더/슬랙 연동
- 음성 모드 + 립싱크
- 멀티 캐릭터 / 유저별 커스터마이징

---

## ⚠️ 리스크 관리
- **라이선스**: 모델 TOS 반드시 확인 및 레포에 보관  
- **RAG 품질**: 전처리 규칙 표준화, 버전 메타데이터 관리  
- **보안**: 로컬 우선 처리, 로그 암호화  
- **성능**: 캐시, 비동기 검색, OpenAI 호출 최적화

---

## ✅ 한줄 요약
> “이 프로젝트는 단순한 버튜버 위젯이 아니라, **RAG + Agent 기반 AI 데스크톱 앱**이다.  
> 문서 질의응답·상황인지·도구호출이 결합된 실제 서비스급 구조로 설계된다.”
