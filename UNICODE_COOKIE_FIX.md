# 🔧 한글 이름 쿠키 에러 해결

## 🔴 에러 발견!

```
UnicodeEncodeError: 'latin-1' codec can't encode characters in position 59-61: ordinal not in range(256)
```

### 원인
**사용자 이름에 한글이 포함**되어 있을 때 쿠키 설정 실패!

HTTP 쿠키는 `latin-1` (ASCII 확장) 인코딩만 지원하는데, 한글은 이 범위를 벗어납니다.

### 발생 위치
```python
user_data = {
    "email": "yunaya0078@gmail.com",
    "name": "홍길동"  # ← 한글!
}
response.set_cookie(
    key="user",
    value=json.dumps(user_data, ensure_ascii=False),  # ← 에러 발생!
    ...
)
```

## ✅ 해결 방법: URL 인코딩

### 백엔드 수정

**파일**: `backend/app/api/v1/endpoints/auth.py`

**변경 전**:
```python
import json
user_data = {
    "email": result.user.email,
    "name": result.user.name or ""
}
response.set_cookie(
    key="user",
    value=json.dumps(user_data, ensure_ascii=False),  # ❌ 한글 에러
    ...
)
```

**변경 후**:
```python
import json
from urllib.parse import quote

user_data = {
    "email": result.user.email,
    "name": result.user.name or ""
}
# 한글 등 유니코드 문자를 위해 URL 인코딩
user_json = json.dumps(user_data, ensure_ascii=False)
user_encoded = quote(user_json)  # ✅ URL 인코딩

response.set_cookie(
    key="user",
    value=user_encoded,  # ✅ 인코딩된 값 사용
    ...
)
```

### 프론트엔드 수정

**파일**: `frontend/Start/script.js`

**변경 전**:
```javascript
function getUserInfo() {
    const userJson = getCookie('user');
    if (userJson) {
        try {
            return JSON.parse(userJson);  // ❌ 인코딩된 값 파싱 실패
        } catch (e) {
            console.error('사용자 정보 파싱 실패:', e);
            return null;
        }
    }
    return null;
}
```

**변경 후**:
```javascript
function getUserInfo() {
    const userEncoded = getCookie('user');
    if (userEncoded) {
        try {
            // URL 디코딩 후 JSON 파싱
            const userJson = decodeURIComponent(userEncoded);  // ✅ 디코딩
            return JSON.parse(userJson);
        } catch (e) {
            console.error('사용자 정보 파싱 실패:', e);
            return null;
        }
    }
    return null;
}
```

## 🔄 인코딩 과정

### 백엔드 (Python)
```python
user_data = {"email": "test@example.com", "name": "홍길동"}
json_str = json.dumps(user_data, ensure_ascii=False)
# → '{"email":"test@example.com","name":"홍길동"}'

encoded = quote(json_str)
# → '%7B%22email%22%3A%22test%40example.com%22%2C%22name%22%3A%22%ED%99%8D%EA%B8%B8%EB%8F%99%22%7D'
```

### 프론트엔드 (JavaScript)
```javascript
const encoded = getCookie('user');
// → '%7B%22email%22%3A%22test%40example.com%22%2C%22name%22%3A%22%ED%99%8D%EA%B8%B8%EB%8F%99%22%7D'

const decoded = decodeURIComponent(encoded);
// → '{"email":"test@example.com","name":"홍길동"}'

const user = JSON.parse(decoded);
// → {email: "test@example.com", name: "홍길동"}
```

## 📊 수정된 파일

### 1. `backend/app/api/v1/endpoints/auth.py`
- Google OAuth 콜백
- Kakao OAuth 콜백
- Naver OAuth 콜백

모두 `urllib.parse.quote()` 사용하여 URL 인코딩

### 2. `frontend/Start/script.js`
- `getUserInfo()` 함수에 `decodeURIComponent()` 추가

## 🧪 테스트

### 1. 백엔드 재시작
```bash
cd backend
uvicorn app.main:app --reload
```

### 2. 로그인 시도
1. `http://localhost:8000/login` 접속
2. Google/Kakao/Naver 로그인
3. 권한 승인

### 3. 백엔드 콘솔 확인
```
🍪 Google OAuth 콜백 - 쿠키 설정 시작
   - 사용자: yunaya0078@gmail.com
   ✅ access_token 쿠키 설정 완료
   ✅ refresh_token 쿠키 설정 완료
   ✅ user 쿠키 설정 완료 (URL 인코딩)  ← 새로 추가된 메시지
   ✅ logged_in 쿠키 설정 완료
🔄 /start로 리다이렉트
```

### 4. 브라우저 개발자 도구 > Application > Cookies
```
user: %7B%22email%22%3A%22yunaya0078%40gmail.com%22%2C%22name%22%3A%22%ED%99%8D%EA%B8%B8%EB%8F%99%22%7D
```

### 5. 프론트엔드 콘솔 확인
```
📄 Start 페이지 로드
✅ logged_in: true
👤 사용자 정보: {email: "yunaya0078@gmail.com", name: "홍길동"}
✅ 로그인 확인됨 (쿠키)
```

## 🎯 예상 결과

### ✅ 성공 플로우
1. 로그인 버튼 클릭
2. OAuth 인증 (계정 선택)
3. **한글 이름 포함된 쿠키 설정 성공** ✅
4. `/start`로 리다이렉트
5. **한글 이름 정상 표시** ✅
6. **무한 루프 없음!** ✅

### 🌏 지원 언어
- ✅ 한글 (홍길동, 김철수 등)
- ✅ 일본어 (田中太郎 등)
- ✅ 중국어 (王小明 등)
- ✅ 이모지 (😀, 🎉 등)
- ✅ 모든 유니코드 문자

## 🔒 보안 고려사항

### URL 인코딩의 장점
1. **안전한 전송**: 특수 문자를 안전하게 인코딩
2. **표준 준수**: HTTP 쿠키 표준 (RFC 6265) 준수
3. **호환성**: 모든 브라우저에서 동작

### 여전히 안전한 이유
- `access_token`, `refresh_token`은 여전히 HttpOnly
- URL 인코딩은 단순 변환일 뿐 암호화 아님
- 민감한 정보는 여전히 보호됨

## 📝 정리

| 항목 | 이전 | 수정 후 |
|------|------|---------|
| 한글 이름 | ❌ 에러 발생 | ✅ 정상 작동 |
| 쿠키 설정 | ❌ 실패 | ✅ 성공 |
| 무한 루프 | ❌ 발생 | ✅ 해결 |

**이제 한글 이름을 가진 사용자도 정상적으로 로그인할 수 있습니다!** 🎉

