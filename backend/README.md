# 🤖 Virtual Desk Assistant - Backend

AI-powered Multi-Agent Virtual Desktop Assistant Backend API

## 📋 목차

- [프로젝트 개요](#프로젝트-개요)
- [기술 스택](#기술-스택)
- [시작하기](#시작하기)
- [API 문서](#api-문서)
- [데이터베이스](#데이터베이스)
- [환경변수](#환경변수)

---

## 🎯 프로젝트 개요

**Virtual Desk Assistant**는 AI를 활용한 Multi-Agent 버튜버 비서 시스템입니다.

### 주요 기능
- 🔐 **OAuth 2.0 로그인** (Google, Kakao, Naver)
- 💬 **RAG 기반 챗봇** (사내 매뉴얼 검색)
- 🤖 **LLM Agent** (파일 읽기, 음악 재생 등)
- 📊 **보고서 작성 Agent**
- 👀 **화면 감지 Agent**
- 💭 **심리 상담 Agent**
- 💬 **Slack 연동**

---

## 🛠 기술 스택

| 분류 | 기술 |
|------|------|
| **Framework** | FastAPI, Uvicorn |
| **Database** | PostgreSQL, pgvector |
| **ORM** | SQLAlchemy, Alembic |
| **Authentication** | OAuth 2.0, JWT |
| **Vector DB** | ChromaDB, Redis |
| **LLM** | OpenAI GPT-4o |
| **Architecture** | DDD (Domain-Driven Design) |

---

## 🚀 시작하기

### 1️⃣ 사전 요구사항

- Python 3.11+
- PostgreSQL 14+
- Conda (가상환경)

### 2️⃣ 설치

```bash
# 1. 가상환경 생성 및 활성화
conda create -n virtual-assistant python=3.11
conda activate virtual-assistant

# 2. 의존성 설치
cd backend
pip install -r requirements.txt

# 3. 환경변수 설정
cp .env.example .env
# .env 파일을 열어서 실제 값으로 수정
```

### 3️⃣ 데이터베이스 설정

```bash
# PostgreSQL 접속
psql -d postgres

# DB 생성
CREATE DATABASE "virtual-assistant";
\q

# Alembic 마이그레이션 초기화
alembic revision --autogenerate -m "Initial migration"
alembic upgrade head
```

### 4️⃣ 서버 실행

```bash
# 개발 모드 (자동 리로드)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 또는
python -m app.main
```

서버가 실행되면:
- API 문서: http://localhost:8000/docs
- Health Check: http://localhost:8000/health

---

## 📚 API 문서

### Authentication

| Method | Endpoint | 설명 |
|--------|----------|------|
| GET | `/api/v1/auth/google/login` | Google 로그인 URL |
| GET | `/api/v1/auth/google/callback` | Google 콜백 |
| GET | `/api/v1/auth/kakao/login` | Kakao 로그인 URL |
| GET | `/api/v1/auth/kakao/callback` | Kakao 콜백 |
| GET | `/api/v1/auth/naver/login` | Naver 로그인 URL |
| GET | `/api/v1/auth/naver/callback` | Naver 콜백 |
| POST | `/api/v1/auth/refresh` | Token 갱신 |

### Users

| Method | Endpoint | 설명 |
|--------|----------|------|
| GET | `/api/v1/users/me` | 내 정보 조회 |
| PUT | `/api/v1/users/me` | 내 정보 수정 |
| DELETE | `/api/v1/users/me` | 회원 탈퇴 |
| GET | `/api/v1/users/{user_id}` | 사용자 조회 |

### OAuth 로그인 플로우

```
1. 프론트엔드 → GET /api/v1/auth/google/login
   ← { "authorization_url": "https://..." }

2. 사용자가 Google 로그인

3. Google → GET /api/v1/auth/google/callback?code=...
   ← { "access_token": "...", "refresh_token": "...", "user": {...} }

4. 프론트엔드는 access_token을 저장하고 요청 시 Header에 포함:
   Authorization: Bearer {access_token}
```

---

## 🗄️ 데이터베이스

### ERD (Entity Relationship Diagram)

```
┌─────────────────┐
│     Users       │
├─────────────────┤
│ id (PK)         │
│ email (unique)  │
│ name            │
│ profile_image   │
│ oauth_provider  │
│ oauth_id        │
│ created_at      │
│ updated_at      │
│ last_login_at   │
└─────────────────┘
```

### 마이그레이션

```bash
# 새 마이그레이션 생성
alembic revision --autogenerate -m "Description"

# 마이그레이션 적용
alembic upgrade head

# 이전 버전으로 롤백
alembic downgrade -1

# 마이그레이션 히스토리 확인
alembic history
```

---

## 🔐 환경변수

`.env` 파일에 다음 값들을 설정하세요:

### 필수 설정

```env
# Database
DATABASE_URL=postgresql://jinmokim@localhost:5432/virtual-assistant

# JWT
SECRET_KEY=your-secret-key-here

# OAuth - Google
GOOGLE_CLIENT_ID=your-client-id
GOOGLE_CLIENT_SECRET=your-client-secret

# OAuth - Kakao
KAKAO_CLIENT_ID=your-client-id
KAKAO_CLIENT_SECRET=your-client-secret

# OAuth - Naver
NAVER_CLIENT_ID=your-client-id
NAVER_CLIENT_SECRET=your-client-secret

# OpenAI
OPENAI_API_KEY=sk-your-api-key
```

### OAuth Client ID/Secret 발급 방법

#### Google
1. [Google Cloud Console](https://console.cloud.google.com/) 접속
2. 프로젝트 생성
3. **API 및 서비스 → OAuth 동의 화면** 설정
4. **사용자 인증 정보 → OAuth 2.0 클라이언트 ID** 생성
5. 승인된 리디렉션 URI 추가: `http://localhost:8000/api/v1/auth/google/callback`

#### Kakao
1. [Kakao Developers](https://developers.kakao.com/) 접속
2. 애플리케이션 추가
3. **내 애플리케이션 → 앱 설정 → 앱 키**에서 REST API 키 복사
4. **제품 설정 → 카카오 로그인** 활성화
5. Redirect URI 추가: `http://localhost:8000/api/v1/auth/kakao/callback`

#### Naver
1. [Naver Developers](https://developers.naver.com/) 접속
2. 애플리케이션 등록
3. **API 설정**에서 Client ID, Client Secret 확인
4. Callback URL 추가: `http://localhost:8000/api/v1/auth/naver/callback`

---

## 📁 프로젝트 구조 (DDD)

```
backend/
├── app/
│   ├── domain/              # 도메인 로직
│   │   ├── user/
│   │   │   ├── models.py      # User 엔티티
│   │   │   ├── schemas.py     # Pydantic 스키마
│   │   │   ├── repository.py  # 데이터 접근
│   │   │   └── service.py     # 비즈니스 로직
│   │   └── auth/
│   │       ├── schemas.py
│   │       ├── service.py
│   │       └── dependencies.py
│   ├── infrastructure/      # 인프라 레이어
│   │   ├── database/
│   │   │   ├── session.py
│   │   │   └── base.py
│   │   └── oauth/
│   │       ├── google.py
│   │       ├── kakao.py
│   │       └── naver.py
│   ├── api/                 # API 레이어
│   │   └── v1/
│   │       ├── endpoints/
│   │       │   ├── auth.py
│   │       │   └── users.py
│   │       └── router.py
│   ├── core/                # 핵심 설정
│   │   ├── config.py
│   │   └── security.py
│   └── main.py              # FastAPI 앱
├── alembic/                 # DB 마이그레이션
├── .env                     # 환경변수
├── .gitignore
├── requirements.txt
└── README.md
```

---

## 🧪 테스트

```bash
# 테스트 실행
pytest

# 커버리지 포함
pytest --cov=app tests/
```

---

## 👥 팀원

- **진모님**: 화면 감지
- **도연님**: 챗봇
- **윤아님**: 챗봇
- **준경님**: 보고서 작성
- **제헌님**: 상담

---

## 📝 License

MIT License

---

## 🔗 Links

- [API 문서](http://localhost:8000/docs)
- [프로젝트 기획서](../VirtualDeskAssistant_ProjectPlan.md)
- [GitHub Repository](https://github.com/TangledUpTeam/Virtual-Assistant)
