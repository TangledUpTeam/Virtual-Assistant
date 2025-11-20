# MCP 모듈 빠른 시작 가이드

## 🚀 5분 안에 시작하기

### 1단계: 패키지 설치 (1분)

```bash
cd mcp
pip install -r requirements.txt
```

### 2단계: Google Cloud 설정 (2분)

1. [Google Cloud Console](https://console.cloud.google.com/) 접속
2. 프로젝트 생성
3. Google Drive API & Gmail API 활성화
4. OAuth 클라이언트 ID 생성 (데스크톱 앱)
5. JSON 파일 다운로드

### 3단계: 설정 파일 배치 (30초)

```bash
# 다운로드한 JSON 파일을 복사
cp ~/Downloads/client_secret_*.json mcp/google_drive/client_secrets.json
cp ~/Downloads/client_secret_*.json mcp/gmail/client_secrets.json
```

### 4단계: 사용자 인증 (1분)

```python
from mcp.mcp_manager import MCPManager

manager = MCPManager()

# 인증 URL 생성
print(manager.get_drive_auth_url())

# 브라우저에서 인증 후 코드 입력
code = input("인증 코드: ")
manager.authorize_drive_user(code, "user123")

print("✓ 인증 완료!")
```

### 5단계: 첫 번째 Tool-call (30초)

```python
# 폴더 생성
result = manager.drive_create_folder("user123", "내 첫 폴더")
print(result)

# 메일 목록 조회
result = manager.gmail_list_messages("user123", max_results=5)
print(result)
```

## 🎯 주요 사용 사례

### 📁 파일 관리

```python
# 파일 업로드
manager.drive_upload_file("user123", "./report.pdf")

# 파일 검색
manager.drive_search("user123", "name contains '보고서'")
```

### 📧 이메일 관리

```python
# 이메일 보내기
manager.gmail_send_email(
    "user123",
    to="friend@example.com",
    subject="안녕",
    body="잘 지내?"
)

# 받은 메일 읽기
manager.gmail_list_messages("user123", query="is:unread")
```

## 📚 더 알아보기

- **상세 문서**: [README.md](./README.md)
- **설정 가이드**: [SETUP_GUIDE.md](./SETUP_GUIDE.md)
- **에이전트 통합**: [INTEGRATION_GUIDE.md](./INTEGRATION_GUIDE.md)
- **예제 코드**: [example_usage.py](./example_usage.py)

## ❓ 문제 해결

**"인증되지 않은 사용자"** → 4단계 다시 수행

**"API has not been used"** → 2단계에서 API 활성화 확인

**"client_secrets.json not found"** → 3단계 파일 경로 확인

## 💬 지원

자세한 내용은 [SETUP_GUIDE.md](./SETUP_GUIDE.md)를 참고하세요.

