# Virtual Assistant Architecture Documentation

이 문서는 Virtual Assistant 프로젝트의 전체 아키텍처와 모듈별 작동 방식을 설명합니다.

## 1. 프로젝트 개요 (Overview)

이 프로젝트는 **Electron** 기반의 데스크톱 애플리케이션으로, **FastAPI** 백엔드와 **Live2D** 캐릭터가 포함된 프론트엔드로 구성되어 있습니다.

*   **Frontend**: Electron (Main Process) + Vanilla JS/HTML (Renderer Process) + Live2D (Pixi.js)
*   **Backend**: Python FastAPI (REST API, 비즈니스 로직, 데이터베이스)
*   **Database**: PostgreSQL (SQLAlchemy ORM) + ChromaDB (Vector Store)

---

## 2. 디렉토리 구조 (Directory Structure)

```
Virtual-Assistant/
├── backend/                # Python 백엔드
│   ├── app/                # FastAPI 애플리케이션 코어
│   │   ├── api/            # API 엔드포인트 (Router)
│   │   ├── core/           # 설정 (Config, Security)
│   │   ├── domain/         # 도메인별 로직 (Service, Schema, CRUD)
│   │   ├── infrastructure/ # DB, OAuth, Vector Store 등 인프라
│   │   └── main.py         # 백엔드 진입점
│   ├── alembic/            # DB 마이그레이션
│   └── assistant.py        # 백엔드 실행 스크립트
├── frontend/               # 프론트엔드 (로그인/시작 페이지)
│   ├── Login/              # 로그인 페이지
│   └── Start/              # 시작 페이지
├── renderer/               # Electron Renderer 리소스
│   ├── chat/               # 채팅 UI 로직
│   ├── tasks/              # 업무/보고서 UI 로직
│   └── brainstorming/      # 브레인스토밍 UI 로직
├── tools/                  # 외부 도구 연동 (Google Drive, Slack 등)
├── main.js                 # Electron Main Process 진입점
├── index.html              # 메인 캐릭터 화면 (Renderer Entry)
└── requirements.txt        # Python 의존성
```

---

## 3. 백엔드 아키텍처 (Backend Architecture)

백엔드는 **FastAPI**를 사용하여 구축되었으며, 모듈화된 구조를 따릅니다.

### 3.1 진입점 (Entry Point)
*   **파일**: `backend/app/main.py`
*   **역할**:
    *   FastAPI 앱 인스턴스 생성 (`app = FastAPI(...)`)
    *   CORS 미들웨어 설정
    *   정적 파일 마운트 (`/public`, `/static`, `/renderer`)
    *   API 라우터 등록 (`app.include_router(api_router)`)
    *   서버 시작/종료 시 DB 테이블 생성 및 초기화 (`lifespan`)

### 3.2 설정 (Configuration)
*   **파일**: `backend/app/core/config.py`
*   **역할**: `pydantic-settings`를 사용하여 환경 변수(`.env`)를 로드하고 관리합니다.
    *   DB URL, JWT Secret, OAuth Key, API Key 등을 포함합니다.

### 3.3 API 레이어 (API Layer)
*   **위치**: `backend/app/api/v1`
*   **구조**:
    *   `endpoints/`: 각 기능별 엔드포인트 정의 (예: `auth.py`, `chat.py`)
    *   `router.py` (또는 `__init__.py`): 모든 엔드포인트 라우터를 하나로 통합 (`api_router`)

### 3.4 도메인 레이어 (Domain Layer)
*   **위치**: `backend/app/domain`
*   **패턴**: 각 도메인(예: `auth`, `user`, `chatbot`)은 다음과 같은 구조를 가집니다.
    *   `schemas.py`: Pydantic 모델 (요청/응답 데이터 검증)
    *   `service.py`: 비즈니스 로직 처리 (DB 조회, 계산 등)
    *   `dependencies.py`: 의존성 주입 (현재 사용자 확인 등)
    *   `models.py` (선택적): SQLAlchemy DB 모델 정의 (또는 `infrastructure/database.py`에 통합)

### 3.5 인프라 레이어 (Infrastructure Layer)
*   **위치**: `backend/app/infrastructure`
*   **역할**:
    *   `database.py`: SQLAlchemy 엔진 및 세션 관리 (`get_db`)
    *   `oauth/`: Google, Kakao 등 OAuth 인증 처리
    *   `vector_store.py`: RAG를 위한 ChromaDB 연동

### 3.6 외부 도구 (Tools)
*   **위치**: `tools/`
*   **역할**: Google Drive, Gmail, Slack, Notion 등 외부 API와의 연동을 담당합니다.
*   **Router**: `tools/router.py`를 통해 별도의 API 엔드포인트로 노출되어 프론트엔드나 챗봇이 호출할 수 있습니다.

---

## 4. 프론트엔드 아키텍처 (Frontend Architecture)

프론트엔드는 **Electron**을 기반으로 하며, **Live2D** 캐릭터와 상호작용하는 투명 윈도우 인터페이스를 제공합니다.

### 4.1 Electron Main Process
*   **파일**: `main.js`
*   **역할**:
    *   애플리케이션 생명주기 관리
    *   윈도우 생성 (`createLoginWindow`, `createCharacterWindow`)
    *   백엔드 프로세스(`assistant.py`) 자동 실행 및 관리
    *   IPC 통신 처리 (렌더러 프로세스와의 메시지 교환)

### 4.2 Renderer Process (UI)
*   **파일**: `index.html`
*   **역할**: 메인 캐릭터 화면의 진입점입니다.
*   **구성요소**:
    *   **Live2D**: `pixi.js`와 `pixi-live2d-display`를 사용하여 캐릭터 렌더링 및 모션 제어.
    *   **UI Modules**: `renderer/` 폴더 내의 모듈을 동적으로 로드합니다.
        *   `chatUI.js`: 채팅 인터페이스
        *   `reportChatUI.js`: 보고서 작성 인터페이스
        *   `brainstormingService.js`: 브레인스토밍 기능

### 4.3 통신 (Communication)
*   **IPC**: `ipcRenderer` (Frontend) <-> `ipcMain` (Backend) 간의 통신을 통해 윈도우 제어(종료, 최소화, 마우스 이벤트 무시 등)를 수행합니다.
*   **HTTP**: 프론트엔드에서 `fetch` 또는 `axios`를 사용하여 백엔드 API (`http://localhost:8000`)를 호출합니다.

---

## 5. 주요 워크플로우 (Key Workflows)

### 5.1 애플리케이션 시작 (Startup)
1.  사용자가 Electron 앱 실행 (`npm start` or exe 실행).
2.  `main.js`가 실행되어 `python assistant.py`를 스폰(Spawn)하여 백엔드 서버를 시작.
3.  백엔드 헬스 체크(`/health`)를 주기적으로 호출하여 준비 대기.
4.  백엔드 준비 완료 시, `Login` 윈도우 생성 및 로드.

### 5.2 로그인 및 인증 (Authentication)
1.  사용자가 로그인 페이지에서 로그인 (또는 OAuth).
2.  백엔드에서 JWT Access/Refresh Token 발급.
3.  로그인 성공 시 `main.js`에 알림 -> `Login` 윈도우 닫기 -> `Character` 윈도우(투명) 생성.
4.  `Character` 윈도우는 토큰을 사용하여 백엔드 API와 통신.

### 5.3 채팅 및 기능 수행
1.  사용자가 채팅 입력.
2.  `chatUI.js`에서 백엔드 API 호출.
3.  백엔드 `chatbot` 도메인에서 요청 처리 (RAG, LLM 호출 등).
4.  필요 시 `tools` 모듈을 통해 외부 서비스(이메일 전송 등) 수행.
5.  응답을 프론트엔드로 반환하여 말풍선 표시 및 캐릭터 모션 재생.

---

## 6. 주요 기능 상세 (Feature Details)

### 6.1 챗봇 및 RAG (Chatbot & RAG)
*   **위치**: `backend/app/domain/chatbot/service.py`
*   **작동 방식**:
    1.  **세션 관리**: `SessionManager`를 통해 최근 15개 대화 히스토리를 메모리(Deque)에 유지합니다.
    2.  **장기 기억**: 15개를 초과하는 대화는 `MemoryManager`를 통해 Markdown 파일로 백업하고, `Summarizer`가 내용을 요약하여 시스템 프롬프트에 반영합니다.
    3.  **Function Calling**: 사용자의 질문이 도구 사용을 필요로 하면(예: "이메일 보내줘"), OpenAI Function Calling 기능을 통해 `tools` 모듈의 함수를 실행합니다.
    4.  **RAG (Retrieval-Augmented Generation)**: (활성화 시) 사용자의 질문과 관련된 문서를 ChromaDB에서 검색하여 프롬프트 컨텍스트에 추가합니다.

### 6.2 보고서 자동화 (Report Automation)
*   **위치**: `backend/app/domain/report/service.py`
*   **작동 방식**:
    1.  **PDF 처리**: 업로드된 PDF 보고서를 `PyMuPDF`를 사용하여 이미지로 변환합니다.
    2.  **타입 감지**: GPT-4o Vision API에 이미지를 전송하여 보고서 타입(일일/주간/월간/실적)을 자동 감지합니다.
    3.  **정보 추출**: 감지된 타입에 맞는 JSON 스키마를 사용하여, GPT-4o Vision이 이미지에서 텍스트 데이터를 구조화된 JSON으로 추출합니다.
    4.  **정규화 (Normalization)**: 추출된 Raw JSON 데이터를 내부 표준 포맷(`CanonicalReport`)으로 변환하여 DB에 저장하거나 활용합니다.

### 6.3 브레인스토밍 (Brainstorming)
*   **위치**: `backend/app/domain/brainstorming/service.py`
*   **작동 방식**:
    1.  **임베딩**: 사용자의 아이디어/질문을 OpenAI Embedding API를 통해 벡터로 변환합니다.
    2.  **검색**: ChromaDB(`brainstorming_techniques` 컬렉션)에서 유사한 브레인스토밍 기법(예: 마인드맵, SCAMPER)을 검색합니다.
    3.  **제안 생성**: 검색된 기법들을 컨텍스트로 하여, GPT-4o가 구체적인 아이디어 발전 방안을 제안합니다.

### 6.4 외부 도구 연동 (Tools Integration)
*   **위치**: `tools/` (예: `drive_tool.py`, `gmail_tool.py`)
*   **작동 방식**:
    1.  **인증**: `token_manager`를 통해 사용자의 OAuth 토큰(Google, Slack 등)을 로드하고 갱신합니다.
    2.  **API 호출**: 공식 SDK(Google API Client, Slack SDK 등)를 사용하여 외부 서비스를 호출합니다.
    3.  **기능**:
        *   **Google Drive**: 폴더 생성, 파일 업로드/다운로드, 검색
        *   **Gmail**: 이메일 전송, 조회
        *   **Slack**: DM/채널 메시지 전송
        *   **Notion**: 페이지 생성, 데이터베이스 아이템 추가
