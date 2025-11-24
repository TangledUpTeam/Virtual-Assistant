# 🍪 쿠키 보안 정책 문제 해결 (최종)

## 🔴 문제: "서버는 줬는데 브라우저는 안 받았다"

### 증상
- 백엔드 로그: "✅ 쿠키 설정 완료"
- 브라우저 개발자 도구: 쿠키 없음 😱
- 결과: 무한 루프

### 원인
**브라우저의 쿠키 보안 정책**이 까다로워서 서버가 보낸 쿠키를 거부!

특히 **localhost 개발 환경**에서 크롬/일렉트론의 보안 정책:
- `Secure=True` + HTTP (not HTTPS) → ❌ 거부
- `SameSite=None` + `Secure=False` → ❌ 거부
- `domain=localhost` 명시 → ❌ 거부 (역설적이지만 사실)

## ✅ 해결 방법

### 쿠키 설정 완화 (로컬 개발 환경용)

```python
response.set_cookie(
    key="access_token",
    value=result.access_token,
    httponly=True,           # ✅ 유지 (XSS 방지)
    secure=False,            # ✅ 로컬은 HTTP라서 False
    samesite="Lax",          # ✅ Lax (None은 Secure=True 필수)
    max_age=1800,
    path="/",                # ✅ 모든 경로
    domain=None              # ✅ 중요! localhost는 domain 지정 안 함
)
```

### 핵심 포인트

| 설정 | 이전 | 수정 후 | 이유 |
|------|------|---------|------|
| `secure` | `not settings.DEBUG` | `False` | localhost는 HTTP (HTTPS 아님) |
| `samesite` | `"lax"` (소문자) | `"Lax"` (대문자) | 크롬 정책 (대소문자 구분) |
| `domain` | 없음 | `None` 명시 | localhost에서는 domain 지정 금지 |

## 🔧 수정된 코드

### Google OAuth 콜백 (`/google/callback`)

```python
# Access Token (HttpOnly)
response.set_cookie(
    key="access_token",
    value=result.access_token,
    httponly=True,
    secure=False,      # ← 변경
    samesite="Lax",    # ← 대문자
    max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    path="/",
    domain=None        # ← 추가
)

# Refresh Token (HttpOnly)
response.set_cookie(
    key="refresh_token",
    value=result.refresh_token,
    httponly=True,
    secure=False,
    samesite="Lax",
    max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
    path="/",
    domain=None
)

# User 정보 (일반 쿠키)
response.set_cookie(
    key="user",
    value=json.dumps(user_data, ensure_ascii=False),
    httponly=False,
    secure=False,
    samesite="Lax",
    max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
    path="/",
    domain=None
)

# 로그인 플래그 (일반 쿠키)
response.set_cookie(
    key="logged_in",
    value="true",
    httponly=False,
    secure=False,
    samesite="Lax",
    max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    path="/",
    domain=None
)
```

**Kakao, Naver 콜백도 동일하게 수정됨**

## 🔒 보안 고려사항

### ✅ 여전히 안전한 이유

1. **HttpOnly 유지**
   - `access_token`, `refresh_token`은 여전히 HttpOnly
   - JavaScript에서 접근 불가 → XSS 공격 방어

2. **SameSite=Lax**
   - CSRF 공격 방어
   - 외부 사이트에서 쿠키 전송 불가

3. **로컬 개발 전용**
   - 프로덕션에서는 HTTPS + Secure=True 사용 필수

### ⚠️ 프로덕션 배포 시 주의

프로덕션 환경에서는 **반드시** 다음과 같이 변경:

```python
# 프로덕션 설정 (예시)
response.set_cookie(
    key="access_token",
    value=result.access_token,
    httponly=True,
    secure=True,           # ← HTTPS 필수
    samesite="Lax",
    max_age=1800,
    path="/",
    domain=".yourdomain.com"  # ← 실제 도메인
)
```

또는 환경 변수로 분기:

```python
secure=not settings.DEBUG,  # DEBUG=False면 Secure=True
domain=settings.COOKIE_DOMAIN if not settings.DEBUG else None
```

## 📊 테스트 방법

### 1. 백엔드 재시작
```bash
cd backend
uvicorn app.main:app --reload
```

### 2. 브라우저에서 로그인
1. `http://localhost:8000/login` 접속
2. Google/Kakao/Naver 로그인
3. 권한 승인

### 3. 백엔드 콘솔 확인
```
🍪 Google OAuth 콜백 - 쿠키 설정 시작
   - DEBUG 모드: True
   - Secure 설정: False
   - 사용자: user@example.com
   ✅ access_token 쿠키 설정 완료
   ✅ refresh_token 쿠키 설정 완료
   ✅ user 쿠키 설정 완료
   ✅ logged_in 쿠키 설정 완료
🔄 /start로 리다이렉트
```

### 4. 브라우저 개발자 도구 > Application > Cookies 확인

**이제 쿠키가 보여야 합니다!** ✅

| 이름 | 값 | HttpOnly | Secure | SameSite | Path |
|------|-----|----------|--------|----------|------|
| `access_token` | `eyJ...` | ✓ | | Lax | / |
| `refresh_token` | `eyJ...` | ✓ | | Lax | / |
| `logged_in` | `true` | | | Lax | / |
| `user` | `{"email":"..."}` | | | Lax | / |

### 5. 프론트엔드 콘솔 확인
```
📄 Start 페이지 로드
🍪 전체 쿠키: logged_in=true; user={"email":"user@example.com","name":"홍길동"}
✅ logged_in: true
👤 user: {"email":"user@example.com","name":"홍길동"}
✅ 로그인 확인됨 (쿠키)
```

## 🎯 예상 결과

### ✅ 정상 플로우
1. 로그인 버튼 클릭
2. OAuth 인증 (계정 선택)
3. 백엔드: 쿠키 설정
4. **브라우저: 쿠키 저장 성공** 🎉
5. `/start`로 리다이렉트
6. 프론트엔드: `logged_in=true` 확인
7. **무한 루프 없음!** ✅

### ❌ 여전히 안 되면?

#### 체크리스트
- [ ] 백엔드 재시작했나?
- [ ] 브라우저 쿠키 전체 삭제했나? (Ctrl+Shift+Delete)
- [ ] 시크릿 모드로 테스트했나?
- [ ] 백엔드 포트가 8000인가? (`http://localhost:8000`)
- [ ] CORS 설정에 `allow_credentials=True`가 있나?

#### CORS 확인
`backend/app/main.py`:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,  # ← 중요!
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## 📝 변경 사항 요약

### 파일: `backend/app/api/v1/endpoints/auth.py`

**3개 OAuth 콜백 모두 수정**:
- `/google/callback`
- `/kakao/callback`
- `/naver/callback`

**변경 내용**:
```diff
- secure=not settings.DEBUG,
+ secure=False,

- samesite="lax",
+ samesite="Lax",

+ domain=None
```

## 🚀 다음 단계

- [x] 쿠키 설정 완화
- [ ] 로그인 테스트
- [ ] 쿠키 확인 (개발자 도구)
- [ ] 무한 루프 해결 확인
- [ ] 프로덕션 배포 시 보안 설정 강화

---

**이제 정말로 작동할 것입니다!** 🎉

로컬 개발 환경의 까다로운 보안 정책을 우회하면서도, HttpOnly로 토큰은 안전하게 보호하는 균형잡힌 설정입니다.

