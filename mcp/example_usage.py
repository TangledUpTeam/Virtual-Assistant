"""
MCP 사용 예제
Google Drive와 Gmail MCP 모듈 사용법 데모
"""

from mcp_manager import MCPManager


def demo_oauth_flow():
    """OAuth 인증 플로우 데모"""
    print("=" * 50)
    print("OAuth 인증 플로우")
    print("=" * 50)
    
    manager = MCPManager()
    
    # 1. 인증 URL 생성
    drive_auth_url = manager.get_drive_auth_url()
    gmail_auth_url = manager.get_gmail_auth_url()
    
    print("\n[1단계] 브라우저에서 다음 URL에 접속하여 인증하세요:")
    print(f"\nGoogle Drive 인증:")
    print(drive_auth_url)
    print(f"\nGmail 인증:")
    print(gmail_auth_url)
    
    # 2. 사용자 입력 (실제 사용 시)
    print("\n[2단계] 인증 후 받은 코드를 입력하세요:")
    # drive_code = input("Google Drive 인증 코드: ")
    # gmail_code = input("Gmail 인증 코드: ")
    # 
    # user_id = "demo_user"
    # manager.authorize_drive_user(drive_code, user_id)
    # manager.authorize_gmail_user(gmail_code, user_id)
    # 
    # print("\n✓ 인증 완료!")


def demo_google_drive(user_id: str = "demo_user"):
    """Google Drive 기능 데모"""
    print("\n" + "=" * 50)
    print("Google Drive Tool-calls 데모")
    print("=" * 50)
    
    manager = MCPManager()
    
    # 1. 폴더 생성
    print("\n[1] 폴더 생성")
    result = manager.drive_create_folder(user_id, "MCP 테스트 폴더")
    if result.get("success"):
        folder_id = result.get("folder_id")
        print(f"✓ 폴더 생성 성공: {folder_id}")
    else:
        print(f"✗ 실패: {result.get('error')}")
        return
    
    # 2. 파일 업로드 (예제 파일 경로)
    print("\n[2] 파일 업로드")
    result = manager.drive_upload_file(
        user_id,
        local_path="./README.md",  # 예제 파일
        folder_id=folder_id,
        filename="MCP_README.md"
    )
    if result.get("success"):
        file_id = result.get("file_id")
        print(f"✓ 파일 업로드 성공: {file_id}")
    else:
        print(f"✗ 실패: {result.get('error')}")
        return
    
    # 3. 파일 검색
    print("\n[3] 파일 검색")
    result = manager.drive_search(user_id, "name contains 'README'", max_results=5)
    if result.get("success"):
        files = result.get("files", [])
        print(f"✓ 검색 결과: {len(files)}개 파일")
        for file in files:
            print(f"  - {file.get('name')} ({file.get('id')})")
    else:
        print(f"✗ 실패: {result.get('error')}")
    
    # 4. 파일 목록 조회
    print("\n[4] 폴더 내 파일 목록")
    result = manager.drive_list_files(user_id, folder_id=folder_id)
    if result.get("success"):
        files = result.get("files", [])
        print(f"✓ 폴더 내 파일: {len(files)}개")
        for file in files:
            print(f"  - {file.get('name')}")
    else:
        print(f"✗ 실패: {result.get('error')}")
    
    # 5. 파일 다운로드
    print("\n[5] 파일 다운로드")
    result = manager.drive_download_file(user_id, file_id)
    if result.get("success"):
        filename = result.get("filename")
        size = result.get("size_bytes")
        print(f"✓ 다운로드 성공: {filename} ({size} bytes)")
        # data_base64 = result.get("data")  # base64 인코딩된 데이터
    else:
        print(f"✗ 실패: {result.get('error')}")


def demo_gmail(user_id: str = "demo_user"):
    """Gmail 기능 데모"""
    print("\n" + "=" * 50)
    print("Gmail Tool-calls 데모")
    print("=" * 50)
    
    manager = MCPManager()
    
    # 1. 받은 메일 목록 조회
    print("\n[1] 받은 메일 목록 (최근 5개)")
    result = manager.gmail_list_messages(user_id, max_results=5)
    if result.get("success"):
        messages = result.get("messages", [])
        print(f"✓ 메일 {len(messages)}개 조회 성공")
        for msg in messages:
            print(f"  - {msg.get('subject')} (from: {msg.get('from')})")
            print(f"    {msg.get('snippet')[:50]}...")
        
        # 첫 번째 메시지 상세 조회
        if messages:
            message_id = messages[0]["id"]
            print(f"\n[2] 메시지 상세 조회")
            result = manager.gmail_get_message(user_id, message_id)
            if result.get("success"):
                print(f"✓ 메시지 상세:")
                print(f"  From: {result.get('from')}")
                print(f"  To: {result.get('to')}")
                print(f"  Subject: {result.get('subject')}")
                print(f"  Date: {result.get('date')}")
                print(f"  Body: {result.get('body')[:100]}...")
                print(f"  Attachments: {len(result.get('attachments', []))}개")
            else:
                print(f"✗ 실패: {result.get('error')}")
    else:
        print(f"✗ 실패: {result.get('error')}")
    
    # 3. 초안 생성
    print("\n[3] 초안 생성")
    result = manager.gmail_create_draft(
        user_id,
        to="test@example.com",
        subject="MCP 테스트 초안",
        body="이것은 MCP Gmail 모듈 테스트 초안입니다."
    )
    if result.get("success"):
        draft_id = result.get("draft_id")
        print(f"✓ 초안 생성 성공: {draft_id}")
    else:
        print(f"✗ 실패: {result.get('error')}")
    
    # 4. 이메일 보내기 (주석 처리 - 실제 발송 방지)
    print("\n[4] 이메일 보내기 (데모 - 실제 발송 안 함)")
    print("  실제 사용 시:")
    print("""
    result = manager.gmail_send_email(
        user_id,
        to="recipient@example.com",
        subject="안녕하세요",
        body="MCP Gmail 테스트 메일입니다."
    )
    """)


def demo_agent_integration(user_id: str = "demo_user"):
    """에이전트 통합 예제"""
    print("\n" + "=" * 50)
    print("에이전트 통합 데모")
    print("=" * 50)
    
    class SimpleAgent:
        """간단한 에이전트 예제"""
        
        def __init__(self, user_id: str):
            self.user_id = user_id
            self.mcp = MCPManager()
        
        def execute_tool(self, tool_name: str, **kwargs):
            """Tool-call 실행"""
            kwargs['user_id'] = self.user_id
            
            if hasattr(self.mcp, tool_name):
                method = getattr(self.mcp, tool_name)
                return method(**kwargs)
            else:
                return {"success": False, "error": f"Unknown tool: {tool_name}"}
        
        def process_command(self, command: str):
            """간단한 명령어 처리"""
            if "폴더 만들어" in command:
                return self.execute_tool("drive_create_folder", name="에이전트 폴더")
            
            elif "메일 목록" in command:
                return self.execute_tool("gmail_list_messages", max_results=5)
            
            elif "검색해줘" in command:
                # 간단한 파싱 (실제로는 LLM이 처리)
                query = "name contains '문서'"
                return self.execute_tool("drive_search", query=query)
            
            else:
                return {"success": False, "error": "알 수 없는 명령어"}
    
    # 에이전트 사용
    agent = SimpleAgent(user_id)
    
    print("\n[시뮬레이션] 사용자: '드라이브에 폴더 만들어줘'")
    result = agent.process_command("폴더 만들어")
    print(f"에이전트 응답: {result}")
    
    print("\n[시뮬레이션] 사용자: '메일 목록 보여줘'")
    result = agent.process_command("메일 목록")
    print(f"에이전트 응답: 메일 {result.get('count', 0)}개 조회")
    
    print("\n[시뮬레이션] 사용자: '문서 파일 검색해줘'")
    result = agent.process_command("검색해줘")
    print(f"에이전트 응답: {result.get('count', 0)}개 파일 발견")


def show_available_tools():
    """사용 가능한 모든 tool-call 출력"""
    print("\n" + "=" * 50)
    print("사용 가능한 Tool-calls")
    print("=" * 50)
    
    tools = MCPManager.get_available_tools()
    
    for service, tool_dict in tools.items():
        print(f"\n[{service.upper()}]")
        for tool_name, info in tool_dict.items():
            print(f"\n  {tool_name}")
            print(f"    설명: {info['description']}")
            print(f"    파라미터:")
            for param, desc in info['parameters'].items():
                print(f"      - {param}: {desc}")
            print(f"    반환값: {info['returns']}")


def main():
    """메인 함수"""
    print("\n" + "=" * 50)
    print("MCP 모듈 사용 예제")
    print("=" * 50)
    
    print("\n이 예제는 MCP 모듈의 기능을 시연합니다.")
    print("실제 사용을 위해서는 OAuth 인증이 필요합니다.\n")
    
    # 1. OAuth 인증 플로우
    demo_oauth_flow()
    
    # 2. 사용 가능한 도구 출력
    show_available_tools()
    
    # 실제 API 호출이 필요한 데모들은 주석 처리
    # (인증된 사용자가 있을 때만 활성화)
    
    print("\n" + "=" * 50)
    print("실제 API 호출 데모 (인증 필요)")
    print("=" * 50)
    print("\n다음 함수들의 주석을 해제하여 실제 API를 테스트할 수 있습니다:")
    print("  - demo_google_drive('your_user_id')")
    print("  - demo_gmail('your_user_id')")
    print("  - demo_agent_integration('your_user_id')")
    
    # 인증된 사용자로 테스트하려면 아래 주석 해제
    # user_id = "your_user_id"
    # demo_google_drive(user_id)
    # demo_gmail(user_id)
    # demo_agent_integration(user_id)


if __name__ == "__main__":
    main()

