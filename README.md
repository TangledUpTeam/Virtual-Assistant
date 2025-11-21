# 🤖 Virtual Desk Assistant

AI 기반 Live2D 캐릭터 데스크톱 비서 with RAG 시스템

---

## 📋 목차

- [프로젝트 개요](#프로젝트-개요)
- [주요 기능](#주요-기능)
- [기술 스택](#기술-스택)
- [빠른 시작](#빠른-시작)
- [사용 방법](#사용-방법)
- [RAG 시스템](#rag-시스템)
- [프로젝트 구조](#프로젝트-구조)
- [API 문서](#api-문서)
- [개발 가이드](#개발-가이드)
- [문제 해결](#문제-해결)

---

## 🎯 프로젝트 개요

**Virtual Desk Assistant**는 Live2D 캐릭터와 AI를 결합한 차세대 데스크톱 비서입니다.

### 특징
- 🎭 **Live2D 캐릭터**: 투명 전체화면에서 상주하는 인터랙티브 캐릭터
- 💬 **RAG 기반 챗봇**: 사내 문서를 학습한 AI 비서
- 🔐 **OAuth 로그인**: Google, Kakao, Naver 간편 로그인
- 📚 **문서 관리**: PDF 업로드 및 자동 처리
- 🖱️ **클릭-스루 UI**: 배경 투명, 캐릭터만 상호작용

---

## ✨ 주요 기능

### 1️⃣ Frontend (Electron)
- **Live2D 렌더링**: PixiJS 기반 캐릭터 애니메이션
- **채팅 패널**: 왼쪽 고정 패널에서 AI와 대화
  - Enter: 메시지 전송
  - Cmd/Ctrl + Enter: 패널 토글
- **드래그 앤 드롭**: 캐릭터 위치 조정
- **크기 조절**: +/- 키로 스케일 변경

### 2️⃣ Backend (FastAPI)
- **OAuth 2.0**: Google, Kakao, Naver 소셜 로그인
- **RAG 시스템**: 
  - PDF 파싱 및 벡터화
  - 한국어 특화 임베딩 (KoSentenceBERT)
  - GPT-4o 기반 답변 생성
  - LangSmith 추적 지원
- **REST API**: 완전한 REST API 제공

### 3️⃣ RAG 시스템
- **문서 처리**: PDF → 텍스트/표/이미지 추출
- **벡터 검색**: ChromaDB 기반 유사도 검색
- **답변 생성**: 문서 컨텍스트 기반 정확한 답변
- **CLI 도구**: 터미널에서 문서 관리 및 질의응답

---

## 🛠️ 기술 스택

### Frontend
| 분류 | 기술 |
|------|------|
| Framework | Electron |
| Rendering | Live2D Cubism, PixiJS |
| Language | JavaScript |

### Backend
| 분류 | 기술 |
|------|------|
| Framework | FastAPI, Uvicorn |
| Database | PostgreSQL, ChromaDB |
| ORM | SQLAlchemy, Alembic |
| Authentication | OAuth 2.0, JWT |
| LLM | OpenAI GPT-4o |
| Embedding | KoSentenceBERT |
| Vector DB | ChromaDB |
| Tracing | LangSmith |

---

## 🚀 빠른 시작

### 1️⃣ 사전 요구사항
- **Python**: 3.10 이상
- **Node.js**: 18 이상
- **PostgreSQL**: 14 이상 (선택사항)
- **Conda**: 가상환경 관리

### 2️⃣ 설치

```bash
# 저장소 클론
git clone https://github.com/TangledUpTeam/Virtual-Assistant.git
cd Virtual-Assistant

# 가상환경 생성
conda create -n virtual_assistant python=3.11
conda activate virtual_assistant

# 백엔드 의존성 설치
cd Virtual-Assistant/backend
pip install -r requirements.txt

# 프론트엔드 의존성 설치
cd ..
npm install
```

### 3️⃣ 환경변수 설정

```bash
# backend/.env 파일 생성
cp backend/.env.example backend/.env

# .env 파일 수정 (필수)
# - OPENAI_API_KEY: OpenAI API 키
# - DATABASE_URL: 데이터베이스 연결 문자열
# - SECRET_KEY: JWT 비밀키
# - OAuth 설정 (Google, Kakao, Naver)
```

### 4️⃣ 데이터베이스 설정 (선택사항)

```bash
# PostgreSQL 생성
createdb virtual-assistant

# 마이그레이션 실행
cd backend
alembic revision --autogenerate -m "Initial"
alembic upgrade head
```

### 5️⃣ 실행

```bash
# 한 번에 실행 (백엔드 + Electron)
npm start

# 또는 개별 실행
# 백엔드만
npm run start:backend

# Electron만 (백엔드가 이미 실행 중일 때)
npm run start:electron
```

---

## 📖 사용 방법

### 로그인
1. 앱 시작 시 로그인 창 표시
2. Google, Kakao, Naver 중 선택
3. OAuth 인증 완료 후 자동 로그인 유지

### 캐릭터 상호작용
- **드래그**: 캐릭터를 클릭하고 드래그하여 이동
- **크기 조절**: `+` / `-` 키
- **종료**: `ESC` 키
- **개발자 도구**: `F12`

### 채팅
- **메시지 전송**: 입력 후 Enter
- **패널 토글**: Cmd/Ctrl + Enter
- **질문 예시**:
  - "휴가 신청 방법은?"
  - "연차 규정 알려줘"
  - "복지 혜택은 뭐가 있어?"

---

## 📚 RAG 시스템

### 특징
- **한국어 특화**: KoSentenceBERT 임베딩 모델
- **정확한 답변**: 문서 기반 응답 (환각 방지)
- **참고 문서 제공**: 답변 근거 제시
- **LangSmith 추적**: 실시간 디버깅

### CLI 사용법

```bash
cd backend

# 문서 업로드
python -m app.domain.rag.cli upload internal_docs/uploads

# 대화형 질의응답
python -m app.domain.rag.cli query

# 통계 확인
python -m app.domain.rag.cli stats

# 컬렉션 초기화
python -m app.domain.rag.cli reset --yes
```

### API 사용법

```bash
# PDF 업로드
curl -X POST http://localhost:8000/api/v1/rag/upload \
  -F "file=@document.pdf"

# 질의응답
curl -X POST http://localhost:8000/api/v1/rag/query \
  -H "Content-Type: application/json" \
  -d '{"query": "휴가 신청 방법은?"}'
```

### RAG 처리 흐름

```
PDF 파일
  ↓
[1] PDF 파싱 (PyMuPDF, pdfplumber)
  ├─ 텍스트 추출
  ├─ 표 → JSON
  └─ 이미지 → 설명 (GPT-4 Vision)
  ↓
[2] 문서 변환 (LangChain)
  └─ 마크다운 + 청킹 (400토큰)
  ↓
[3] 임베딩 (KoSentenceBERT)
  └─ 768차원 벡터 생성
  ↓
[4] 저장 (ChromaDB)
  └─ 벡터 + 메타데이터 저장
```

```
사용자 질문
  ↓
[1] 질문 임베딩
  ↓
[2] 유사도 검색 (Top-3)
  ↓
[3] 컨텍스트 구성
  ↓
[4] GPT-4o 답변 생성
  ↓
답변 + 참고 문서
```

### LangSmith 설정

```bash
# 1. API Key 발급: https://smith.langchain.com
# 2. .env 파일에 추가
LANGSMITH_API_KEY=lsv2_pt_your_key_here
LANGSMITH_PROJECT=virtual-assistant-rag
LANGSMITH_TRACING=true

# 3. 실행 후 대시보드 확인
# https://smith.langchain.com → virtual-assistant-rag
```

---

## 📁 프로젝트 구조

```
Virtual-Assistant/
├── backend/                    # FastAPI 백엔드
│   ├── app/
│   │   ├── api/               # API 엔드포인트
│   │   │   └── v1/
│   │   │       └── endpoints/
│   │   │           ├── auth.py       # OAuth 로그인
│   │   │           ├── users.py      # 사용자 관리
│   │   │           └── rag.py        # RAG API
│   │   ├── core/              # 핵심 설정
│   │   │   ├── config.py
│   │   │   └── security.py
│   │   ├── domain/            # 도메인 로직
│   │   │   ├── user/
│   │   │   ├── auth/
│   │   │   └── rag/           # RAG 시스템
│   │   │       ├── config.py
│   │   │       ├── pdf_processor.py
│   │   │       ├── document_converter.py
│   │   │       ├── vector_store.py
│   │   │       ├── retriever.py
│   │   │       ├── cli.py
│   │   │       └── schemas.py
│   │   ├── infrastructure/    # 인프라
│   │   │   ├── database/
│   │   │   └── oauth/
│   │   └── main.py
│   ├── internal_docs/         # 문서 저장소
│   │   ├── uploads/           # 업로드 PDF
│   │   ├── processed/         # 처리된 JSON
│   │   └── chroma/            # 벡터 DB
│   ├── requirements.txt
│   └── alembic/               # DB 마이그레이션
├── frontend/                   # 프론트엔드 페이지
│   ├── Login/                 # 로그인
│   └── Start/                 # 시작 페이지
├── renderer/                   # 렌더러 모듈
│   └── chat/                  # 채팅 모듈
├── public/                     # 정적 파일
│   └── models/                # Live2D 모델
├── main.js                     # Electron 메인
├── index.html                  # 캐릭터 화면
├── package.json
└── README.md
```

---

## 📡 API 문서

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

### RAG

| Method | Endpoint | 설명 |
|--------|----------|------|
| POST | `/api/v1/rag/upload` | PDF 업로드 |
| POST | `/api/v1/rag/query` | 질의응답 |
| GET | `/api/v1/rag/stats` | 통계 조회 |
| DELETE | `/api/v1/rag/document/{id}` | 문서 삭제 |
| POST | `/api/v1/rag/reset` | 컬렉션 초기화 |

### Users

| Method | Endpoint | 설명 |
|--------|----------|------|
| GET | `/api/v1/users/me` | 내 정보 |
| PUT | `/api/v1/users/me` | 정보 수정 |
| DELETE | `/api/v1/users/me` | 회원 탈퇴 |

**Swagger UI**: http://localhost:8000/docs

---

## 🔧 개발 가이드

### 백엔드 개발

```bash
# 개발 모드 실행
cd backend
uvicorn app.main:app --reload

# 테스트
pytest

# 마이그레이션
alembic revision --autogenerate -m "Description"
alembic upgrade head
```

### 프론트엔드 개발

```bash
# Electron 디버깅
npm run start:electron

# 패키지 빌드
npm run build
```

### RAG 개발

```bash
# 모듈 테스트
python -m app.domain.rag.cli stats

# 새 문서 처리 테스트
python -m app.domain.rag.cli upload test.pdf

# 질의응답 테스트
python -m app.domain.rag.cli query "테스트 질문"
```

---

## 🐛 문제 해결

### Electron 창이 안 뜨는 경우
- 백엔드가 먼저 실행되어야 합니다
- `http://localhost:8000/health` 확인

### OAuth 로그인 실패
- `.env` 파일의 OAuth 설정 확인
- 리다이렉트 URI 일치 여부 확인

### RAG 검색이 안 되는 경우
- 문서가 업로드되었는지 확인: `python -m app.domain.rag.cli stats`
- OPENAI_API_KEY 설정 확인
- 첫 실행 시 모델 다운로드 시간 필요 (약 500MB)

### 유사도가 0으로 나오는 경우
- 컬렉션 초기화 후 재업로드:
  ```bash
  python -m app.domain.rag.cli reset --yes
  python -m app.domain.rag.cli upload internal_docs/uploads
  ```

---

## 📝 최신 업데이트 (2025-11-18)

### ✅ RAG 시스템 개선
1. **유사도 필터링 수정**: L2 distance → 지수 감쇠 함수
2. **UUID 기반 청크 ID**: 재처리 시 충돌 방지
3. **LangSmith 통합**: 실시간 추적 및 디버깅
4. **Small Talk 제거**: 모든 질문을 RAG로 처리
5. **CLI 초기화 기능**: `reset` 명령어 추가

### 테스트 결과
- **유사도 계산**: 0.0 → 0.43 ✅
- **문서 검색**: 실패 → 성공 ✅
- **청크 ID**: 파일명 기반 → UUID ✅

상세 내용: `backend/CHANGELOG.md` 참조

---

## 👥 팀원
- **진모님**: 화면 감지
- **도연님**: 챗봇
- **윤아님**: 챗봇
- **준경님**: 보고서 작성
- **제헌님**: 심리 상담

---

## 📝 라이선스
MIT License

---

## 📧 문의
이슈를 통해 문의해주세요.

GitHub: https://github.com/TangledUpTeam/Virtual-Assistant

---

**🎉 Virtual Desk Assistant - AI와 함께하는 스마트한 하루!**
