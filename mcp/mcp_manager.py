"""
MCP Manager
모든 MCP 서버를 통합 관리하는 매니저
"""

from typing import Optional, Dict, Any
from .google_drive.server import GoogleDriveMCPServer
from .gmail.server import GmailMCPServer


class MCPManager:
    """
    MCP 통합 관리자
    에이전트가 tool-call로 사용할 수 있는 통합 인터페이스
    """

    def __init__(
        self,
        drive_client_secrets: Optional[str] = None,
        gmail_client_secrets: Optional[str] = None
    ):
        """
        Args:
            drive_client_secrets: Google Drive OAuth client secrets 파일 경로
            gmail_client_secrets: Gmail OAuth client secrets 파일 경로
        """
        self.drive_server = GoogleDriveMCPServer(drive_client_secrets)
        self.gmail_server = GmailMCPServer(gmail_client_secrets)

    # ========== Google Drive Tool-calls ==========

    def drive_create_folder(
        self,
        user_id: str,
        name: str,
        parent_folder_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """폴더 생성"""
        return self.drive_server.drive_create_folder(user_id, name, parent_folder_id)

    def drive_upload_file(
        self,
        user_id: str,
        local_path: str,
        folder_id: Optional[str] = None,
        filename: Optional[str] = None
    ) -> Dict[str, Any]:
        """파일 업로드"""
        return self.drive_server.drive_upload_file(user_id, local_path, folder_id, filename)

    def drive_download_file(self, user_id: str, file_id: str) -> Dict[str, Any]:
        """파일 다운로드"""
        return self.drive_server.drive_download_file(user_id, file_id)

    def drive_search(
        self,
        user_id: str,
        query: str,
        max_results: int = 10
    ) -> Dict[str, Any]:
        """파일 검색"""
        return self.drive_server.drive_search(user_id, query, max_results)

    def drive_read(self, user_id: str, file_id: str) -> Dict[str, Any]:
        """파일 읽기"""
        return self.drive_server.drive_read(user_id, file_id)

    def drive_list_files(
        self,
        user_id: str,
        folder_id: Optional[str] = None,
        max_results: int = 20
    ) -> Dict[str, Any]:
        """파일 목록 조회"""
        return self.drive_server.drive_list_files(user_id, folder_id, max_results)

    def drive_delete_file(self, user_id: str, file_id: str) -> Dict[str, Any]:
        """파일 삭제"""
        return self.drive_server.drive_delete_file(user_id, file_id)

    # ========== Gmail Tool-calls ==========

    def gmail_send_email(
        self,
        user_id: str,
        to: str,
        subject: str,
        body: str,
        attachment_base64: Optional[str] = None,
        attachment_filename: Optional[str] = None
    ) -> Dict[str, Any]:
        """이메일 보내기"""
        return self.gmail_server.gmail_send_email(
            user_id, to, subject, body, attachment_base64, attachment_filename
        )

    def gmail_list_messages(
        self,
        user_id: str,
        query: Optional[str] = None,
        max_results: int = 10
    ) -> Dict[str, Any]:
        """받은 메일 목록 조회"""
        return self.gmail_server.gmail_list_messages(user_id, query, max_results)

    def gmail_get_message(self, user_id: str, message_id: str) -> Dict[str, Any]:
        """메시지 상세 조회"""
        return self.gmail_server.gmail_get_message(user_id, message_id)

    def gmail_create_draft(
        self,
        user_id: str,
        to: str,
        subject: str,
        body: str,
        attachment_base64: Optional[str] = None,
        attachment_filename: Optional[str] = None
    ) -> Dict[str, Any]:
        """초안 생성"""
        return self.gmail_server.gmail_create_draft(
            user_id, to, subject, body, attachment_base64, attachment_filename
        )

    def gmail_delete_message(self, user_id: str, message_id: str) -> Dict[str, Any]:
        """메시지 삭제"""
        return self.gmail_server.gmail_delete_message(user_id, message_id)

    def gmail_mark_as_read(self, user_id: str, message_id: str) -> Dict[str, Any]:
        """메시지를 읽음으로 표시"""
        return self.gmail_server.gmail_mark_as_read(user_id, message_id)

    def gmail_mark_as_unread(self, user_id: str, message_id: str) -> Dict[str, Any]:
        """메시지를 읽지 않음으로 표시"""
        return self.gmail_server.gmail_mark_as_unread(user_id, message_id)

    # ========== OAuth 관련 ==========

    def get_drive_auth_url(self, redirect_uri: str = "urn:ietf:wg:oauth:2.0:oob") -> str:
        """Google Drive OAuth 인증 URL 생성"""
        return self.drive_server.get_authorization_url(redirect_uri)

    def get_gmail_auth_url(self, redirect_uri: str = "urn:ietf:wg:oauth:2.0:oob") -> str:
        """Gmail OAuth 인증 URL 생성"""
        return self.gmail_server.get_authorization_url(redirect_uri)

    def authorize_drive_user(
        self,
        code: str,
        user_id: str,
        redirect_uri: str = "urn:ietf:wg:oauth:2.0:oob"
    ) -> Dict[str, Any]:
        """Google Drive 사용자 인증"""
        return self.drive_server.authorize_user(code, user_id, redirect_uri)

    def authorize_gmail_user(
        self,
        code: str,
        user_id: str,
        redirect_uri: str = "urn:ietf:wg:oauth:2.0:oob"
    ) -> Dict[str, Any]:
        """Gmail 사용자 인증"""
        return self.gmail_server.authorize_user(code, user_id, redirect_uri)

    def revoke_drive_access(self, user_id: str) -> Dict[str, Any]:
        """Google Drive 액세스 취소"""
        return self.drive_server.revoke_user_access(user_id)

    def revoke_gmail_access(self, user_id: str) -> Dict[str, Any]:
        """Gmail 액세스 취소"""
        return self.gmail_server.revoke_user_access(user_id)

    # ========== Tool-call 메타데이터 (에이전트용) ==========

    @staticmethod
    def get_available_tools() -> Dict[str, Any]:
        """
        사용 가능한 모든 tool-call 목록과 스키마 반환
        에이전트가 참조할 수 있는 도구 목록
        """
        return {
            "google_drive": {
                "drive_create_folder": {
                    "description": "Google Drive에 폴더 생성",
                    "parameters": {
                        "user_id": "str - 사용자 ID",
                        "name": "str - 폴더 이름",
                        "parent_folder_id": "Optional[str] - 부모 폴더 ID"
                    },
                    "returns": {"folder_id": "str", "success": "bool"}
                },
                "drive_upload_file": {
                    "description": "Google Drive에 파일 업로드",
                    "parameters": {
                        "user_id": "str - 사용자 ID",
                        "local_path": "str - 로컬 파일 경로",
                        "folder_id": "Optional[str] - 업로드할 폴더 ID",
                        "filename": "Optional[str] - 저장할 파일명"
                    },
                    "returns": {"file_id": "str", "success": "bool"}
                },
                "drive_download_file": {
                    "description": "Google Drive에서 파일 다운로드",
                    "parameters": {
                        "user_id": "str - 사용자 ID",
                        "file_id": "str - 파일 ID"
                    },
                    "returns": {"filename": "str", "data": "str (base64)", "success": "bool"}
                },
                "drive_search": {
                    "description": "Google Drive에서 파일 검색",
                    "parameters": {
                        "user_id": "str - 사용자 ID",
                        "query": "str - 검색 쿼리",
                        "max_results": "int - 최대 결과 수"
                    },
                    "returns": {"files": "List[dict]", "success": "bool"}
                },
                "drive_read": {
                    "description": "Google Drive 파일 읽기 (바이너리, base64)",
                    "parameters": {
                        "user_id": "str - 사용자 ID",
                        "file_id": "str - 파일 ID"
                    },
                    "returns": {"data": "str (base64)", "success": "bool"}
                }
            },
            "gmail": {
                "gmail_send_email": {
                    "description": "Gmail로 이메일 보내기",
                    "parameters": {
                        "user_id": "str - 사용자 ID",
                        "to": "str - 수신자 이메일",
                        "subject": "str - 제목",
                        "body": "str - 본문",
                        "attachment_base64": "Optional[str] - 첨부 파일 (base64)",
                        "attachment_filename": "Optional[str] - 첨부 파일 이름"
                    },
                    "returns": {"success": "bool", "message_id": "str"}
                },
                "gmail_list_messages": {
                    "description": "받은 메일 목록 조회",
                    "parameters": {
                        "user_id": "str - 사용자 ID",
                        "query": "Optional[str] - 검색 쿼리",
                        "max_results": "int - 최대 결과 수"
                    },
                    "returns": {"messages": "List[dict]", "success": "bool"}
                },
                "gmail_get_message": {
                    "description": "메시지 상세 조회",
                    "parameters": {
                        "user_id": "str - 사용자 ID",
                        "message_id": "str - 메시지 ID"
                    },
                    "returns": {
                        "id": "str",
                        "from": "str",
                        "to": "str",
                        "subject": "str",
                        "body": "str",
                        "attachments": "List[dict]",
                        "success": "bool"
                    }
                },
                "gmail_create_draft": {
                    "description": "Gmail 초안 생성",
                    "parameters": {
                        "user_id": "str - 사용자 ID",
                        "to": "str - 수신자 이메일",
                        "subject": "str - 제목",
                        "body": "str - 본문",
                        "attachment_base64": "Optional[str] - 첨부 파일 (base64)",
                        "attachment_filename": "Optional[str] - 첨부 파일 이름"
                    },
                    "returns": {"draft_id": "str", "success": "bool"}
                }
            }
        }

