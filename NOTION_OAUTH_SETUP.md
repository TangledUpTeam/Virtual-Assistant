# Notion OAuth 설정 가이드

## 문제: Notion 로그인 시 권한 창이 아닌 Notion 사이트로 이동하는 경우

이는 **Internal Integration**을 사용하고 있거나 OAuth 설정이 잘못된 경우입니다.

## 해결 방법

### 1. Notion Integration 타입 확인

https://www.notion.so/my-integrations 에 접속하여:

- 현재 Integration이 **"Internal Integration"**인 경우 → OAuth 사용 불가
- **"Public Integration"**으로 변경하거나 새로 생성해야 함

### 2. Public OAuth Integration 생성

1. https://www.notion.so/my-integrations 접속
2. **"+ New integration"** 클릭
3. **Integration 타입 선택**:
   - ✅ **"Public"** 선택 (중요!)
   - ❌ "Internal" 선택하면 OAuth 불가

4. **기본 정보 입력**:
   - Name: `Virtual Assistant` (원하는 이름)
   - Associated workspace: 본인 워크스페이스 선택

5. **Capabilities 설정**:
   - ✅ Read content
   - ✅ Update content
   - ✅ Insert content
   - (필요한 권한 선택)

6. **OAuth Domain & URIs 설정** (중요!):
   - **Redirect URIs**:
     ```
     http://localhost:8000/api/v1/auth/notion/callback
     ```
   - **Submit** 클릭하여 저장

7. **Secrets 확인**:
   - **OAuth client ID**: `2bdd872b-...` 형식
   - **OAuth client secret**: `secret_...` 형식
   - **Internal Integration Secret**과 다름!

### 3. .env 파일 업데이트

`backend/.env` 파일에 다음 내용 확인:

```env
# Notion OAuth (Public Integration)
NOTION_CLIENT_ID=your_oauth_client_id_here
NOTION_CLIENT_SECRET=your_oauth_client_secret_here
NOTION_REDIRECT_URI=http://localhost:8000/api/v1/auth/notion/callback
```

⚠️ **주의**: 
- `NOTION_CLIENT_ID`는 **OAuth client ID**여야 함
- `NOTION_CLIENT_SECRET`는 **OAuth client secret**여야 함
- **Internal Integration Secret**이 아님!

### 4. 올바른 OAuth URL 확인

정상적인 Notion OAuth URL은 다음과 같아야 합니다:

```
https://api.notion.com/v1/oauth/authorize?client_id=YOUR_CLIENT_ID&redirect_uri=http://localhost:8000/api/v1/auth/notion/callback&response_type=code&owner=user&state=RANDOM_STATE
```

이 URL로 접속하면:
- ✅ Notion 권한 승인 페이지가 나타남
- ❌ Notion 워크스페이스로 바로 이동하면 안 됨

### 5. 테스트

1. 백엔드 재시작
2. 로그인 후 "Notion 연동하기" 클릭
3. 터미널에서 생성된 URL 확인:
   ```
   [DEBUG] Generated OAuth URL: https://api.notion.com/v1/oauth/authorize?...
   ```
4. 권한 승인 페이지가 나타나는지 확인

### 6. 문제 해결

만약 여전히 Notion 사이트로 이동한다면:

1. **Integration 타입 재확인**: Public인지 확인
2. **Redirect URI 확인**: 정확히 일치하는지 확인
3. **OAuth 활성화 확인**: Integration 설정에서 OAuth가 활성화되어 있는지 확인
4. **브라우저 캐시 삭제**: 이전 세션이 남아있을 수 있음

### 7. Internal Integration vs Public Integration

| 구분 | Internal Integration | Public Integration |
|------|---------------------|-------------------|
| 용도 | 개인/팀 내부 사용 | 외부 사용자에게 배포 |
| OAuth | ❌ 지원 안 함 | ✅ 지원 |
| 인증 방식 | API Key (Secret) | OAuth 2.0 |
| 권한 부여 | 수동으로 페이지 공유 | 사용자가 승인 |

**우리 프로젝트는 Public Integration이 필요합니다!**


값들이:
- ✅ Public Integration의 OAuth credentials인지 확인
- ❌ Internal Integration의 Secret이 아닌지 확인

## 참고 링크

- Notion OAuth 공식 문서: https://developers.notion.com/docs/authorization
- Notion Integrations 관리: https://www.notion.so/my-integrations

