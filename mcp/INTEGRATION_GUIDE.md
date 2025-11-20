# MCP 모듈 에이전트 통합 가이드

이 문서는 AI 에이전트가 MCP 모듈의 tool-call을 사용하는 방법을 설명합니다.

## 🎯 개요

MCP (Model Context Protocol) 모듈은 Google Drive와 Gmail을 에이전트가 tool-call로 사용할 수 있도록 합니다.

### 주요 특징

- ✅ **완전 독립**: RAG, backend, frontend 등 다른 폴더와 완전히 독립적
- ✅ **OAuth 인증**: 사용자별 토큰 관리
- ✅ **Tool-call 인터페이스**: 표준화된 함수 호출 방식
- ✅ **에러 처리**: 모든 함수가 `{"success": bool}` 형식으로 반환

## 📦 빠른 시작

### 1. 설치

```bash
cd mcp
pip install -r requirements.txt
```

### 2. 기본 사용

```python
from mcp.mcp_manager import MCPManager

# MCP Manager 초기화
manager = MCPManager()

# 사용자 ID
user_id = "user123"

# Google Drive 폴더 생성
result = manager.drive_create_folder(user_id, "내 폴더")

if result["success"]:
    folder_id = result["folder_id"]
    print(f"폴더 생성 완료: {folder_id}")
else:
    print(f"오류: {result['error']}")
```

## 🤖 에이전트 통합 패턴

### 패턴 1: 직접 호출

```python
from mcp.mcp_manager import MCPManager

class MyAgent:
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.mcp = MCPManager()
    
    def handle_request(self, request: str):
        # 사용자 요청 처리
        if "폴더 만들어" in request:
            result = self.mcp.drive_create_folder(
                self.user_id,
                name="새 폴더"
            )
            return result
```

### 패턴 2: Tool Registry

```python
from mcp.mcp_manager import MCPManager
from typing import Callable, Dict, Any

class AgentWithTools:
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.mcp = MCPManager()
        self.tools = self._register_tools()
    
    def _register_tools(self) -> Dict[str, Callable]:
        """사용 가능한 도구 등록"""
        return {
            # Google Drive
            "create_folder": self.mcp.drive_create_folder,
            "upload_file": self.mcp.drive_upload_file,
            "search_files": self.mcp.drive_search,
            
            # Gmail
            "send_email": self.mcp.gmail_send_email,
            "read_emails": self.mcp.gmail_list_messages,
        }
    
    def execute_tool(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        """도구 실행"""
        if tool_name not in self.tools:
            return {"success": False, "error": f"Unknown tool: {tool_name}"}
        
        # user_id 자동 추가
        kwargs["user_id"] = self.user_id
        
        # 도구 실행
        tool_func = self.tools[tool_name]
        return tool_func(**kwargs)

# 사용 예
agent = AgentWithTools("user123")
result = agent.execute_tool("create_folder", name="프로젝트 폴더")
```

### 패턴 3: LLM Function Calling

OpenAI Function Calling이나 LangChain Tools와 통합하는 예제:

```python
from mcp.mcp_manager import MCPManager
import json

class LLMAgent:
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.mcp = MCPManager()
    
    def get_tool_definitions(self):
        """LLM에 전달할 도구 정의"""
        return [
            {
                "name": "drive_create_folder",
                "description": "Google Drive에 새 폴더를 생성합니다",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "생성할 폴더 이름"
                        },
                        "parent_folder_id": {
                            "type": "string",
                            "description": "부모 폴더 ID (선택사항)"
                        }
                    },
                    "required": ["name"]
                }
            },
            {
                "name": "gmail_send_email",
                "description": "Gmail로 이메일을 보냅니다",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "to": {
                            "type": "string",
                            "description": "수신자 이메일 주소"
                        },
                        "subject": {
                            "type": "string",
                            "description": "이메일 제목"
                        },
                        "body": {
                            "type": "string",
                            "description": "이메일 본문"
                        }
                    },
                    "required": ["to", "subject", "body"]
                }
            }
            # ... 더 많은 도구들
        ]
    
    def execute_function_call(self, function_name: str, arguments: dict):
        """LLM이 요청한 function call 실행"""
        
        # MCP Manager의 메서드에 매핑
        function_map = {
            "drive_create_folder": self.mcp.drive_create_folder,
            "gmail_send_email": self.mcp.gmail_send_email,
            # ... 더 많은 매핑
        }
        
        if function_name not in function_map:
            return {"success": False, "error": "Unknown function"}
        
        # user_id 추가
        arguments["user_id"] = self.user_id
        
        # 함수 실행
        func = function_map[function_name]
        return func(**arguments)

# OpenAI API와 함께 사용 예
"""
import openai

agent = LLMAgent("user123")

messages = [
    {"role": "user", "content": "내 드라이브에 '프로젝트' 폴더를 만들어줘"}
]

response = openai.ChatCompletion.create(
    model="gpt-4",
    messages=messages,
    functions=agent.get_tool_definitions(),
    function_call="auto"
)

# Function call이 있으면 실행
if response.choices[0].message.get("function_call"):
    func_name = response.choices[0].message["function_call"]["name"]
    func_args = json.loads(response.choices[0].message["function_call"]["arguments"])
    
    result = agent.execute_function_call(func_name, func_args)
    print(result)
"""
```

### 패턴 4: LangChain Integration

```python
from langchain.tools import Tool
from mcp.mcp_manager import MCPManager

class MCPLangChainTools:
    """LangChain Tools로 MCP 모듈 통합"""
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.mcp = MCPManager()
    
    def get_tools(self):
        """LangChain Tool 객체 리스트 반환"""
        return [
            Tool(
                name="CreateDriveFolder",
                func=self._create_folder_wrapper,
                description="Google Drive에 새 폴더를 생성합니다. Input: 폴더 이름"
            ),
            Tool(
                name="SearchDriveFiles",
                func=self._search_files_wrapper,
                description="Google Drive에서 파일을 검색합니다. Input: 검색 쿼리"
            ),
            Tool(
                name="SendGmail",
                func=self._send_email_wrapper,
                description="Gmail로 이메일을 보냅니다. Input: 'to|subject|body' 형식"
            ),
            # ... 더 많은 도구들
        ]
    
    def _create_folder_wrapper(self, folder_name: str) -> str:
        """LangChain Tool wrapper"""
        result = self.mcp.drive_create_folder(self.user_id, folder_name)
        if result["success"]:
            return f"폴더 생성 완료: {result['folder_id']}"
        else:
            return f"오류: {result['error']}"
    
    def _search_files_wrapper(self, query: str) -> str:
        """LangChain Tool wrapper"""
        result = self.mcp.drive_search(self.user_id, query)
        if result["success"]:
            files = result["files"]
            return f"{len(files)}개 파일 발견: " + ", ".join([f["name"] for f in files])
        else:
            return f"오류: {result['error']}"
    
    def _send_email_wrapper(self, email_info: str) -> str:
        """LangChain Tool wrapper"""
        # Input 형식: "to|subject|body"
        try:
            to, subject, body = email_info.split("|", 2)
            result = self.mcp.gmail_send_email(
                self.user_id,
                to=to.strip(),
                subject=subject.strip(),
                body=body.strip()
            )
            if result["success"]:
                return f"이메일 전송 완료: {result['message_id']}"
            else:
                return f"오류: {result['error']}"
        except Exception as e:
            return f"입력 형식 오류: {str(e)}"

# LangChain Agent와 함께 사용
"""
from langchain.agents import initialize_agent, AgentType
from langchain.llms import OpenAI

mcp_tools = MCPLangChainTools("user123")
tools = mcp_tools.get_tools()

llm = OpenAI(temperature=0)
agent = initialize_agent(
    tools,
    llm,
    agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    verbose=True
)

# 사용
agent.run("내 드라이브에 '새 프로젝트' 폴더를 만들고 README 파일을 검색해줘")
"""
```

## 📋 사용 가능한 모든 Tool-calls

### Google Drive Tools

```python
# 1. 폴더 생성
result = manager.drive_create_folder(
    user_id="user123",
    name="폴더 이름",
    parent_folder_id=None  # 선택사항
)

# 2. 파일 업로드
result = manager.drive_upload_file(
    user_id="user123",
    local_path="./file.pdf",
    folder_id=None,  # 선택사항
    filename=None  # 선택사항
)

# 3. 파일 다운로드
result = manager.drive_download_file(
    user_id="user123",
    file_id="파일ID"
)

# 4. 파일 검색
result = manager.drive_search(
    user_id="user123",
    query="name contains '문서'",
    max_results=10
)

# 5. 파일 읽기
result = manager.drive_read(
    user_id="user123",
    file_id="파일ID"
)

# 6. 파일 목록 조회
result = manager.drive_list_files(
    user_id="user123",
    folder_id=None,  # 선택사항
    max_results=20
)

# 7. 파일 삭제
result = manager.drive_delete_file(
    user_id="user123",
    file_id="파일ID"
)
```

### Gmail Tools

```python
# 1. 이메일 보내기
result = manager.gmail_send_email(
    user_id="user123",
    to="recipient@example.com",
    subject="제목",
    body="본문",
    attachment_base64=None,  # 선택사항
    attachment_filename=None  # 선택사항
)

# 2. 메일 목록 조회
result = manager.gmail_list_messages(
    user_id="user123",
    query="is:unread",  # 선택사항
    max_results=10
)

# 3. 메시지 상세 조회
result = manager.gmail_get_message(
    user_id="user123",
    message_id="메시지ID"
)

# 4. 초안 생성
result = manager.gmail_create_draft(
    user_id="user123",
    to="recipient@example.com",
    subject="제목",
    body="본문",
    attachment_base64=None,  # 선택사항
    attachment_filename=None  # 선택사항
)

# 5. 메시지 삭제
result = manager.gmail_delete_message(
    user_id="user123",
    message_id="메시지ID"
)

# 6. 읽음 표시
result = manager.gmail_mark_as_read(
    user_id="user123",
    message_id="메시지ID"
)

# 7. 읽지 않음 표시
result = manager.gmail_mark_as_unread(
    user_id="user123",
    message_id="메시지ID"
)
```

## 🔐 OAuth 관리

### 인증 URL 생성

```python
# Google Drive 인증
auth_url = manager.get_drive_auth_url()

# Gmail 인증
auth_url = manager.get_gmail_auth_url()

# 커스텀 리다이렉트 URI
auth_url = manager.get_drive_auth_url(redirect_uri="http://localhost:8000/callback")
```

### 사용자 인증

```python
# Google Drive
result = manager.authorize_drive_user(
    code="인증_코드",
    user_id="user123"
)

# Gmail
result = manager.authorize_gmail_user(
    code="인증_코드",
    user_id="user123"
)
```

### 액세스 취소

```python
# Google Drive 액세스 취소
result = manager.revoke_drive_access(user_id="user123")

# Gmail 액세스 취소
result = manager.revoke_gmail_access(user_id="user123")
```

## 🎨 고급 사용 예제

### 예제 1: 파일 업로드 후 공유 링크 생성

```python
# 파일 업로드
result = manager.drive_upload_file(user_id, "./report.pdf")
file_id = result["file_id"]

# 파일 정보 조회 (검색으로)
result = manager.drive_search(user_id, f"id = '{file_id}'")
file_info = result["files"][0]

print(f"파일 링크: https://drive.google.com/file/d/{file_id}/view")
```

### 예제 2: 이메일 + 첨부 파일

```python
import base64

# 파일을 base64로 인코딩
with open("report.pdf", "rb") as f:
    file_data = base64.b64encode(f.read()).decode('utf-8')

# 이메일 전송
result = manager.gmail_send_email(
    user_id,
    to="boss@company.com",
    subject="월간 보고서",
    body="이번 달 보고서를 첨부합니다.",
    attachment_base64=file_data,
    attachment_filename="report.pdf"
)
```

### 예제 3: 읽지 않은 메일 처리

```python
# 읽지 않은 메일 조회
result = manager.gmail_list_messages(user_id, query="is:unread", max_results=10)

for msg in result["messages"]:
    # 메시지 상세 조회
    detail = manager.gmail_get_message(user_id, msg["id"])
    
    print(f"From: {detail['from']}")
    print(f"Subject: {detail['subject']}")
    
    # 읽음 표시
    manager.gmail_mark_as_read(user_id, msg["id"])
```

## 🐛 에러 처리

모든 tool-call은 일관된 형식으로 결과를 반환합니다:

```python
# 성공
{
    "success": True,
    "folder_id": "...",  # 결과 데이터
    # ... 기타 필드
}

# 실패
{
    "success": False,
    "error": "오류 메시지"
}
```

권장 에러 처리 패턴:

```python
result = manager.drive_create_folder(user_id, "폴더")

if result["success"]:
    # 성공 처리
    folder_id = result["folder_id"]
    print(f"성공: {folder_id}")
else:
    # 에러 처리
    error = result["error"]
    
    if "인증되지 않은" in error:
        # OAuth 재인증 필요
        print("인증이 필요합니다.")
    else:
        # 기타 에러
        print(f"오류 발생: {error}")
```

## 📚 추가 리소스

- [README.md](./README.md) - 기본 사용법
- [SETUP_GUIDE.md](./SETUP_GUIDE.md) - 설정 가이드
- [example_usage.py](./example_usage.py) - 실행 가능한 예제

## 💡 팁

1. **user_id 관리**: 실제 앱에서는 로그인한 사용자의 고유 ID를 사용하세요
2. **토큰 자동 갱신**: OAuth 모듈이 자동으로 토큰을 갱신합니다
3. **에러 처리**: 항상 `success` 필드를 확인하세요
4. **독립성**: MCP 모듈은 다른 코드와 완전히 독립적입니다

---

질문이나 문제가 있으면 [README.md](./README.md)의 문제 해결 섹션을 참고하세요.

