# MCP 모듈 설정 가이드

Google Drive와 Gmail MCP 모듈을 설정하는 단계별 가이드입니다.

## 📋 사전 요구사항

- Python 3.8 이상
- Google 계정
- Google Cloud Console 접근 권한

## 🔧 1단계: Python 패키지 설치

```bash
pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib
```

또는 requirements.txt에 추가:

```txt
google-api-python-client>=2.100.0
google-auth-httplib2>=0.1.1
google-auth-oauthlib>=1.1.0
```

## 🌐 2단계: Google Cloud Console 설정

### 2.1. 프로젝트 생성

1. [Google Cloud Console](https://console.cloud.google.com/) 접속
2. 상단 프로젝트 드롭다운 클릭
3. "새 프로젝트" 클릭
4. 프로젝트 이름 입력 (예: "MCP-Virtual-Assistant")
5. "만들기" 클릭

### 2.2. API 활성화

1. 좌측 메뉴에서 "API 및 서비스" > "라이브러리" 선택
2. 다음 API를 검색하고 활성화:

#### Google Drive API
- "Google Drive API" 검색
- 클릭 후 "사용" 버튼 클릭

#### Gmail API
- "Gmail API" 검색
- 클릭 후 "사용" 버튼 클릭

### 2.3. OAuth 동의 화면 설정

1. "API 및 서비스" > "OAuth 동의 화면" 선택
2. 사용자 유형 선택:
   - **테스트/개발용**: "외부" 선택
   - **내부용**: "내부" 선택 (Google Workspace 계정만)
3. "만들기" 클릭

#### 앱 정보 입력:
- **앱 이름**: "Virtual Assistant MCP"
- **사용자 지원 이메일**: 본인 이메일
- **개발자 연락처 정보**: 본인 이메일
- "저장 후 계속" 클릭

#### 범위 추가:
1. "범위 추가 또는 삭제" 클릭
2. 다음 범위 검색 및 추가:
   - `https://www.googleapis.com/auth/drive.file`
   - `https://www.googleapis.com/auth/gmail.send`
   - `https://www.googleapis.com/auth/gmail.readonly`
   - `https://www.googleapis.com/auth/gmail.compose`
   - `https://www.googleapis.com/auth/gmail.modify`
3. "업데이트" 클릭
4. "저장 후 계속" 클릭

#### 테스트 사용자 추가 (외부 앱인 경우):
1. "+ ADD USERS" 클릭
2. 테스트할 이메일 주소 입력
3. "저장 후 계속" 클릭

### 2.4. OAuth 2.0 클라이언트 ID 생성

1. "API 및 서비스" > "사용자 인증 정보" 선택
2. 상단 "+ 사용자 인증 정보 만들기" 클릭
3. "OAuth 클라이언트 ID" 선택

#### 애플리케이션 유형 선택:
- **데스크톱 앱**: "데스크톱 앱" 선택
- 이름: "MCP Desktop Client"
- "만들기" 클릭

#### JSON 파일 다운로드:
1. 생성된 클라이언트 ID 옆의 다운로드 아이콘 클릭
2. JSON 파일 다운로드

## 📁 3단계: 설정 파일 배치

### 3.1. Google Drive 설정

다운로드한 JSON 파일을 다음 경로에 복사:

```
mcp/google_drive/client_secrets.json
```

### 3.2. Gmail 설정

**같은** JSON 파일을 다음 경로에도 복사:

```
mcp/gmail/client_secrets.json
```

> 💡 **팁**: 두 서비스가 같은 Google 계정을 사용하므로 동일한 client_secrets.json을 사용합니다.

### 3.3. 폴더 구조 확인

```
mcp/
├── google_drive/
│   └── client_secrets.json  ✓
├── gmail/
│   └── client_secrets.json  ✓
└── token_storage/
    └── tokens/              (자동 생성됨)
```

## 🔐 4단계: 사용자 인증

### 4.1. 인증 코드 방식 (권장)

```python
from mcp.mcp_manager import MCPManager

manager = MCPManager()

# 1. 인증 URL 생성
auth_url = manager.get_drive_auth_url()
print(f"브라우저에서 접속: {auth_url}")

# 2. 브라우저에서 인증 후 코드 복사
code = input("인증 코드를 입력하세요: ")

# 3. 토큰 교환
user_id = "user123"
result = manager.authorize_drive_user(code, user_id)

if result["success"]:
    print("✓ 인증 성공!")
else:
    print(f"✗ 인증 실패: {result.get('error')}")
```

### 4.2. Gmail 인증

```python
# Gmail도 동일한 방식
auth_url = manager.get_gmail_auth_url()
print(f"브라우저에서 접속: {auth_url}")

code = input("인증 코드를 입력하세요: ")
result = manager.authorize_gmail_user(code, user_id)
```

## ✅ 5단계: 테스트

### 5.1. 간단한 테스트

```python
from mcp.mcp_manager import MCPManager

manager = MCPManager()
user_id = "user123"

# Google Drive 테스트
result = manager.drive_create_folder(user_id, "테스트 폴더")
print(result)

# Gmail 테스트
result = manager.gmail_list_messages(user_id, max_results=5)
print(result)
```

### 5.2. 예제 실행

```bash
cd mcp
python example_usage.py
```

## 🔍 문제 해결

### "인증되지 않은 사용자입니다" 오류

**원인**: OAuth 토큰이 없거나 만료됨

**해결**:
1. 4단계의 인증 과정 다시 수행
2. `mcp/token_storage/tokens/` 디렉토리 확인
3. 해당 사용자의 토큰 파일이 있는지 확인

### "client_secrets.json not found" 오류

**원인**: OAuth 클라이언트 설정 파일이 없음

**해결**:
1. 2.4단계에서 JSON 파일을 다운로드했는지 확인
2. 올바른 경로에 배치했는지 확인:
   - `mcp/google_drive/client_secrets.json`
   - `mcp/gmail/client_secrets.json`

### "API has not been used" 오류

**원인**: Google Cloud Console에서 API가 활성화되지 않음

**해결**:
1. 2.2단계의 API 활성화 과정 다시 확인
2. Google Drive API와 Gmail API 모두 활성화되어 있는지 확인

### "Access blocked: This app's request is invalid" 오류

**원인**: OAuth 동의 화면 설정 문제

**해결**:
1. 2.3단계의 OAuth 동의 화면 설정 재확인
2. 필요한 scope가 모두 추가되었는지 확인
3. 테스트 사용자에 본인 이메일이 추가되었는지 확인

### 토큰이 자동으로 갱신되지 않음

**원인**: refresh_token이 없거나 유효하지 않음

**해결**:
1. 기존 토큰 삭제:
   ```python
   manager.revoke_drive_access(user_id)
   ```
2. 인증 다시 수행 (4단계)

## 🔒 보안 권장사항

### 1. client_secrets.json 보호

```bash
# .gitignore에 추가되어 있는지 확인
cat mcp/.gitignore | grep client_secrets.json
```

### 2. 토큰 디렉토리 보호

```bash
# 토큰 디렉토리 권한 설정 (Linux/Mac)
chmod 700 mcp/token_storage/tokens/
```

### 3. 프로덕션 환경

프로덕션 환경에서는:
1. 환경 변수로 client_secrets 관리
2. 토큰을 데이터베이스에 암호화하여 저장
3. HTTPS를 사용한 리다이렉트 URI 설정

## 📚 추가 자료

- [Google Drive API 문서](https://developers.google.com/drive/api/v3/about-sdk)
- [Gmail API 문서](https://developers.google.com/gmail/api/guides)
- [Google OAuth 2.0 가이드](https://developers.google.com/identity/protocols/oauth2)

## 💬 지원

문제가 지속되면 다음을 확인하세요:
1. Python 버전 (3.8 이상)
2. 패키지 버전 (최신 버전 권장)
3. Google Cloud Console 설정
4. 네트워크 연결

---

설정 완료 후 [README.md](./README.md)의 사용법을 참고하세요.

