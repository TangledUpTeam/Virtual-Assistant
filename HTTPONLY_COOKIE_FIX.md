# HttpOnly 쿠키 문제 해결

## 🔴 핵심 문제

**무한 루프의 진짜 원인**: `access_token`과 `refresh_token`이 **HttpOnly 쿠키**로 설정되어 있어서 **JavaScript에서 읽을 수 없었습니다!**

### HttpOnly 쿠키란?

- **HttpOnly=true**: JavaScript에서 `document.cookie`로 읽을 수 없음
- **보안 목적**: XSS 공격으로부터 토큰 보호
- **서버에서만 접근 가능**: HTTP 요청 시 자동으로 전송됨

### 문제 상황

```javascript
// 프론트엔드에서 시도
const accessToken = getCookie('access_token');  // ❌ null 반환!

// 왜냐하면 access_token은 HttpOnly 쿠키이기 때문
```

결과:
1. `/start` 페이지 로드
2. `isLoggedIn()` 체크 → `access_token` 읽기 시도
3. HttpOnly라서 읽을 수 없음 → `null` 반환
4. 로그인 안 된 것으로 판단 → `/login`으로 리다이렉트
5. 다시 로그인 → 다시 `/start`로 이동
6. **무한 루프** 🔄

## ✅ 해결 방법

### 방법 1: HttpOnly를 false로 변경 (❌ 권장하지 않음)
```python
response.set_cookie(
    key="access_token",
    httponly=False  # XSS 공격에 취약!
)
```

### 방법 2: 별도의 로그인 상태 플래그 쿠키 추가 (✅ 권장)

**백엔드**: `logged_in=true` 쿠키 추가 (HttpOnly=false)
```python
response.set_cookie(
    key="logged_in",
    value="true",
    httponly=False,  # JavaScript에서 읽을 수 있도록
    secure=not settings.DEBUG,
    samesite="lax",
    max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    path="/"
)
```

**프론트엔드**: `logged_in` 쿠키로 로그인 상태 확인
```javascript
function isLoggedIn() {
    const loggedIn = getCookie('logged_in');
    return loggedIn === 'true';
}
```

## 🔧 수정된 파일

### 1. 백엔드: `backend/app/api/v1/endpoints/auth.py`

**Google, Kakao, Naver OAuth 콜백 모두 수정**:

```python
# 기존 쿠키 (HttpOnly=true, JavaScript에서 읽을 수 없음)
response.set_cookie(key="access_token", httponly=True, ...)
response.set_cookie(key="refresh_token", httponly=True, ...)

# 새로 추가된 쿠키 (HttpOnly=false, JavaScript에서 읽을 수 있음)
response.set_cookie(key="logged_in", value="true", httponly=False, ...)
response.set_cookie(key="user", value=json.dumps(user_data), httponly=False, ...)
```

### 2. 프론트엔드: `frontend/Start/script.js`

**변경 전**:
```javascript
function isLoggedIn() {
    return !!getCookie('access_token');  // ❌ HttpOnly라서 읽을 수 없음
}
```

**변경 후**:
```javascript
function isLoggedIn() {
    const loggedIn = getCookie('logged_in');  // ✅ 읽을 수 있음
    return loggedIn === 'true';
}
```

### 3. 프론트엔드: `frontend/Login/script.js`

동일하게 `logged_in` 쿠키로 로그인 상태 확인하도록 수정

## 🍪 쿠키 구조

### HttpOnly 쿠키 (JavaScript에서 읽을 수 없음)
| 이름 | 용도 | HttpOnly | 만료 시간 |
|------|------|----------|-----------|
| `access_token` | API 인증 | ✅ true | 30분 |
| `refresh_token` | 토큰 갱신 | ✅ true | 7일 |

### 일반 쿠키 (JavaScript에서 읽을 수 있음)
| 이름 | 용도 | HttpOnly | 만료 시간 |
|------|------|----------|-----------|
| `logged_in` | 로그인 상태 플래그 | ❌ false | 30분 |
| `user` | 사용자 정보 (이름, 이메일) | ❌ false | 7일 |

## 🔒 보안 고려사항

### ✅ 안전한 설계
1. **토큰은 HttpOnly**: `access_token`, `refresh_token`은 여전히 HttpOnly로 보호
2. **플래그만 노출**: `logged_in`은 단순 boolean 값으로 민감한 정보 없음
3. **자동 전송**: HttpOnly 쿠키는 API 요청 시 자동으로 전송됨

### 🔐 API 인증 플로우
```
프론트엔드                     백엔드
    |                            |
    |  GET /api/v1/users/me      |
    |  Cookie: access_token=...  |  ← HttpOnly 쿠키 자동 전송
    |--------------------------->|
    |                            |  토큰 검증 (dependencies.py)
    |                            |  ✅ 유효함
    |  200 OK                    |
    |  {user: {...}}             |
    |<---------------------------|
```

프론트엔드는 `logged_in` 쿠키로 **UI 표시만** 결정하고, 실제 인증은 **HttpOnly 쿠키**로 처리!

## 📊 테스트 방법

1. 백엔드 재시작
2. 브라우저 콘솔 열기
3. 로그인 시도
4. 콘솔 로그 확인:

```
📄 Start 페이지 로드
🍪 전체 쿠키: logged_in=true; user={"email":"...","name":"..."}
✅ logged_in: true
👤 user: {"email":"...","name":"..."}
ℹ️  참고: access_token, refresh_token은 HttpOnly 쿠키라서 JavaScript에서 읽을 수 없습니다.
✅ 로그인 확인됨 (쿠키)
```

5. 개발자 도구 > Application > Cookies 확인:
   - ✅ `access_token` (HttpOnly ✓)
   - ✅ `refresh_token` (HttpOnly ✓)
   - ✅ `logged_in` (HttpOnly ✗)
   - ✅ `user` (HttpOnly ✗)

## 🎯 예상 결과

### 정상 플로우
1. 로그인 버튼 클릭
2. OAuth 인증 (계정 선택)
3. `/start`로 리다이렉트
4. **쿠키 확인**:
   - `logged_in=true` 읽기 성공 ✅
   - 로그인 상태 확인 ✅
5. 사용자 정보 표시
6. **무한 루프 없음** ✅

### API 요청 시
```javascript
// 프론트엔드에서 API 호출
fetch('/api/v1/users/me', {
    credentials: 'include'  // 쿠키 자동 전송
})
```

백엔드는 HttpOnly 쿠키에서 `access_token`을 읽어 인증 처리!

## 📝 정리

| 항목 | 이전 | 이후 |
|------|------|------|
| 로그인 상태 확인 | `access_token` (HttpOnly) | `logged_in` (일반 쿠키) |
| JavaScript 접근 | ❌ 불가능 | ✅ 가능 |
| 보안 | 🔒 안전하지만 사용 불가 | 🔒 안전하고 사용 가능 |
| 무한 루프 | ❌ 발생 | ✅ 해결 |

## 🚀 다음 단계

- [ ] 로그인 테스트
- [ ] 쿠키 확인 (개발자 도구)
- [ ] API 요청 테스트
- [ ] 로그아웃 테스트
- [ ] 토큰 만료 시 동작 확인

