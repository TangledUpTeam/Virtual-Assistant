# 🍪 fetch에 credentials: 'include' 추가

## 🔴 문제: "사용자 인증 실패 (게스트 모드)"

### 증상
백엔드 로그:
```
ℹ️  사용자 인증 실패 (게스트 모드): HTTPException
✅ 세션 생성 - 게스트 사용자
```

로그인했는데도 게스트로 인식됨!

### 원인
**fetch 요청에 `credentials: 'include'`가 없어서 쿠키가 전송되지 않음!**

기본적으로 fetch는 **같은 도메인이어도 쿠키를 자동으로 보내지 않습니다.**

## ✅ 해결 방법

### 파일: `renderer/chat/chatbotService.js`

모든 fetch 요청에 `credentials: 'include'` 추가

#### 1. 세션 생성
```javascript
// 변경 전
const response = await fetch(`${API_BASE_URL}/chatbot/session`, {
  method: 'POST',
  headers: headers
});

// 변경 후
const response = await fetch(`${API_BASE_URL}/chatbot/session`, {
  method: 'POST',
  headers: headers,
  credentials: 'include'  // ← 추가!
});
```

#### 2. 메시지 전송
```javascript
// 변경 전
const response = await fetch(`${API_BASE_URL}/chatbot/message`, {
  method: 'POST',
  headers: headers,
  body: JSON.stringify({ ... })
});

// 변경 후
const response = await fetch(`${API_BASE_URL}/chatbot/message`, {
  method: 'POST',
  headers: headers,
  credentials: 'include',  // ← 추가!
  body: JSON.stringify({ ... })
});
```

#### 3. 히스토리 조회
```javascript
// 변경 전
const response = await fetch(`${API_BASE_URL}/chatbot/history/${sessionId}`, {
  method: 'GET',
  headers: { ... }
});

// 변경 후
const response = await fetch(`${API_BASE_URL}/chatbot/history/${sessionId}`, {
  method: 'GET',
  headers: { ... },
  credentials: 'include'  // ← 추가!
});
```

#### 4. 세션 삭제
```javascript
// 변경 전
await fetch(`${API_BASE_URL}/chatbot/session/${sessionId}`, {
  method: 'DELETE'
});

// 변경 후
await fetch(`${API_BASE_URL}/chatbot/session/${sessionId}`, {
  method: 'DELETE',
  credentials: 'include'  // ← 추가!
});
```

## 📊 credentials 옵션 설명

### `credentials: 'include'`
- **모든 요청에 쿠키 포함** (cross-origin 포함)
- 로그인 상태 유지에 필수
- CORS 설정 필요: `allow_credentials=True`

### `credentials: 'same-origin'` (기본값)
- **같은 도메인에만** 쿠키 포함
- 하지만 fetch는 기본적으로 쿠키를 보내지 않음!

### `credentials: 'omit'`
- 쿠키 전송 안 함

## 🔄 요청 플로우

### 변경 전 (쿠키 없음)
```
프론트엔드
  ↓ fetch (쿠키 없음)
백엔드
  ↓ get_current_user_optional
  ↓ 쿠키 없음 → None 반환
엔드포인트
  ↓ 게스트 모드
```

### 변경 후 (쿠키 포함)
```
프론트엔드
  ↓ fetch + credentials: 'include'
  ↓ Cookie: access_token=eyJ...; logged_in=true
백엔드
  ↓ get_current_user_optional
  ↓ 쿠키에서 토큰 추출 → User 객체 반환
엔드포인트
  ↓ 로그인 사용자 모드
  ↓ user_id, email 등 사용 가능
```

## 🧪 테스트

### 1. 프론트엔드 새로고침
브라우저에서 `F5` 또는 Electron 재시작

### 2. 로그인 확인
브라우저 개발자 도구 > Application > Cookies:
```
access_token: eyJ...
logged_in: true
user: {"email":"...","name":"..."}
```

### 3. 채팅 시도
메시지를 보내면 백엔드 콘솔에:

```
✅ 세션 생성 - 로그인 사용자: yunaya0078@gmail.com (ID: 3)
💬 메시지 전송 - 로그인 사용자: yunaya0078@gmail.com (ID: 3)
```

**"게스트 모드" 메시지가 사라집니다!** ✅

### 4. 네트워크 탭 확인
개발자 도구 > Network > chatbot/session:

**Request Headers**:
```
Cookie: access_token=eyJ...; logged_in=true; user=...
```

쿠키가 전송되는 것을 확인할 수 있습니다!

## 🎯 수정된 엔드포인트

| 엔드포인트 | 메서드 | credentials 추가 |
|-----------|--------|-----------------|
| `/chatbot/session` | POST | ✅ |
| `/chatbot/message` | POST | ✅ |
| `/chatbot/message` (재시도) | POST | ✅ |
| `/chatbot/history/:id` | GET | ✅ |
| `/chatbot/session/:id` | DELETE | ✅ |

**총 5개 위치에 `credentials: 'include'` 추가 완료!**

## 💡 왜 필요한가?

### 브라우저 보안 정책
- **Same-Origin Policy**: 같은 도메인이어도 명시적으로 지정해야 쿠키 전송
- **CORS**: Cross-Origin 요청 시 더욱 엄격
- **Privacy**: 사용자 프라이버시 보호를 위한 기본 동작

### FastAPI + 쿠키 인증
```python
# 백엔드에서 쿠키 읽기
access_token: Optional[str] = Cookie(None)
```

프론트엔드에서 `credentials: 'include'` 없으면:
- 쿠키가 전송되지 않음
- `access_token = None`
- 인증 실패

## 📝 정리

| 항목 | 변경 전 | 변경 후 |
|------|---------|---------|
| 쿠키 전송 | ❌ 없음 | ✅ 자동 전송 |
| 사용자 인식 | 게스트 | 로그인 사용자 |
| user_id | None | 3 |
| 사용자 정보 | 없음 | email, name 등 |

## 🚀 다음 단계

이제 채팅 API에서:
1. ✅ 사용자 자동 인식
2. ✅ 사용자별 기능 활성화 (Gmail, Slack 등)
3. ✅ 개인화된 응답
4. ✅ 사용자별 히스토리 저장

모든 준비 완료! 🎉

