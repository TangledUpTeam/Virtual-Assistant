# 🤖 Virtual Desk Assistant

AI 기반 데스크톱 Live2D 캐릭터 비서

## 📋 목차
- [기능](#기능)
- [기술 스택](#기술-스택)
- [설치 및 실행](#설치-및-실행)
- [사용 방법](#사용-방법)
- [프로젝트 구조](#프로젝트-구조)

## ✨ 기능

- 🎭 **Live2D 캐릭터**: 투명 전체화면에서 상주하는 캐릭터
- 💬 **채팅 패널**: 왼쪽 고정 패널에서 AI와 대화
  - 반투명 아이보리 색상 디자인
  - Enter 키로 메시지 전송
  - Cmd/Ctrl + Enter로 패널 토글
  - 메시지 히스토리 유지
- 🔐 **OAuth 로그인**: Google, Kakao, Naver 로그인 지원
- 💬 **AI 대화**: OpenAI GPT 기반 자연스러운 대화 (추후 연동)
- 📚 **RAG 시스템**: 문서 기반 질의응답 (추후 연동)
- 🖱️ **클릭-스루**: 배경은 클릭 불가, 캐릭터와 채팅 패널만 상호작용 가능

## 🛠️ 기술 스택

### Frontend (Electron)
- **Electron**: 데스크톱 앱 프레임워크
- **Live2D Cubism**: 캐릭터 렌더링
- **PixiJS**: 2D 그래픽 렌더링

### Backend (FastAPI)
- **FastAPI**: 고성능 웹 프레임워크
- **SQLAlchemy**: ORM
- **PostgreSQL**: 데이터베이스
- **OAuth 2.0**: 소셜 로그인
- **OpenAI API**: AI 대화 엔진

## 🚀 설치 및 실행

### 1. 필수 요구사항

- **Python**: 3.10 이상
- **Node.js**: 18 이상
- **PostgreSQL**: 14 이상 (선택사항)

### 2. 저장소 클론

```bash
git clone https://github.com/TangledUpTeam/Virtual-Assistant.git
cd Virtual-Assistant
```

### 3. 백엔드 설정

```bash
# Python 패키지 설치
cd backend
pip install -r requirements.txt

# 환경변수 설정
cp .env.example .env
# .env 파일을 열어서 필요한 값들을 설정하세요:
# - DATABASE_URL
# - SECRET_KEY
# - OAuth 클라이언트 ID/SECRET (Google, Kakao, Naver)
# - OPENAI_API_KEY
```

### 4. 프론트엔드 설정

```bash
# 프로젝트 루트로 돌아가기
cd ..

# Node 패키지 설치
npm install
```

### 5. 실행

```bash
# 한 번에 백엔드와 Electron 실행
npm start
```

이 명령어는 자동으로:
1. Python 백엔드 서버 시작 (포트 8000)
2. 백엔드 준비 완료 대기
3. Electron 앱 실행 → 로그인 창 표시

## 📖 사용 방법

### 1. 로그인

앱을 시작하면 로그인 창이 나타납니다.
- Google, Kakao, 또는 Naver로 로그인하세요.
- **한 번 로그인하면 다음부터는 자동으로 로그인됩니다!** 🎉

### 2. 시작하기

로그인 후 시작 페이지에서 "시작하기" 버튼을 클릭합니다.
- 로그인 창이 자동으로 닫히고
- 캐릭터가 투명 전체화면에 나타납니다.

### 3. 캐릭터와 상호작용

- **드래그**: 캐릭터를 클릭하고 드래그하여 이동
- **채팅**: 왼쪽 채팅 패널에서 AI와 대화
  - **Enter**: 메시지 전송
  - **Cmd/Ctrl + Enter**: 채팅 패널 토글 (숨기기/표시)
- **+/-**: 캐릭터 크기 조절
- **ESC**: 앱 종료
- **F12**: 개발자 도구

### 💡 채팅 패널 사용법

- **메시지 전송**: 입력창에 텍스트를 입력하고 Enter 키를 누르거나 전송 버튼 클릭
- **패널 토글**: Cmd (Mac) 또는 Ctrl (Windows/Linux) + Enter 키로 채팅 패널 숨기기/표시
- **메시지 히스토리**: 패널을 숨겨도 대화 내용은 유지됩니다
- **현재 상태**: 더미 응답만 제공 (GPT/RAG 연동 예정)

### 💡 세션 관리

- **앱 실행 중에만 로그인 유지**: 앱을 닫으면 로그인 정보가 삭제됩니다
- **브라우저 세션 활용**: Google/Kakao/Naver에 브라우저에서 이미 로그인되어 있으면 동의만으로 빠르게 로그인됩니다
- **로그아웃**: 시작 페이지에서 "로그아웃" 버튼을 클릭하면 즉시 로그인 화면으로 돌아갑니다

## 📁 프로젝트 구조

```
Virtual-Assistant/
├── backend/                 # FastAPI 백엔드
│   ├── app/
│   │   ├── api/            # API 엔드포인트
│   │   │   └── v1/
│   │   │       └── endpoints/
│   │   │           ├── auth.py      # OAuth 로그인
│   │   │           └── users.py     # 사용자 관리
│   │   ├── core/           # 핵심 설정
│   │   ├── domain/         # 도메인 로직
│   │   ├── infrastructure/ # 인프라 (DB, OAuth)
│   │   └── main.py         # FastAPI 앱
│   └── requirements.txt
├── frontend/               # 프론트엔드 페이지
│   ├── Login/             # 로그인 페이지
│   └── Start/             # 시작 페이지
├── renderer/              # 렌더러 프로세스 모듈
│   └── chat/              # 채팅 모듈
│       ├── chatPanel.js   # UI + 상태 관리
│       └── chatService.js # 챗봇 호출 로직
├── public/                # 정적 파일
│   └── models/            # Live2D 모델
├── main.js                # Electron 메인 프로세스
├── index.html             # 캐릭터 + 채팅 화면
├── package.json
└── README.md
```

## 🔧 개발

### 백엔드만 실행
```bash
npm run start:backend
# 또는
python assistant.py
```

### Electron만 실행 (백엔드가 이미 실행 중일 때)
```bash
npm run start:electron
```

### API 문서 확인
백엔드 실행 후: http://localhost:8000/docs

## 🐛 문제 해결

### 1. Electron 창이 안 뜨는 경우
- 백엔드가 먼저 실행되어야 합니다
- `http://localhost:8000/health`가 응답하는지 확인하세요

### 2. OAuth 로그인이 안 되는 경우
- `.env` 파일에 OAuth 클라이언트 ID/SECRET이 설정되어 있는지 확인
- 리다이렉트 URI가 OAuth 앱 설정과 일치하는지 확인
  - Google: `http://localhost:8000/api/v1/auth/google/callback`
  - Kakao: `http://localhost:8000/api/v1/auth/kakao/callback`
  - Naver: `http://localhost:8000/api/v1/auth/naver/callback`

### 3. 캐릭터가 안 보이는 경우
- `public/models/` 폴더에 Live2D 모델이 있는지 확인
- F12로 개발자 도구를 열어 콘솔 에러 확인

## 📝 라이선스

MIT License

## 👥 기여

Pull Request 환영합니다!

## 📧 문의

이슈를 통해 문의해주세요.

