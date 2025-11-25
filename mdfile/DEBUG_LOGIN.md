# 🔍 로그인 디버깅 가이드

## 문제: "허용 누르면 쿠키 사라지고 로그인으로 롤백"

### 가능한 원인

1. **OAuth 콜백 중 에러 발생** (가장 가능성 높음)
2. 데이터베이스 연결 실패
3. 사용자 생성/조회 실패
4. JWT 토큰 생성 실패
5. 쿠키 설정 실패

## 🧪 디버깅 방법

### 1단계: 백엔드 콘솔 확인

백엔드를 실행하고 로그인을 시도한 후 **콘솔 로그를 주의깊게 확인**하세요.

#### 정상적인 경우:
```
============================================================
🔵 Google OAuth 콜백 시작
============================================================
   Authorization Code 받음: 4/0AeanS0...
   1️⃣ Google에 Access Token 요청 중...
   ✅ Access Token 받음
   2️⃣ Google에 사용자 정보 요청 중...
   ✅ 사용자 정보 받음: user@example.com
   3️⃣ 데이터베이스에서 사용자 조회/생성 중...
   ✅ 사용자 처리 완료: user@example.com

============================================================
🍪 Google OAuth 콜백 - 쿠키 설정 시작
============================================================
   - DEBUG 모드: True
   - Secure 설정: False
   - 사용자: user@example.com
   - Access Token 길이: 205
   - Refresh Token 길이: 205
   ✅ access_token 쿠키 설정 완료
   ✅ refresh_token 쿠키 설정 완료
   ✅ user 쿠키 설정 완료
   ✅ logged_in 쿠키 설정 완료

🔄 /start로 리다이렉트
============================================================
```

#### 에러가 발생한 경우:
```
============================================================
🔵 Google OAuth 콜백 시작
============================================================
   Authorization Code 받음: 4/0AeanS0...
   1️⃣ Google에 Access Token 요청 중...

❌ Google OAuth 콜백 에러 발생!
============================================================
에러 타입: HTTPStatusError
에러 메시지: Client error '400 Bad Request' for url ...
상세 스택:
  File "...", line ..., in google_callback
    token_data = await google_oauth.get_access_token(code)
  ...
============================================================
```

### 2단계: 에러 메시지 분석

#### A. "HTTPStatusError: 400 Bad Request"
**원인**: Google OAuth 설정 문제
- Redirect URI 불일치
- Client ID/Secret 오류
- Authorization Code 재사용

**해결**:
1. Google Cloud Console에서 Redirect URI 확인
2. `.env` 파일의 `GOOGLE_REDIRECT_URI` 확인
3. 브라우저 쿠키 전체 삭제 후 재시도

#### B. "OperationalError: no such table: users"
**원인**: 데이터베이스 테이블 미생성

**해결**:
```bash
cd backend
# 데이터베이스 초기화
rm -f *.db  # 기존 DB 삭제 (개발용)
python -c "from app.infrastructure.database import Base, engine; Base.metadata.create_all(bind=engine)"
```

#### C. "KeyError: 'access_token'"
**원인**: Google OAuth 응답 형식 오류

**해결**: Google OAuth 클라이언트 코드 확인

#### D. "AttributeError: 'NoneType' object has no attribute 'email'"
**원인**: 사용자 정보 파싱 실패

**해결**: Google OAuth 스코프 확인 (email, profile 포함 필요)

### 3단계: .env 파일 확인

```bash
# backend/.env 또는 Virtual-Assistant/.env
DATABASE_URL=sqlite:///./virtual_assistant.db
SECRET_KEY=your-secret-key-here
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret
GOOGLE_REDIRECT_URI=http://localhost:8000/api/v1/auth/google/callback
```

**중요**: `GOOGLE_REDIRECT_URI`가 Google Cloud Console의 설정과 **정확히 일치**해야 합니다!

### 4단계: Google Cloud Console 확인

1. https://console.cloud.google.com/ 접속
2. 프로젝트 선택
3. "API 및 서비스" > "사용자 인증 정보"
4. OAuth 2.0 클라이언트 ID 클릭
5. **승인된 리디렉션 URI** 확인:
   ```
   http://localhost:8000/api/v1/auth/google/callback
   ```

### 5단계: 데이터베이스 확인

```bash
cd backend
sqlite3 virtual_assistant.db

# 테이블 목록 확인
.tables

# users 테이블 확인
SELECT * FROM users;

# 종료
.quit
```

## 🔧 일반적인 해결 방법

### 방법 1: 전체 초기화
```bash
# 1. 백엔드 중지 (Ctrl+C)

# 2. 데이터베이스 삭제
cd backend
rm -f *.db

# 3. 브라우저 쿠키 전체 삭제
# Chrome: Ctrl+Shift+Delete > "전체 기간" > "쿠키 및 기타 사이트 데이터"

# 4. 백엔드 재시작
uvicorn app.main:app --reload

# 5. 로그인 재시도
```

### 방법 2: Redirect URI 재확인
```bash
# .env 파일 확인
cat .env | grep GOOGLE_REDIRECT_URI

# 출력 예시:
# GOOGLE_REDIRECT_URI=http://localhost:8000/api/v1/auth/google/callback
```

Google Cloud Console의 설정과 **완전히 동일**해야 합니다!

### 방법 3: 시크릿 모드 테스트
1. 브라우저 시크릿 모드 열기 (Ctrl+Shift+N)
2. `http://localhost:8000/login` 접속
3. 로그인 시도
4. 백엔드 콘솔 로그 확인

## 📊 체크리스트

로그인 시도 전 확인:

- [ ] 백엔드가 실행 중인가? (`http://localhost:8000/health` 접속 확인)
- [ ] `.env` 파일이 존재하는가?
- [ ] `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` 설정되어 있는가?
- [ ] `GOOGLE_REDIRECT_URI`가 올바른가?
- [ ] Google Cloud Console에서 Redirect URI가 일치하는가?
- [ ] 데이터베이스 파일이 존재하는가? (`virtual_assistant.db`)
- [ ] 브라우저 쿠키를 삭제했는가?

## 🆘 그래도 안 되면?

백엔드 콘솔의 **전체 로그**를 복사해서 공유해주세요. 특히:
- `🔵 Google OAuth 콜백 시작` 이후의 모든 로그
- `❌` 로 시작하는 에러 메시지
- 스택 트레이스 (Traceback)

## 🎯 예상 결과

정상적으로 작동하면:
1. "허용" 버튼 클릭
2. 백엔드 콘솔에 성공 로그 출력
3. `/start` 페이지로 이동
4. 사용자 이름 표시
5. 개발자 도구에서 쿠키 확인 가능

**무한 루프 없음!** ✅

