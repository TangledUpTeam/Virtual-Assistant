# Virtual Assistant 설치 가이드

## 📋 필수 요구사항

- **Node.js** 16 이상
- **Python** 3.9 이상
- **PostgreSQL** (선택사항: SQLite로 대체 가능)

---

## 🚀 설치 방법

### 1️⃣ 프로젝트 클론 및 이동

```bash
git clone <repository-url>
cd Virtual-Assistant
```

---

### 2️⃣ Node.js 의존성 설치

```bash
npm install
```

---

### 3️⃣ Python 백엔드 설정

#### 방법 A: conda 사용 (권장)

```bash
# 가상환경 생성
conda create -n virtual-assistant python=3.10

# 가상환경 활성화
conda activate virtual-assistant

# 의존성 설치
pip install -r backend/requirements.txt
```

#### 방법 B: venv 사용 (conda 없을 때)

**Mac/Linux**:
```bash
# 가상환경 생성
python3 -m venv venv

# 가상환경 활성화
source venv/bin/activate

# 의존성 설치
pip install -r backend/requirements.txt
```

**Windows**:
```cmd
# 가상환경 생성
python -m venv venv

# 가상환경 활성화
venv\Scripts\activate

# 의존성 설치
pip install -r backend\requirements.txt
```

---

### 4️⃣ 환경변수 설정 (선택사항)

백엔드 폴더에 `.env` 파일을 생성하세요:

```bash
cd backend
cp .env.example .env
```

`.env` 파일 내용 예시:
```env
# Database (SQLite 기본)
DATABASE_URL=sqlite:///./virtual_assistant.db

# JWT Secret (임의의 긴 문자열)
JWT_SECRET_KEY=your-secret-key-here

# OAuth (사용하지 않으면 생략 가능)
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
KAKAO_CLIENT_ID=your-kakao-client-id
KAKAO_CLIENT_SECRET=your-kakao-client-secret
```

---

## 🎮 실행 방법

### 전체 앱 실행 (Electron + Backend)

```bash
npm start
```

이 명령어 하나로 백엔드와 프론트엔드가 모두 실행됩니다!

---

### 개발 모드 (백엔드/프론트엔드 따로 실행)

**터미널 1 - 백엔드**:
```bash
# 가상환경 활성화 (conda 또는 venv)
conda activate virtual-assistant
# 또는: source venv/bin/activate (Mac/Linux)
# 또는: venv\Scripts\activate (Windows)

python assistant.py
```

**터미널 2 - Electron**:
```bash
npm run start:electron
```

---

## 🎯 사용 방법

1. **로그인**: OAuth (Google/Kakao/Naver) 또는 게스트 로그인
2. **시작하기**: 캐릭터가 화면에 나타남
3. **조작 방법**:
   - `+/-` 키: 크기 조절
   - **드래그**: 위치 이동
   - `ESC` 키: 프로그램 종료
   - `F12` 키: 개발자 도구

---

## 🐛 문제 해결

### Windows에서 한글이 깨질 때

이미 `assistant.py`와 `main.js`에 UTF-8 설정이 적용되어 있습니다.
여전히 문제가 있다면 콘솔을 UTF-8로 설정하세요:

```cmd
chcp 65001
```

### 백엔드가 시작되지 않을 때

```bash
# Python 버전 확인
python --version

# 의존성 재설치
pip install -r backend/requirements.txt --force-reinstall

# 백엔드만 실행해서 에러 확인
python assistant.py
```

### 포트 8000이 이미 사용 중일 때

다른 프로그램이 8000 포트를 사용 중입니다.

**확인**:
```bash
# Mac/Linux
lsof -i :8000

# Windows
netstat -ano | findstr :8000
```

해당 프로세스를 종료하거나 `assistant.py`에서 포트를 변경하세요.

---

## 📦 프로젝트 구조

```
Virtual-Assistant/
├── backend/              # FastAPI 백엔드
│   ├── app/
│   ├── requirements.txt
│   └── alembic/         # DB 마이그레이션
├── frontend/            # 로그인/시작 화면
│   ├── Login/
│   └── Start/
├── public/              # Live2D 모델
├── index.html           # 메인 캐릭터 화면
├── main.js              # Electron 메인 프로세스
├── assistant.py         # 백엔드 실행 스크립트
└── package.json
```

---

## 🤝 기여

버그 리포트나 기능 제안은 Issue를 생성해주세요!

---

**업데이트**: 2025-11-14  
**버전**: 1.0.0

