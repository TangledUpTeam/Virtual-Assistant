# Virtual Assistant - 시스템 플로우차트 & 관계도

> 중간발표용 시각화 자료  
> 작성일: 2025-11-25

---

## 📋 목차

1. [전체 시스템 아키텍처](#1-전체-시스템-아키텍처)
2. [사용자 플로우 (User Flow)](#2-사용자-플로우-user-flow)
3. [브레인스토밍 모듈 상세](#3-브레인스토밍-모듈-상세)
4. [챗봇 모듈 상세](#4-챗봇-모듈-상세)
5. [RAG 시스템 관계도](#5-rag-시스템-관계도)
6. [프롬프트 엔지니어링 플로우](#6-프롬프트-엔지니어링-플로우)
7. [모듈 간 통신 구조](#7-모듈-간-통신-구조)

---

## 1. 전체 시스템 아키텍처

```mermaid
graph TB
    subgraph "Frontend Layer"
        A[Electron Desktop App]
        A1[Landing Page<br/>로그인/시작]
        A2[Chatbot UI<br/>대화형 인터페이스]
        A3[Brainstorming UI<br/>아이디어 생성]
        A --> A1
        A --> A2
        A --> A3
    end

    subgraph "Backend Layer - FastAPI"
        B[API Gateway<br/>main.py]
        B1[Auth Module<br/>OAuth 인증]
        B2[Chatbot Module<br/>대화 처리]
        B3[Brainstorming Module<br/>아이디어 생성]
        B4[Slack Module<br/>메시지 연동]
        B --> B1
        B --> B2
        B --> B3
        B --> B4
    end

    subgraph "AI/LLM Layer"
        C[OpenAI API]
        C1[GPT-4o<br/>대화 생성]
        C2[text-embedding-3-large<br/>벡터 임베딩]
        C3[TTS API<br/>음성 합성]
        C --> C1
        C --> C2
        C --> C3
    end

    subgraph "Data Layer"
        D[PostgreSQL<br/>사용자/세션 DB]
        E1[ChromaDB<br/>브레인스토밍 RAG]
        E2[ChromaDB<br/>챗봇 RAG]
        E3[Markdown Files<br/>채팅 히스토리]
    end

    A -.IPC.-> B
    B1 -.OAuth.-> Google[Google/Kakao/Naver]
    B2 --> C1
    B2 --> E2
    B2 --> E3
    B3 --> C1
    B3 --> C2
    B3 --> E1
    B1 --> D
    B4 -.Webhook.-> Slack[Slack API]

    style A fill:#e1f5ff
    style B fill:#fff4e6
    style C fill:#f3e5f5
    style D fill:#e8f5e9
    style E1 fill:#fff9c4
    style E2 fill:#fff9c4
    style E3 fill:#ffe0b2
```

---

## 2. 사용자 플로우 (User Flow)

```mermaid
flowchart TD
    Start([앱 실행]) --> Landing[Landing Page]
    Landing --> Login{로그인<br/>여부}
    
    Login -->|미로그인| OAuth[OAuth 로그인<br/>Google/Kakao/Naver]
    OAuth --> AuthSuccess{인증<br/>성공?}
    AuthSuccess -->|실패| OAuth
    AuthSuccess -->|성공| Landing
    
    Login -->|로그인됨| StartBtn[시작하기 클릭]
    StartBtn --> ChatMain[챗봇 메인 화면]
    
    ChatMain --> UserInput[사용자 메시지 입력]
    UserInput --> Intent{의도<br/>분석}
    
    Intent -->|일반 대화| NormalChat[GPT-4o 응답]
    NormalChat --> ChatMain
    
    Intent -->|아이디어 요청| BsModule[브레인스토밍<br/>모듈 실행]
    BsModule --> Phase1[Phase 1:<br/>목적 분석]
    Phase1 --> Phase2[Phase 2:<br/>키워드 수집]
    Phase2 --> Phase3[Phase 3:<br/>아이디어 생성]
    Phase3 --> Result[10개 아이디어<br/>+ 강점/약점]
    Result --> ChatMain
    
    Intent -->|Slack 연동| SlackModule[Slack 메시지 전송]
    SlackModule --> ChatMain
    
    ChatMain --> Logout{로그아웃?}
    Logout -->|예| Landing
    Logout -->|아니오| ChatMain

    style Landing fill:#e3f2fd
    style ChatMain fill:#f3e5f5
    style BsModule fill:#fff9c4
    style SlackModule fill:#e8f5e9
```

---

## 3. 브레인스토밍 모듈 상세

```mermaid
flowchart TB
    subgraph "입력 단계"
        A[사용자: 아이디어 목적 입력<br/>예: 소상공인 홍보 앱]
    end

    subgraph "Phase 1: 목적 분석 (30초)"
        B[IdeaGenerator.start_session]
        C[GPT-4o: 유도 질문 3개 생성]
        D[타이머: 30초 시작]
        B --> C --> D
    end

    subgraph "Phase 2: 키워드 수집 (30초)"
        E[사용자: 키워드 입력<br/>10~20개]
        F[EphemeralRAG: 임베딩 저장]
        G[session_uuid 별 임시 컬렉션]
        E --> F --> G
    end

    subgraph "Phase 3: 아이디어 생성"
        H[RAG 검색]
        I1[영구 RAG<br/>brainstorming_techniques<br/>매뉴얼 검색]
        I2[Ephemeral RAG<br/>session_uuid<br/>사용자 키워드 검색]
        J[직군 추론<br/>domain_hints.py]
        K[Prompt Engineering<br/>컨텍스트 조합]
        L[GPT-4o: 10개 아이디어 생성]
        M[각 아이디어:<br/>제목 + 설명 + 강점 + 약점]
        
        H --> I1
        H --> I2
        I1 --> K
        I2 --> K
        J --> K
        K --> L --> M
    end

    subgraph "후처리"
        N[Ephemeral RAG 삭제]
        O[세션 종료]
        M --> N --> O
    end

    A --> B
    D --> E
    G --> H

    style A fill:#e1f5ff
    style B fill:#fff4e6
    style E fill:#fff4e6
    style H fill:#f3e5f5
    style L fill:#f3e5f5
    style M fill:#c8e6c9
    style N fill:#ffccbc
```

---

## 4. 챗봇 모듈 상세

```mermaid
flowchart TB
    subgraph "세션 관리"
        A[사용자 로그인] --> B[세션 생성<br/>UUID 발급]
        B --> C[chat_history/<br/>session_uuid/<br/>폴더 생성]
    end

    subgraph "대화 처리"
        D[사용자 메시지 입력]
        E[ChatService.chat]
        F{RAG<br/>필요?}
        
        D --> E --> F
        
        F -->|예| G1[문서 검색<br/>ChromaDB]
        F -->|아니오| G2[대화 히스토리만 사용]
        
        G1 --> H[컨텍스트 조합]
        G2 --> H
        
        H --> I[Prompt Engineering]
        I --> J[GPT-4o API 호출]
        J --> K[AI 응답 생성]
    end

    subgraph "저장 & 요약"
        K --> L[Markdown 저장<br/>chat_YYYYMMDD_HHMMSS.md]
        L --> M{대화 길이<br/>10회 이상?}
        
        M -->|예| N[요약 생성<br/>GPT-4o]
        M -->|아니오| O[그대로 저장]
        
        N --> P[summary_YYYYMMDD.md]
        O --> Q[다음 대화 대기]
        P --> Q
    end

    C --> D
    K --> D

    style A fill:#e3f2fd
    style E fill:#fff4e6
    style J fill:#f3e5f5
    style L fill:#c8e6c9
    style N fill:#fff9c4
```

---

## 5. RAG 시스템 관계도

```mermaid
graph TB
    subgraph "RAG 시스템 전체 구조"
        subgraph "브레인스토밍 RAG"
            A1[영구 RAG<br/>brainstorming_techniques]
            A2[Ephemeral RAG<br/>session_uuid]
            A3[매뉴얼 데이터<br/>brainstorming_chunks.md]
            A4[사용자 키워드<br/>실시간 저장]
            
            A3 -.임베딩.-> A1
            A4 -.임베딩.-> A2
        end

        subgraph "챗봇 RAG (구현 예정)"
            B1[문서 RAG<br/>uploaded_docs]
            B2[회사 지식베이스<br/>company_knowledge]
            B3[PDF/Excel 업로드<br/>문서 파싱]
            B4[지식 관리<br/>Admin Panel]
            
            B3 -.임베딩.-> B1
            B4 -.임베딩.-> B2
        end

        subgraph "임베딩 엔진"
            C[OpenAI API<br/>text-embedding-3-large<br/>3072 차원]
        end

        subgraph "벡터 DB"
            D[ChromaDB<br/>Cosine Similarity 검색]
            D1[영구 컬렉션<br/>persistent]
            D2[임시 컬렉션<br/>ephemeral]
            
            D --> D1
            D --> D2
        end

        A1 --> D1
        A2 --> D2
        B1 --> D1
        B2 --> D1
        
        A3 --> C
        A4 --> C
        B3 --> C
        B4 --> C
        
        C -.벡터.-> D
    end

    subgraph "검색 & 활용"
        E[사용자 쿼리]
        F[유사도 검색<br/>Top-K]
        G[컨텍스트 조합]
        H[GPT-4o에 전달]
        
        E --> F
        F --> G
        G --> H
        
        D -.검색.-> F
    end

    style A1 fill:#fff9c4
    style A2 fill:#ffccbc
    style B1 fill:#c8e6c9
    style B2 fill:#c8e6c9
    style C fill:#f3e5f5
    style D fill:#e1f5ff
    style H fill:#f3e5f5
```

---

## 6. 프롬프트 엔지니어링 플로우

```mermaid
flowchart LR
    subgraph "입력 수집"
        A1[사용자 목적]
        A2[사용자 키워드]
        A3[대화 히스토리]
    end

    subgraph "컨텍스트 검색"
        B1[RAG 검색<br/>관련 문서]
        B2[직군 추론<br/>domain_hints]
        B3[시스템 페르소나<br/>역할 정의]
    end

    subgraph "프롬프트 조합"
        C[System Prompt<br/>+ 역할/규칙]
        D[RAG Context<br/>+ 관련 지식]
        E[User Input<br/>+ 현재 질문]
        F[Formatting Rules<br/>+ 출력 형식]
    end

    subgraph "LLM 실행"
        G[GPT-4o API]
        H[Temperature 조정<br/>창의성 vs 정확성]
        I[Max Tokens 제한]
    end

    subgraph "후처리"
        J[응답 파싱]
        K[형식 검증]
        L[사용자에게 반환]
    end

    A1 --> B1
    A2 --> B1
    A3 --> C
    
    B1 --> D
    B2 --> C
    B3 --> C
    
    C --> G
    D --> G
    E --> G
    F --> G
    
    G --> H
    H --> I
    I --> J
    J --> K
    K --> L

    style A1 fill:#e3f2fd
    style A2 fill:#e3f2fd
    style A3 fill:#e3f2fd
    style C fill:#fff4e6
    style D fill:#fff9c4
    style G fill:#f3e5f5
    style L fill:#c8e6c9
```

### 프롬프트 구조 예시

```
┌─────────────────────────────────────────────────┐
│ System Prompt (역할 정의)                        │
│ "당신은 실무 경험이 풍부한 기획자입니다."          │
└─────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────┐
│ RAG Context (검색된 지식)                        │
│ - 브레인스토밍 기법 매뉴얼 3개 문서               │
│ - 사용자 키워드 15개                             │
└─────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────┐
│ Domain Hints (직군별 가이드)                     │
│ "소상공인: 매출, 홍보, 예산, 이벤트 고려"         │
└─────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────┐
│ User Input (현재 요청)                           │
│ "목적: 소상공인 홍보 앱"                         │
└─────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────┐
│ Formatting Rules (출력 형식)                     │
│ "💡 아이디어 X: [제목]"                          │
│ "[설명 - 최소 3줄]"                              │
│ "✅ 강점 / ⚠️ 약점"                             │
└─────────────────────────────────────────────────┘
                      ↓
              [ GPT-4o 실행 ]
                      ↓
┌─────────────────────────────────────────────────┐
│ Output (10개 구체적 아이디어)                    │
└─────────────────────────────────────────────────┘
```

---

## 7. 모듈 간 통신 구조

```mermaid
graph TB
    subgraph "Frontend - Electron"
        F1[Landing Page<br/>script.js]
        F2[Chatbot UI<br/>chatbotService.js]
        F3[Brainstorming UI<br/>brainstormingService.js]
        F4[IPC Renderer<br/>프로세스 간 통신]
    end

    subgraph "Backend - FastAPI Router"
        R[API Gateway<br/>main.py]
        R1[Auth Router<br/>/api/v1/auth]
        R2[Chatbot Router<br/>/api/v1/chatbot]
        R3[Brainstorming Router<br/>/api/v1/brainstorming]
        R4[Slack Router<br/>/api/v1/slack]
    end

    subgraph "Domain Services"
        S1[Auth Service<br/>OAuth 처리]
        S2[Chat Service<br/>대화 로직]
        S3[Idea Generator<br/>아이디어 생성]
        S4[Slack Service<br/>메시지 전송]
    end

    subgraph "Core Components"
        C1[SessionManager<br/>세션 관리]
        C2[RAG Service<br/>벡터 검색]
        C3[Prompt Builder<br/>프롬프트 조합]
        C4[LLM Client<br/>OpenAI API]
    end

    F1 -.HTTP.-> R1
    F2 -.HTTP.-> R2
    F3 -.HTTP.-> R3
    F4 -.IPC.-> Main[Electron Main<br/>Process]

    R --> R1
    R --> R2
    R --> R3
    R --> R4

    R1 --> S1
    R2 --> S2
    R3 --> S3
    R4 --> S4

    S2 --> C1
    S2 --> C2
    S2 --> C4
    
    S3 --> C1
    S3 --> C2
    S3 --> C3
    S3 --> C4

    C2 -.검색.-> DB1[(ChromaDB)]
    C4 -.API.-> OpenAI[OpenAI API]
    S1 -.인증.-> OAuth[(OAuth Providers)]
    S4 -.Webhook.-> Slack[(Slack API)]

    style F1 fill:#e3f2fd
    style F2 fill:#e3f2fd
    style F3 fill:#e3f2fd
    style R fill:#fff4e6
    style S3 fill:#fff9c4
    style C4 fill:#f3e5f5
    style DB1 fill:#c8e6c9
```

---

## 8. 데이터 흐름 (Data Flow)

```mermaid
sequenceDiagram
    actor User as 사용자
    participant UI as Frontend UI
    participant API as FastAPI
    participant BsModule as Brainstorming<br/>Module
    participant RAG as RAG System
    participant LLM as GPT-4o
    participant DB as ChromaDB

    User->>UI: "아이디어 생성 시작"
    UI->>API: POST /brainstorming/session/start
    API->>BsModule: start_session(user_purpose)
    
    BsModule->>LLM: "3개 유도 질문 생성"
    LLM-->>BsModule: ["질문1", "질문2", "질문3"]
    BsModule-->>API: session_id + questions
    API-->>UI: 응답 반환
    UI-->>User: 유도 질문 표시 (30초 타이머)

    Note over User,UI: Phase 2: 키워드 수집
    User->>UI: 키워드 10개 입력
    UI->>API: POST /session/{id}/add-idea (10번)
    API->>BsModule: add_idea(keyword)
    BsModule->>DB: 임베딩 저장 (Ephemeral RAG)
    DB-->>BsModule: 저장 완료
    BsModule-->>API: 성공
    API-->>UI: 키워드 카운트

    Note over User,UI: Phase 3: 아이디어 생성
    User->>UI: "생성하기" 클릭
    UI->>API: POST /session/{id}/generate
    API->>BsModule: generate_ideas()
    
    BsModule->>RAG: search_permanent_rag("소상공인 홍보")
    RAG->>DB: 벡터 검색 (영구 컬렉션)
    DB-->>RAG: 매뉴얼 3개 문서
    RAG-->>BsModule: 관련 지식 반환
    
    BsModule->>RAG: search_ephemeral_rag(session_id)
    RAG->>DB: 벡터 검색 (임시 컬렉션)
    DB-->>RAG: 사용자 키워드 15개
    RAG-->>BsModule: 키워드 컨텍스트
    
    BsModule->>BsModule: infer_job_domain() → "소상공인"
    BsModule->>BsModule: build_prompt() → 프롬프트 조합
    
    BsModule->>LLM: "10개 아이디어 생성 (구체적)"
    LLM-->>BsModule: 10개 아이디어 + 강점/약점
    
    BsModule->>DB: delete_collection(session_id)
    DB-->>BsModule: Ephemeral RAG 삭제 완료
    
    BsModule-->>API: 10개 아이디어
    API-->>UI: 응답 반환
    UI-->>User: 아이디어 목록 표시
```

---

## 9. 기술 스택 맵

```mermaid
mindmap
  root((Virtual<br/>Assistant))
    Frontend
      Electron
        Desktop App
        IPC Communication
      HTML/CSS/JS
        Landing Page
        Chatbot UI
        Brainstorming UI
      
    Backend
      FastAPI
        REST API
        Async/Await
        Pydantic Models
      Python 3.10+
        Type Hints
        Async IO
      
    AI/LLM
      OpenAI API
        GPT-4o
        text-embedding-3-large
        TTS API
      LangChain
        RAG Pipeline
        Document Loaders
      
    Database
      PostgreSQL
        User Info
        Session Data
      ChromaDB
        Vector Store
        Cosine Similarity
      Markdown
        Chat History
        Summaries
      
    Infrastructure
      OAuth 2.0
        Google
        Kakao
        Naver
      Slack API
        Webhook
        Bot Token
      Git
        Version Control
        Team Collaboration
```

---

## 10. 주요 모듈별 책임 (Responsibility Map)

| 모듈 | 책임 | 입력 | 출력 |
|------|------|------|------|
| **Frontend** | UI 렌더링, 사용자 이벤트 처리 | 사용자 클릭/입력 | HTTP 요청 |
| **API Gateway** | 라우팅, 인증 검증 | HTTP 요청 | JSON 응답 |
| **Auth Module** | OAuth 인증, 토큰 관리 | 인증 코드 | 세션 쿠키 |
| **Chatbot Module** | 대화 처리, 히스토리 저장 | 사용자 메시지 | AI 응답 |
| **Brainstorming Module** | 아이디어 생성, RAG 검색 | 목적 + 키워드 | 10개 아이디어 |
| **RAG Service** | 벡터 검색, 임베딩 생성 | 쿼리 텍스트 | 관련 문서 |
| **SessionManager** | 세션 생성/관리/삭제 | 사용자 ID | 세션 ID |
| **LLM Client** | OpenAI API 호출 | 프롬프트 | AI 응답 |
| **Prompt Builder** | 프롬프트 조합, 컨텍스트 구성 | RAG 결과 + 사용자 입력 | 완성된 프롬프트 |
| **Slack Module** | 메시지 전송, Webhook | 메시지 내용 | 전송 결과 |

---

## 11. 배포 아키텍처 (예정)

```mermaid
graph TB
    subgraph "사용자 디바이스"
        A[Electron App<br/>Windows/Mac/Linux]
    end

    subgraph "Cloud Server (AWS/GCP)"
        B[Nginx<br/>Reverse Proxy]
        C[FastAPI Server<br/>Uvicorn x4]
        D[PostgreSQL<br/>Master]
        E[Redis<br/>Session Cache]
    end

    subgraph "External Services"
        F[OpenAI API]
        G[OAuth Providers<br/>Google/Kakao/Naver]
        H[Slack API]
    end

    subgraph "Storage"
        I[S3 / Cloud Storage<br/>ChromaDB 백업]
        J[Local SSD<br/>ChromaDB 실시간]
    end

    A -.HTTPS.-> B
    B --> C
    C --> D
    C --> E
    C --> J
    C -.API.-> F
    C -.OAuth.-> G
    C -.Webhook.-> H
    J -.백업.-> I

    style A fill:#e3f2fd
    style B fill:#fff4e6
    style C fill:#fff4e6
    style F fill:#f3e5f5
    style J fill:#c8e6c9
```

---

## 📊 발표 시 활용 팁

### **1. 전체 시스템 아키텍처** → 프로젝트 개요 소개
- "우리 프로젝트는 Electron 기반 데스크톱 앱으로..."
- Frontend → Backend → AI → Data 레이어 설명

### **2. 사용자 플로우** → 사용자 경험 설명
- "사용자가 앱을 실행하면..."
- 로그인 → 챗봇 → 브레인스토밍 흐름

### **3. 브레인스토밍 모듈 상세** → 핵심 기능 강조
- "3단계로 아이디어를 생성합니다"
- Phase별 타이머, RAG 활용 강조

### **4. RAG 시스템** → 기술적 차별화
- "영구 + 임시 RAG 이중 구조로..."
- ChromaDB, OpenAI 임베딩 활용

### **5. 프롬프트 엔지니어링** → AI 품질 향상 방법
- "단순 LLM 호출이 아니라..."
- 컨텍스트 조합, 직군별 힌트

### **6. 모듈 간 통신** → 아키텍처 설계 역량
- "DDD 구조로 모듈을 격리..."
- FastAPI Router, Domain Service 분리

---

## 🎨 시각화 도구 추천

### **Mermaid → 다른 도구 변환**

1. **draw.io (diagrams.net)**
   - 위 Mermaid 다이어그램을 참고하여 수동 작성
   - 더 예쁜 아이콘, 색상 커스터마이징

2. **Figma**
   - UI/UX 디자인 툴로 플로우차트 작성
   - 팀원과 공유 가능

3. **Lucidchart**
   - 전문 다이어그램 툴
   - Mermaid import 지원

4. **Excalidraw**
   - 손그림 스타일 다이어그램
   - 발표 자료에 친근한 느낌

---

## 📌 GitHub에서 보는 방법

이 파일을 GitHub에 푸시하면 Mermaid 다이어그램이 자동으로 렌더링됩니다!

```bash
git add SYSTEM_FLOWCHART.md
git commit -m "docs: 시스템 플로우차트 추가"
git push
```

---

**작성 완료!** 🎉

**추가 다이어그램이나 수정이 필요하면 말씀해주세요!** 😊

