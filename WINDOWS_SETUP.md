# Windows 환경 설정 가이드

## 🪟 Windows에서 Virtual Desk Assistant 실행하기

### 1. 필수 소프트웨어 설치

#### Node.js 18 이상
- [Node.js 공식 사이트](https://nodejs.org/)에서 LTS 버전 다운로드
- 설치 후 확인:
```bash
node -v
npm -v
```

#### Python 3.10
- [Python 공식 사이트](https://www.python.org/downloads/)에서 3.10 버전 다운로드
- **중요**: 설치 시 "Add Python to PATH" 체크!
- 설치 후 확인:
```bash
python --version
```

#### PostgreSQL
- [PostgreSQL 공식 사이트](https://www.postgresql.org/download/windows/)에서 다운로드
- 설치 후 데이터베이스 생성:
```sql
CREATE DATABASE "virtual-assistant";
```

---

### 2. 프로젝트 클론 및 설정

```bash
# 프로젝트 클론
git clone <repository-url>
cd Virtual-Assistant

# Node 의존성 설치
npm install
```

---

### 3. Python 가상환경 설정

```bash
# 백엔드 폴더로 이동
cd backend

# 가상환경 생성
python -m venv venv

# 가상환경 활성화 (PowerShell)
.\venv\Scripts\Activate.ps1

# 가상환경 활성화 (CMD)
.\venv\Scripts\activate.bat

# 의존성 설치
pip install -r requirements.txt
```

**PowerShell 실행 정책 오류 시:**
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

---

### 4. 환경 변수 설정

루트 폴더에 `.env` 파일 생성:
```env
# OpenAI API Key
OPENAI_API_KEY=your_openai_api_key_here

# Database
DATABASE_URL=postgresql://postgres:password@localhost:5432/virtual-assistant

# Naver OAuth (선택)
NAVER_CLIENT_ID=your_naver_client_id
NAVER_CLIENT_SECRET=your_naver_client_secret
NAVER_REDIRECT_URI=http://localhost:8000/auth/naver/callback
```

---

### 5. 앱 실행

```bash
# 루트 폴더에서
npm start
```

---

## 🐛 문제 해결

### 문제 1: "python을 찾을 수 없습니다"
**해결:**
- Python 설치 시 "Add to PATH" 체크했는지 확인
- 또는 수동으로 PATH 추가:
  1. 시스템 환경 변수 편집
  2. Path에 `C:\Users\<사용자명>\AppData\Local\Programs\Python\Python310` 추가

### 문제 2: "node-gyp 오류"
**해결:**
```bash
npm install --global windows-build-tools
```

### 문제 3: "Electron이 시작되지 않음"
**해결:**
```bash
npm install electron --save-dev
npx electron-rebuild
```

### 문제 4: 캐릭터 무빙/토글이 안 됨
**확인 사항:**
1. F12를 눌러 개발자 도구 열기
2. Console 탭에서 오류 확인
3. 터미널에서 백엔드 오류 확인

**단축키 확인:**
- 채팅 토글: `Ctrl + Enter` (Windows), `Cmd + Enter` (Mac)
- 브레인스토밍 토글: `Ctrl + Shift + B` (Windows), `Cmd + Shift + B` (Mac)
- 캐릭터 크기 조절: `+` / `-` 키
- 앱 종료: `ESC` 키

### 문제 5: PostgreSQL 연결 오류
**해결:**
1. PostgreSQL 서비스가 실행 중인지 확인:
   - `서비스(services.msc)` → `postgresql-x64-16` 실행 확인
2. 데이터베이스 생성 확인:
```sql
psql -U postgres
CREATE DATABASE "virtual-assistant";
\q
```

---

## 📝 디버깅 정보 수집

문제가 지속되면 다음 정보를 공유해주세요:

### 1. 환경 정보
```bash
node -v
npm -v
python --version
```

### 2. 터미널 오류 로그
```bash
npm start
# 오류 메시지 전체 복사
```

### 3. 브라우저 콘솔 오류
- 앱 실행 후 `F12` 키
- Console 탭의 빨간색 오류 메시지 복사

---

## 🔧 브레인스토밍 모듈 초기 설정 (필수!)

Git에서 ChromaDB 데이터가 제외되어 있으므로, **처음 실행 시 반드시** 다음을 실행해야 합니다:

```bash
# 1. 가상환경 활성화
cd backend
.\venv\Scripts\Activate.ps1

# 2. 브레인스토밍 ChromaDB 생성
cd app/domain/brainstorming
python chroma_loader.py

# 3. 성공 메시지 확인
# ✅ ChromaDB 데이터 로드 완료!
# 📊 총 <N>개 청크가 저장되었습니다.
```

**이 과정을 건너뛰면:**
```
⚠️ 영구 RAG 컬렉션 로드 실패: Collection brainstorming_techniques does not exist.
```
이런 경고가 나타나며, 브레인스토밍 기능이 작동하지 않습니다!

---

## 🎯 정상 작동 확인

### 백엔드 (FastAPI)
```bash
python assistant.py

# 정상 출력:
# ✅ SessionManager 초기화 완료
# ✅ Database tables created
# 🚀 Starting Virtual Desk Assistant API...
```

### 프론트엔드 (Electron)
```bash
npm start

# 정상 동작:
# 1. ✅ 캐릭터가 화면에 나타남
# 2. ✅ 캐릭터를 마우스로 드래그 가능
# 3. ✅ `Ctrl + Enter`로 채팅창 토글
# 4. ✅ `Ctrl + Shift + B`로 브레인스토밍 패널 토글
# 5. ✅ `+` / `-` 키로 캐릭터 크기 조절
```

---

문제가 해결되지 않으면 위 디버깅 정보를 함께 이슈를 등록해주세요!

