# MCP (Model Context Protocol) 모듈

Google Drive와 Gmail을 에이전트가 tool-call로 사용할 수 있도록 하는 독립적인 MCP 모듈입니다.

## 📁 구조

```
mcp/
├── token_storage/          # 사용자별 OAuth 토큰 저장소
│   ├── __init__.py
│   ├── token_store.py
│   └── tokens/            # 토큰 파일들이 저장되는 디렉토리
│
├── google_drive/          # Google Drive MCP 모듈
│   ├── __init__.py
│   ├── server.py         # Tool-call 엔드포인트
│   ├── drive_api.py      # Drive API 구현
│   ├── oauth.py          # OAuth 핸들러
│   └── client_secrets.json  # (사용자가 추가) OAuth credentials
│
├── gmail/                # Gmail MCP 모듈
│   ├── __init__.py
│   ├── server.py         # Tool-call 엔드포인트
│   ├── gmail_api.py      # Gmail API 구현
│   ├── oauth.py          # OAuth 핸들러
│   └── client_secrets.json  # (사용자가 추가) OAuth credentials
│
├── __init__.py
├── mcp_manager.py        # 통합 MCP 관리자
├── README.md             # 이 문서
└── example_usage.py      # 사용 예제
```

## 🚀 설치

### 1. 필요한 패키지 설치

```bash
pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib
```

### 2. Google Cloud Console 설정

1. [Google Cloud Console](https://console.cloud.google.com/)에서 프로젝트 생성
2. "API 및 서비스" > "라이브러리"에서 다음 API 활성화:
   - Google Drive API
   - Gmail API
3. "API 및 서비스" > "OAuth 동의 화면" 설정
4. "API 및 서비스" > "사용자 인증 정보" > "OAuth 2.0 클라이언트 ID" 생성
5. JSON 파일 다운로드 후 다음 위치에 저장:
   - `mcp/google_drive/client_secrets.json`
   - `mcp/gmail/client_secrets.json`

## 📖 사용법

### 기본 사용

```python
from mcp.mcp_manager import MCPManager

# MCP Manager 초기화
manager = MCPManager()

# 사용자 ID (실제 앱에서는 로그인한 사용자의 ID)
user_id = "user123"
```

### OAuth 인증

```python
# 1. 인증 URL 생성
drive_auth_url = manager.get_drive_auth_url()
gmail_auth_url = manager.get_gmail_auth_url()

print(f"Google Drive 인증: {drive_auth_url}")
print(f"Gmail 인증: {gmail_auth_url}")

# 2. 사용자가 브라우저에서 인증 후 받은 코드로 토큰 교환
drive_code = "사용자가_받은_인증_코드"
gmail_code = "사용자가_받은_인증_코드"

manager.authorize_drive_user(drive_code, user_id)
manager.authorize_gmail_user(gmail_code, user_id)
```

### Google Drive Tool-calls

```python
# 폴더 생성
result = manager.drive_create_folder(user_id, "내 프로젝트")
folder_id = result.get("folder_id")

# 파일 업로드
result = manager.drive_upload_file(
    user_id,
    local_path="./report.pdf",
    folder_id=folder_id,
    filename="월간보고서.pdf"
)
file_id = result.get("file_id")

# 파일 검색
result = manager.drive_search(user_id, "name contains '보고서'")
files = result.get("files", [])

# 파일 다운로드
result = manager.drive_download_file(user_id, file_id)
file_data_base64 = result.get("data")

# 파일 읽기
result = manager.drive_read(user_id, file_id)
content = result.get("data")

# 파일 목록 조회
result = manager.drive_list_files(user_id, folder_id=folder_id)
files = result.get("files", [])
```

### Gmail Tool-calls

```python
# 이메일 보내기
result = manager.gmail_send_email(
    user_id,
    to="recipient@example.com",
    subject="프로젝트 보고서",
    body="첨부된 보고서를 확인해주세요."
)

# 첨부 파일과 함께 이메일 보내기
import base64

with open("report.pdf", "rb") as f:
    attachment_data = base64.b64encode(f.read()).decode('utf-8')

result = manager.gmail_send_email(
    user_id,
    to="recipient@example.com",
    subject="보고서 첨부",
    body="보고서 파일입니다.",
    attachment_base64=attachment_data,
    attachment_filename="report.pdf"
)

# 받은 메일 목록 조회
result = manager.gmail_list_messages(user_id, query="is:unread", max_results=5)
messages = result.get("messages", [])

# 특정 메시지 상세 조회
if messages:
    message_id = messages[0]["id"]
    result = manager.gmail_get_message(user_id, message_id)
    print(f"From: {result.get('from')}")
    print(f"Subject: {result.get('subject')}")
    print(f"Body: {result.get('body')}")

# 초안 생성
result = manager.gmail_create_draft(
    user_id,
    to="recipient@example.com",
    subject="초안 테스트",
    body="나중에 보낼 이메일"
)
draft_id = result.get("draft_id")

# 메시지를 읽음으로 표시
manager.gmail_mark_as_read(user_id, message_id)
```

## 🔧 에이전트 통합

에이전트가 tool-call로 사용할 수 있도록 MCPManager를 통합하는 예제:

```python
from mcp.mcp_manager import MCPManager

class AIAgent:
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.mcp = MCPManager()
    
    def execute_tool_call(self, tool_name: str, **kwargs):
        """에이전트가 tool-call을 실행하는 메서드"""
        
        # user_id를 자동으로 추가
        kwargs['user_id'] = self.user_id
        
        # MCP Manager에서 해당 메서드 호출
        if hasattr(self.mcp, tool_name):
            method = getattr(self.mcp, tool_name)
            return method(**kwargs)
        else:
            return {"success": False, "error": f"Unknown tool: {tool_name}"}
    
    def process_user_request(self, request: str):
        """사용자 요청 처리 예제"""
        
        if "메일 보내" in request:
            # 예: "홍길동에게 메일 보내줘"
            return self.execute_tool_call(
                "gmail_send_email",
                to="hong@example.com",
                subject="안녕하세요",
                body="메시지 내용"
            )
        
        elif "파일 업로드" in request:
            # 예: "report.pdf를 드라이브에 업로드해줘"
            return self.execute_tool_call(
                "drive_upload_file",
                local_path="./report.pdf"
            )
        
        # ... 기타 tool-call 처리

# 사용 예
agent = AIAgent("user123")
result = agent.execute_tool_call("drive_create_folder", name="AI Projects")
```

## 📋 사용 가능한 Tool-calls

### Google Drive

| Tool-call | 설명 | 주요 파라미터 |
|-----------|------|--------------|
| `drive_create_folder` | 폴더 생성 | `name`, `parent_folder_id` |
| `drive_upload_file` | 파일 업로드 | `local_path`, `folder_id` |
| `drive_download_file` | 파일 다운로드 | `file_id` |
| `drive_search` | 파일 검색 | `query`, `max_results` |
| `drive_read` | 파일 읽기 | `file_id` |
| `drive_list_files` | 파일 목록 조회 | `folder_id`, `max_results` |
| `drive_delete_file` | 파일 삭제 | `file_id` |

### Gmail

| Tool-call | 설명 | 주요 파라미터 |
|-----------|------|--------------|
| `gmail_send_email` | 이메일 보내기 | `to`, `subject`, `body`, `attachment_base64` |
| `gmail_list_messages` | 받은 메일 목록 | `query`, `max_results` |
| `gmail_get_message` | 메시지 상세 조회 | `message_id` |
| `gmail_create_draft` | 초안 생성 | `to`, `subject`, `body` |
| `gmail_delete_message` | 메시지 삭제 | `message_id` |
| `gmail_mark_as_read` | 읽음 표시 | `message_id` |
| `gmail_mark_as_unread` | 읽지 않음 표시 | `message_id` |

## 🔐 OAuth Scope

이 MCP 모듈들은 다음 Google OAuth scope를 사용합니다:

- `https://www.googleapis.com/auth/drive.file`
- `https://www.googleapis.com/auth/gmail.send`
- `https://www.googleapis.com/auth/gmail.readonly`
- `https://www.googleapis.com/auth/gmail.compose`
- `https://www.googleapis.com/auth/gmail.modify`

## 📝 토큰 저장

사용자별 OAuth 토큰은 다음 위치에 저장됩니다:

```
mcp/token_storage/tokens/
├── user123_google_drive_token.json
└── user123_gmail_token.json
```

## ⚠️ 주의사항

1. **보안**: `client_secrets.json` 파일과 `tokens/` 디렉토리를 `.gitignore`에 추가하세요.
2. **독립성**: 이 MCP 모듈은 다른 프로젝트 폴더(`backend/`, `frontend/` 등)와 완전히 독립적입니다.
3. **에러 처리**: 모든 tool-call은 `{"success": bool}` 형태로 결과를 반환하므로 항상 확인하세요.

## 🧪 테스트

```bash
cd mcp
python example_usage.py
```

## 📄 라이선스

이 MCP 모듈은 프로젝트의 일부로, 프로젝트 라이선스를 따릅니다.

