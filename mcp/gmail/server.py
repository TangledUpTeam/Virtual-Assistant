"""
Gmail MCP Server
Tool-call 엔드포인트 제공
"""

from typing import Optional, Dict, Any, List
from .oauth import GoogleOAuth
from .gmail_api import GmailAPI


class GmailMCPServer:
    """Gmail MCP 서버"""

    def __init__(self, client_secrets_file: Optional[str] = None):
        """
        Args:
            client_secrets_file: OAuth client secrets 파일 경로
        """
        self.oauth = GoogleOAuth(client_secrets_file)

    def _get_gmail_api(self, user_id: str) -> Optional[GmailAPI]:
        """
        GmailAPI 인스턴스 생성
        
        Args:
            user_id: 사용자 ID
            
        Returns:
            GmailAPI 인스턴스 또는 None
        """
        credentials = self.oauth.get_credentials(user_id, service="gmail")
        if not credentials:
            return None
        return GmailAPI(credentials)

    # ========== Tool-call 함수들 ==========

    def gmail_send_email(
        self,
        user_id: str,
        to: str,
        subject: str,
        body: str,
        attachment_base64: Optional[str] = None,
        attachment_filename: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        이메일 보내기 tool-call
        
        Args:
            user_id: 사용자 ID
            to: 수신자 이메일
            subject: 제목
            body: 본문
            attachment_base64: 첨부 파일 (base64)
            attachment_filename: 첨부 파일 이름
            
        Returns:
            {"success": bool, "message_id": str}
        """
        api = self._get_gmail_api(user_id)
        if not api:
            return {
                "success": False,
                "error": "인증되지 않은 사용자입니다. OAuth 인증이 필요합니다."
            }
        
        return api.send_email(to, subject, body, attachment_base64, attachment_filename)

    def gmail_list_messages(
        self,
        user_id: str,
        query: Optional[str] = None,
        max_results: int = 10,
        label_ids: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        받은 메일 목록 조회 tool-call
        
        Args:
            user_id: 사용자 ID
            query: 검색 쿼리
            max_results: 최대 결과 수
            label_ids: 레이블 ID 목록
            
        Returns:
            {"messages": List[dict], "success": bool}
        """
        api = self._get_gmail_api(user_id)
        if not api:
            return {
                "success": False,
                "error": "인증되지 않은 사용자입니다. OAuth 인증이 필요합니다."
            }
        
        return api.list_messages(query, max_results, label_ids)

    def gmail_get_message(
        self,
        user_id: str,
        message_id: str
    ) -> Dict[str, Any]:
        """
        메시지 상세 조회 tool-call
        
        Args:
            user_id: 사용자 ID
            message_id: 메시지 ID
            
        Returns:
            {"id": str, "from": str, "to": str, "subject": str, "body": str, "attachments": List}
        """
        api = self._get_gmail_api(user_id)
        if not api:
            return {
                "success": False,
                "error": "인증되지 않은 사용자입니다. OAuth 인증이 필요합니다."
            }
        
        return api.get_message(message_id)

    def gmail_create_draft(
        self,
        user_id: str,
        to: str,
        subject: str,
        body: str,
        attachment_base64: Optional[str] = None,
        attachment_filename: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        초안 생성 tool-call
        
        Args:
            user_id: 사용자 ID
            to: 수신자 이메일
            subject: 제목
            body: 본문
            attachment_base64: 첨부 파일 (base64)
            attachment_filename: 첨부 파일 이름
            
        Returns:
            {"draft_id": str, "success": bool}
        """
        api = self._get_gmail_api(user_id)
        if not api:
            return {
                "success": False,
                "error": "인증되지 않은 사용자입니다. OAuth 인증이 필요합니다."
            }
        
        return api.create_draft(to, subject, body, attachment_base64, attachment_filename)

    def gmail_delete_message(
        self,
        user_id: str,
        message_id: str
    ) -> Dict[str, Any]:
        """
        메시지 삭제 tool-call
        
        Args:
            user_id: 사용자 ID
            message_id: 메시지 ID
            
        Returns:
            {"success": bool}
        """
        api = self._get_gmail_api(user_id)
        if not api:
            return {
                "success": False,
                "error": "인증되지 않은 사용자입니다. OAuth 인증이 필요합니다."
            }
        
        return api.delete_message(message_id)

    def gmail_mark_as_read(
        self,
        user_id: str,
        message_id: str
    ) -> Dict[str, Any]:
        """
        메시지를 읽음으로 표시 tool-call
        
        Args:
            user_id: 사용자 ID
            message_id: 메시지 ID
            
        Returns:
            {"success": bool}
        """
        api = self._get_gmail_api(user_id)
        if not api:
            return {
                "success": False,
                "error": "인증되지 않은 사용자입니다. OAuth 인증이 필요합니다."
            }
        
        return api.mark_as_read(message_id)

    def gmail_mark_as_unread(
        self,
        user_id: str,
        message_id: str
    ) -> Dict[str, Any]:
        """
        메시지를 읽지 않음으로 표시 tool-call
        
        Args:
            user_id: 사용자 ID
            message_id: 메시지 ID
            
        Returns:
            {"success": bool}
        """
        api = self._get_gmail_api(user_id)
        if not api:
            return {
                "success": False,
                "error": "인증되지 않은 사용자입니다. OAuth 인증이 필요합니다."
            }
        
        return api.mark_as_unread(message_id)

    # ========== OAuth 관련 함수들 ==========

    def get_authorization_url(self, redirect_uri: str = "urn:ietf:wg:oauth:2.0:oob") -> str:
        """
        OAuth 인증 URL 생성
        
        Args:
            redirect_uri: 리다이렉트 URI
            
        Returns:
            인증 URL
        """
        return self.oauth.get_authorization_url(redirect_uri)

    def authorize_user(
        self,
        code: str,
        user_id: str,
        redirect_uri: str = "urn:ietf:wg:oauth:2.0:oob"
    ) -> Dict[str, Any]:
        """
        사용자 인증 (인증 코드 -> 토큰 교환)
        
        Args:
            code: OAuth 인증 코드
            user_id: 사용자 ID
            redirect_uri: 리다이렉트 URI
            
        Returns:
            {"success": bool}
        """
        success = self.oauth.exchange_code_for_token(code, user_id, "gmail", redirect_uri)
        return {"success": success}

    def revoke_user_access(self, user_id: str) -> Dict[str, Any]:
        """
        사용자 액세스 취소
        
        Args:
            user_id: 사용자 ID
            
        Returns:
            {"success": bool}
        """
        success = self.oauth.revoke_token(user_id, "gmail")
        return {"success": success}

