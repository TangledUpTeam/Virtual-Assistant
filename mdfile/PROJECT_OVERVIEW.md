# Virtual Desk Assistant - 프로젝트 통합 문서

> **생성일**: 2024년  
> **버전**: 1.0.0  
> **설명**: AI 기반 멀티 에이전트 가상 데스크톱 어시스턴트

---

## 📋 목차

1. [프로젝트 개요](#프로젝트-개요)
2. [시스템 아키텍처](#시스템-아키텍처)
3. [디렉토리 구조](#디렉토리-구조)
4. [주요 기능](#주요-기능)
5. [기술 스택](#기술-스택)
6. [파일별 상세 설명](#파일별-상세-설명)

---

## 프로젝트 개요

Virtual Desk Assistant는 Electron 기반의 데스크톱 애플리케이션으로, Live2D 캐릭터와 함께 동작하는 AI 비서입니다. 멀티 에이전트 시스템을 통해 다양한 업무를 자동화하고 지원합니다.

### 핵심 특징

- 🤖 **멀티 에이전트 시스템**: 9개의 전문 에이전트가 협력하여 작업 수행
- 🎭 **Live2D 캐릭터**: 투명 창에서 동작하는 가상 캐릭터
- 🔐 **OAuth 인증**: Google, Kakao, Naver 소셜 로그인 지원
- 📝 **Notion 연동**: 페이지 생성, 검색, 내용 저장
- 📧 **Gmail 연동**: 이메일 전송 기능
- 📁 **Google Drive 연동**: 파일 검색, 폴더 생성
- 📊 **보고서 생성**: 일간/주간/월간 업무 보고서 자동 생성
- 🧠 **브레인스토밍**: 창의적 아이디어 생성 지원
- 💬 **심리 상담**: 감정 지원 및 상담 기능

---

## 시스템 아키텍처

```
┌─────────────────────────────────────────────────────────┐
│                    Electron App (main.js)                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │ Landing Page │  │ Character    │  │ Popups       │  │
│  │ (Login)      │  │ Window      │  │ (BS, etc)    │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
└─────────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────┐
│              FastAPI Backend (backend/app)              │
│  ┌──────────────────────────────────────────────────┐  │
│  │         Multi-Agent System (supervisor.py)        │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐       │  │
│  │  │ Chatbot  │  │   RAG    │  │ Notion   │  ...  │  │
│  │  │ Agent    │  │  Agent   │  │  Agent   │       │  │
│  │  └──────────┘  └──────────┘  └──────────┘       │  │
│  └──────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────┐  │
│  │              API Endpoints (api/v1)                │  │
│  │  - auth, chatbot, rag, reports, therapy, etc.     │  │
│  └──────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────┐  │
│  │              Tools Integration (tools/)            │  │
│  │  - Notion, Gmail, Google Drive                   │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────┐
│              External Services                          │
│  - PostgreSQL (User, Session)                          │
│  - ChromaDB (Vector Store)                             │
│  - OpenAI (LLM, Embeddings)                           │
│  - Notion API                                          │
│  - Google APIs (Gmail, Drive)                          │
└─────────────────────────────────────────────────────────┘
```

---

## 디렉토리 구조

```
Virtual-Assistant/
├── assistant.py                 # 백엔드 서버 실행 파일
├── main.js                      # Electron 메인 프로세스
├── index.html                   # 메인 캐릭터 화면
├── package.json                 # Node.js 의존성
├── requirements.txt              # Python 의존성
│
├── backend/                      # 백엔드 코드
│   ├── app/                     # FastAPI 애플리케이션
│   │   ├── main.py              # FastAPI 앱 진입점
│   │   ├── api/v1/              # API 엔드포인트
│   │   │   └── endpoints/       # 각 기능별 엔드포인트
│   │   │       ├── auth.py      # 인증 (OAuth)
│   │   │       ├── chatbot.py   # 챗봇 API
│   │   │       ├── rag.py       # 문서 검색 API
│   │   │       ├── multi_agent.py  # 멀티 에이전트 API
│   │   │       ├── reports.py   # 보고서 API
│   │   │       └── ...
│   │   ├── core/                # 핵심 설정
│   │   │   ├── config.py        # 환경 변수 설정
│   │   │   └── security.py      # JWT 인증
│   │   ├── domain/              # 도메인 로직
│   │   │   ├── auth/            # 인증 도메인
│   │   │   ├── user/            # 사용자 도메인
│   │   │   ├── chatbot/         # 챗봇 도메인
│   │   │   ├── brainstorming/   # 브레인스토밍 도메인
│   │   │   └── ...
│   │   ├── infrastructure/      # 인프라스트럭처
│   │   │   ├── database/        # DB 세션 관리
│   │   │   └── oauth/           # OAuth 클라이언트
│   │   ├── reporting/           # 보고서 생성 로직
│   │   └── services/            # 비즈니스 서비스
│   │
│   ├── multi_agent/             # 멀티 에이전트 시스템
│   │   ├── supervisor.py        # 중앙 조율자
│   │   ├── agents/              # 전문 에이전트들
│   │   │   ├── base_agent.py   # 기본 에이전트 클래스
│   │   │   ├── chatbot_agent.py # 일반 대화
│   │   │   ├── rag_agent.py    # 문서 검색
│   │   │   ├── notion_agent.py # Notion 관리
│   │   │   ├── email_agent.py  # 이메일 전송
│   │   │   ├── brainstorming_agent.py  # 브레인스토밍
│   │   │   ├── therapy_agent.py       # 심리 상담
│   │   │   ├── planner_agent.py       # 일정 관리
│   │   │   └── report_agent.py        # 보고서 생성
│   │   ├── tools/               # 에이전트 도구
│   │   │   └── agent_tools.py   # LangChain Tool 래퍼
│   │   ├── config.py            # 멀티 에이전트 설정
│   │   ├── context.py           # 컨텍스트 관리
│   │   └── schemas.py           # 데이터 스키마
│   │
│   ├── ingestion/               # 데이터 수집
│   │   ├── chroma_client.py     # ChromaDB 클라이언트
│   │   ├── embed.py             # 임베딩 생성
│   │   ├── ingest_reports.py    # 보고서 수집
│   │   └── ...
│   │
│   ├── debug/                   # 디버깅 스크립트
│   ├── data/                    # 데이터 파일
│   └── alembic/                 # DB 마이그레이션
│
├── frontend/                    # 프론트엔드 페이지
│   ├── Landing/                 # 랜딩 페이지
│   │   ├── index.html
│   │   ├── script.js
│   │   └── style.css
│   └── Login/                   # 로그인 페이지
│       ├── index.html
│       ├── script.js
│       └── style.css
│
├── renderer/                    # 렌더러 프로세스 코드
│   ├── chat/                    # 채팅 기능
│   │   ├── chatUI.js           # 채팅 UI 관리
│   │   ├── chatPanel.js        # 채팅 패널
│   │   ├── chatbotService.js   # 챗봇 API 서비스
│   │   └── chatService.js      # 채팅 서비스
│   │
│   ├── brainstorming/           # 브레인스토밍
│   │   ├── brainstormingPanel.js
│   │   └── brainstormingService.js
│   │
│   ├── tasks/                   # 업무 관리
│   │   ├── taskUI.js           # 업무 UI
│   │   ├── taskService.js      # 업무 서비스
│   │   ├── reportChatUI.js     # 보고서 채팅 UI
│   │   └── reportService.js    # 보고서 서비스
│   │
│   ├── activity-monitor/        # 활동 모니터링
│   │   └── activityMonitor.js
│   │
│   └── styles/                  # CSS 스타일
│       ├── chat.css
│       ├── live2d.css
│       ├── tasks.css
│       └── brainstorming.css
│
├── tools/                       # 외부 서비스 통합
│   ├── router.py                # Tools API 라우터
│   ├── notion_tool.py           # Notion API
│   ├── notion_utils.py          # Notion 유틸리티
│   ├── gmail_tool.py            # Gmail API
│   ├── drive_tool.py            # Google Drive API
│   ├── slack_tool.py            # Slack API
│   ├── token_manager.py         # OAuth 토큰 관리
│   └── schemas.py               # 데이터 스키마
│
├── public/                      # 정적 파일
│   └── models/                  # Live2D 모델
│       └── hiyori_free_ko/      # 히요리 캐릭터
│
├── brainstorming-popup.html     # 브레인스토밍 팝업
└── start_backend.sh             # 백엔드 시작 스크립트
```

---

## 주요 기능

### 1. 멀티 에이전트 시스템

**Supervisor Agent** (`backend/multi_agent/supervisor.py`)
- 사용자 질문을 분석하여 적절한 전문 에이전트 선택
- LangGraph를 사용한 에이전트 조율
- 컨텍스트 기반 라우팅

**전문 에이전트들** (`backend/multi_agent/agents/`)
1. **Chatbot Agent**: 일반 대화, 인사, 잡담
2. **RAG Agent**: 회사 문서, 규정, 정책 검색 (ChromaDB 기반)
3. **Notion Agent**: Notion 페이지 검색, 생성, 저장
4. **Email Agent**: Gmail을 통한 이메일 전송
5. **Brainstorming Agent**: 창의적 아이디어 생성
6. **Therapy Agent**: 심리 상담 및 감정 지원
7. **Planner Agent**: 일정 관리 및 계획 수립
8. **Report Agent**: 업무 보고서 생성

### 2. 인증 시스템

**OAuth 지원** (`backend/app/api/v1/endpoints/auth.py`)
- Google OAuth
- Kakao OAuth
- Naver OAuth
- Notion OAuth (사용자 개인 연동)
- Slack OAuth (사용자 개인 연동)

**JWT 토큰 관리** (`backend/app/core/security.py`)
- Access Token (30분)
- Refresh Token (15일)
- HttpOnly Cookie 기반 저장

### 3. Notion 통합

**Notion Agent** (`backend/multi_agent/agents/notion_agent.py`)
- **검색 모드**: 자연어 쿼리로 페이지 검색 및 RAG 답변
- **조회 모드**: 특정 페이지 내용 전체 가져오기
- **생성 모드**: 페이지 생성 및 대화 내용 저장
- 페이지 이름 자동 추출 및 매칭
- 전체 페이지 목록 기반 정확한 매칭

**Notion Tool** (`tools/notion_tool.py`)
- 페이지 생성/수정/조회
- 마크다운 변환
- 페이지 검색 (페이지네이션 지원)

### 4. 보고서 생성

**보고서 유형** (`backend/app/reporting/`)
- 일간 보고서 (`daily_report.py`)
- 주간 보고서 (`weekly_report.py`)
- 월간 보고서 (`monthly_report.py`)
- 실적 보고서 (`performance_report.py`)
- PDF 내보내기 (`pdf_export.py`)

**보고서 기능**
- 자동 업무 내용 수집
- LLM 기반 요약 및 분석
- PDF 형식으로 내보내기

### 5. 브레인스토밍

**Brainstorming Agent** (`backend/multi_agent/agents/brainstorming_agent.py`)
- 창의적 아이디어 생성
- 다양한 브레인스토밍 기법 적용
- 세션 기반 대화 관리

**UI** (`renderer/brainstorming/`)
- 팝업 창 인터페이스
- 아이디어 저장 및 관리

### 6. 심리 상담

**Therapy Agent** (`backend/multi_agent/agents/therapy_agent.py`)
- 감정 분석 및 지원
- 스트레스 관리 조언
- 대인관계 조언
- ChromaDB 기반 상담 데이터 활용

### 7. Live2D 캐릭터

**캐릭터 시스템** (`index.html`, `main.js`)
- 투명 창에서 동작
- 드래그 앤 드롭으로 위치 이동
- 크기 조절 (+/- 키)
- 활동 모니터링 기반 모션
- 클릭-스루 기능 (패널 제외)

### 8. 채팅 인터페이스

**채팅 기능** (`renderer/chat/`)
- 멀티 에이전트 시스템과 통신
- 마크다운 렌더링
- 대화 히스토리 관리
- 세션 기반 메모리

---

## 기술 스택

### 프론트엔드
- **Electron**: 데스크톱 애플리케이션 프레임워크
- **Live2D**: 2D 캐릭터 애니메이션
- **Pixi.js**: WebGL 기반 렌더링
- **Vanilla JavaScript**: 프레임워크 없는 순수 JS

### 백엔드
- **FastAPI**: 비동기 웹 프레임워크
- **Python 3.10+**: 백엔드 언어
- **SQLAlchemy**: ORM
- **Alembic**: DB 마이그레이션
- **PostgreSQL**: 관계형 데이터베이스

### AI/ML
- **LangChain**: LLM 프레임워크
- **LangGraph**: 에이전트 오케스트레이션
- **OpenAI API**: GPT-4o, GPT-4o-mini
- **ChromaDB**: 벡터 데이터베이스
- **text-embedding-3-large**: 임베딩 모델

### 외부 서비스
- **Notion API**: 페이지 관리
- **Google APIs**: Gmail, Drive
- **Slack API**: 메시지 전송

---

## 파일별 상세 설명

### 루트 파일

#### `assistant.py`
- **역할**: 백엔드 서버 실행 진입점
- **기능**: 
  - Uvicorn 서버 시작
  - 포트 8000에서 실행
  - Windows 호환성 고려 (reload=False)

#### `main.js`
- **역할**: Electron 메인 프로세스
- **기능**:
  - 랜딩 창 생성
  - 캐릭터 창 생성 (투명 전체화면)
  - 브레인스토밍 팝업 관리
  - Notion OAuth 창 관리
  - 백엔드 프로세스 자동 시작
  - IPC 통신 처리

#### `index.html`
- **역할**: 메인 캐릭터 화면
- **기능**:
  - Live2D 캐릭터 렌더링
  - 채팅 패널
  - 보고서 패널
  - 활동 모니터링
  - 캐릭터 드래그 앤 드롭

#### `package.json`
- **역할**: Node.js 프로젝트 설정
- **의존성**:
  - electron: ^39.1.2
  - concurrently: ^8.2.2
  - wait-on: ^8.0.0

#### `requirements.txt`
- **역할**: Python 의존성 관리
- **주요 패키지**:
  - fastapi, uvicorn
  - sqlalchemy, alembic
  - langchain, langgraph
  - openai
  - chromadb
  - notion-client

### 백엔드 핵심 파일

#### `backend/app/main.py`
- **역할**: FastAPI 애플리케이션 진입점
- **기능**:
  - FastAPI 앱 생성
  - CORS 설정
  - 라우터 등록
  - 정적 파일 서빙
  - Lifespan 이벤트 처리 (DB 초기화, Vector DB 생성)

#### `backend/app/core/config.py`
- **역할**: 환경 변수 설정 관리
- **설정 항목**:
  - 데이터베이스 URL
  - JWT 시크릿 키
  - OAuth 클라이언트 정보
  - OpenAI API 키
  - ChromaDB 설정
  - LLM 모델 설정

#### `backend/multi_agent/supervisor.py`
- **역할**: 멀티 에이전트 시스템 중앙 조율자
- **기능**:
  - 사용자 질문 분석
  - 적절한 에이전트 선택
  - LangGraph 기반 실행
  - 컨텍스트 관리

#### `backend/multi_agent/agents/base_agent.py`
- **역할**: 모든 에이전트의 기본 클래스
- **기능**:
  - 공통 인터페이스 정의
  - 에이전트 메타데이터 관리

#### `backend/multi_agent/agents/notion_agent.py`
- **역할**: Notion 전용 에이전트
- **기능**:
  - 모드 자동 결정 (search/get/create)
  - 페이지 이름 자동 추출
  - 전체 페이지 목록 기반 매칭
  - 대화 내용 저장
  - 페이지 검색 및 조회

#### `backend/multi_agent/tools/agent_tools.py`
- **역할**: 에이전트를 LangChain Tool로 래핑
- **기능**:
  - 각 에이전트를 Tool로 변환
  - 컨텍스트 자동 주입
  - 대화 히스토리 관리

### 프론트엔드 핵심 파일

#### `renderer/chat/chatUI.js`
- **역할**: 채팅 UI 메인 모듈
- **기능**:
  - 채팅 패널 초기화
  - 메시지 표시
  - 멀티 에이전트 API 호출
  - 마크다운 렌더링

#### `renderer/chat/chatbotService.js`
- **역할**: 챗봇 API 서비스
- **기능**:
  - 세션 관리
  - API 호출
  - 에러 처리
  - 멀티 에이전트 시스템 연동

#### `renderer/tasks/reportChatUI.js`
- **역할**: 보고서 채팅 UI
- **기능**:
  - 보고서 패널 관리
  - 보고서 생성 요청
  - 날짜 설정 UI

### Tools 파일

#### `tools/notion_tool.py`
- **역할**: Notion API 래퍼
- **기능**:
  - 페이지 CRUD
  - 마크다운 변환
  - 검색 및 페이지네이션
  - OAuth 토큰 관리

#### `tools/gmail_tool.py`
- **역할**: Gmail API 래퍼
- **기능**:
  - 이메일 전송
  - OAuth 토큰 관리

#### `tools/drive_tool.py`
- **역할**: Google Drive API 래퍼
- **기능**:
  - 파일 검색
  - 폴더 생성
  - OAuth 토큰 관리

#### `tools/token_manager.py`
- **역할**: OAuth 토큰 관리
- **기능**:
  - 토큰 로드/저장
  - 토큰 갱신
  - 캐시 관리
  - DB 연동

#### `tools/router.py`
- **역할**: Tools API 라우터
- **기능**:
  - REST API 엔드포인트 제공
  - Notion, Gmail, Drive 기능 노출

### API 엔드포인트

#### `backend/app/api/v1/endpoints/auth.py`
- **기능**: OAuth 인증 처리
- **엔드포인트**:
  - `/api/v1/auth/{provider}/login`: 로그인 URL 생성
  - `/api/v1/auth/{provider}/callback`: OAuth 콜백 처리
  - `/api/v1/auth/refresh`: 토큰 갱신

#### `backend/app/api/v1/endpoints/multi_agent.py`
- **기능**: 멀티 에이전트 시스템 API
- **엔드포인트**:
  - `/api/v1/multi-agent/chat`: 멀티 에이전트 채팅

#### `backend/app/api/v1/endpoints/rag.py`
- **기능**: 문서 검색 API
- **엔드포인트**:
  - `/api/v1/rag/search`: 문서 검색

#### `backend/app/api/v1/endpoints/reports.py`
- **기능**: 보고서 생성 API
- **엔드포인트**:
  - `/api/v1/reports/daily`: 일간 보고서
  - `/api/v1/reports/weekly`: 주간 보고서
  - `/api/v1/reports/monthly`: 월간 보고서

---

## 실행 방법

### 개발 환경 설정

1. **의존성 설치**
```bash
# Python 의존성
pip install -r requirements.txt

# Node.js 의존성
npm install
```

2. **환경 변수 설정**
`.env` 파일 생성:
```
DATABASE_URL=postgresql://user:password@localhost/dbname
SECRET_KEY=your-secret-key
OPENAI_API_KEY=your-openai-key
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
# ... 기타 OAuth 설정
```

3. **데이터베이스 설정**
```bash
# Alembic 마이그레이션
cd backend
alembic upgrade head
```

4. **실행**
```bash
# 백엔드만 실행
python assistant.py

# 또는 Electron과 함께 실행
npm start
```

---

## 주요 워크플로우

### 1. 사용자 로그인
1. 랜딩 페이지에서 OAuth 제공자 선택
2. OAuth 인증 후 콜백 처리
3. JWT 토큰 발급 및 쿠키 저장
4. 캐릭터 창으로 이동

### 2. 멀티 에이전트 질문 처리
1. 사용자 질문 입력
2. Supervisor Agent가 질문 분석
3. 적절한 전문 에이전트 선택
4. 에이전트 실행 및 결과 반환
5. 사용자에게 답변 표시

### 3. Notion 페이지 저장
1. 사용자: "방금 답변한 내용을 Notion에 저장해줘"
2. Notion Agent가 모드 결정 (create)
3. 페이지 이름 추출 및 매칭
4. 전체 대화 내용 수집
5. Notion API로 페이지 생성

### 4. 보고서 생성
1. 사용자가 보고서 타입 선택
2. 날짜/기간 설정
3. Report Agent가 업무 데이터 수집
4. LLM으로 요약 및 분석
5. PDF로 내보내기

---

## 데이터베이스 스키마

### 주요 테이블
- **users**: 사용자 정보
- **user_tokens**: OAuth 토큰 저장
- **chatbot_sessions**: 챗봇 세션
- **chatbot_messages**: 대화 메시지
- **brainstorming_sessions**: 브레인스토밍 세션

---

## 보안 고려사항

- JWT 토큰을 HttpOnly Cookie에 저장
- OAuth 토큰은 암호화하여 DB 저장
- CORS 설정으로 허용된 도메인만 접근
- 환경 변수로 민감 정보 관리

---

## 향후 개선 사항

- [ ] 에이전트 성능 모니터링
- [ ] 사용자 피드백 수집 시스템
- [ ] 에이전트 학습 및 개선
- [ ] 추가 외부 서비스 연동
- [ ] 모바일 앱 지원

---

## 라이선스

ISC

---

## 기여자

TangledUpTeam

---

**마지막 업데이트**: 2024년

