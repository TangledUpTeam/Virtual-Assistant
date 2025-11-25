# 쿠키 기반 인증으로 변경 완료

## 변경 사항

### 문제점
- 기존에는 OAuth 로그인 후 토큰을 URL 쿼리 파라미터로 전달하고 sessionStorage에 저장
- 쿠키를 전혀 사용하지 않아 브라우저 개발자 도구에서 쿠키가 보이지 않음
- URL에 토큰이 노출되어 보안상 취약

### 해결 방법
OAuth 로그인 후 토큰을 **HttpOnly 쿠키**에 저장하도록 변경

## 수정된 파일

### 1. 백엔드

#### `backend/app/api/v1/endpoints/auth.py`
- **변경 내용**: OAuth 콜백에서 토큰을 쿠키에 저장
- **주요 변경점**:
  - `access_token`: HttpOnly, Secure (개발 환경에서는 Secure=False), SameSite=Lax
  - `refresh_token`: HttpOnly, Secure, SameSite=Lax
  - `user`: 일반 쿠키 (JavaScript에서 읽을 수 있도록 HttpOnly=False)
  - URL 쿼리 파라미터 대신 쿠키 사용

```python
# 쿠키에 토큰 저장
response = RedirectResponse(url="/start", status_code=302)

response.set_cookie(
    key="access_token",
    value=result.access_token,
    httponly=True,
    secure=not settings.DEBUG,
    samesite="lax",
    max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
)
```

#### `backend/app/domain/auth/dependencies.py`
- **변경 내용**: 토큰을 Authorization 헤더 또는 쿠키에서 읽도록 수정
- **주요 변경점**:
  - `HTTPBearer(auto_error=False)`: 토큰이 없어도 에러를 발생시키지 않음
  - `Cookie(None)`: 쿠키에서 access_token 읽기
  - 우선순위: Authorization 헤더 > 쿠키

```python
def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    access_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
) -> User:
    # Authorization 헤더 우선, 없으면 쿠키
    token = None
    if credentials:
        token = credentials.credentials
    elif access_token:
        token = access_token
```

### 2. 프론트엔드

#### `frontend/Start/script.js`
- **변경 내용**: sessionStorage 대신 쿠키 사용
- **주요 변경점**:
  - `getCookie()`: 쿠키에서 값 읽기
  - `deleteCookie()`: 쿠키 삭제
  - `isLoggedIn()`: 쿠키에서 access_token 확인
  - `getUserInfo()`: 쿠키에서 사용자 정보 읽기
  - OAuth 콜백 처리 로직 제거 (백엔드에서 쿠키 설정)

#### `frontend/Login/script.js`
- **변경 내용**: sessionStorage 대신 쿠키 사용
- **주요 변경점**:
  - `getCookie()`, `deleteCookie()` 함수 추가
  - `isLoggedIn()`, `logout()` 함수 쿠키 사용하도록 수정

## 쿠키 설정 상세

### Access Token 쿠키
- **이름**: `access_token`
- **HttpOnly**: `true` (JavaScript에서 접근 불가, XSS 방지)
- **Secure**: `true` (HTTPS에서만 전송, 개발 환경에서는 false)
- **SameSite**: `lax` (CSRF 방지)
- **Max-Age**: 30분 (설정값에 따라 변경 가능)

### Refresh Token 쿠키
- **이름**: `refresh_token`
- **HttpOnly**: `true`
- **Secure**: `true` (개발 환경에서는 false)
- **SameSite**: `lax`
- **Max-Age**: 7일 (설정값에 따라 변경 가능)

### User 정보 쿠키
- **이름**: `user`
- **HttpOnly**: `false` (JavaScript에서 읽을 수 있도록)
- **Secure**: `true` (개발 환경에서는 false)
- **SameSite**: `lax`
- **Max-Age**: 7일
- **내용**: `{"email": "user@example.com", "name": "사용자"}`

## 보안 개선 사항

1. **URL에 토큰 노출 방지**: 쿼리 파라미터 대신 쿠키 사용
2. **XSS 방지**: HttpOnly 쿠키로 JavaScript에서 토큰 접근 불가
3. **CSRF 방지**: SameSite=Lax 설정
4. **HTTPS 강제**: 프로덕션 환경에서 Secure=true

## 테스트 방법

1. 백엔드 실행:
```bash
cd backend
uvicorn app.main:app --reload
```

2. 프론트엔드 접속:
```
http://localhost:8000/login
```

3. OAuth 로그인 (Google/Kakao/Naver)

4. 브라우저 개발자 도구 > Application > Cookies 확인:
   - `access_token` (HttpOnly)
   - `refresh_token` (HttpOnly)
   - `user` (일반 쿠키)

5. `/start` 페이지에서 사용자 정보 표시 확인

## 주의사항

- **개발 환경**: `DEBUG=True`일 때 `Secure=False`로 설정되어 HTTP에서도 쿠키 전송
- **프로덕션 환경**: `DEBUG=False`로 설정하고 HTTPS 사용 필수
- **CORS 설정**: `allow_credentials=True` 설정 필요 (이미 설정됨)

## 다음 단계

- [ ] API 요청 시 쿠키 자동 전송 확인
- [ ] Refresh Token으로 Access Token 갱신 기능 테스트
- [ ] 로그아웃 시 쿠키 삭제 확인
- [ ] HTTPS 환경에서 Secure 쿠키 동작 확인

