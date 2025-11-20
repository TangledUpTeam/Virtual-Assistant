"""
Google Drive MCP Server
Tool-call 엔드포인트 제공
"""

from typing import Optional, Dict, Any
from .oauth import GoogleOAuth
from .drive_api import DriveAPI


class GoogleDriveMCPServer:
    """Google Drive MCP 서버"""

    def __init__(self, client_secrets_file: Optional[str] = None):
        """
        Args:
            client_secrets_file: OAuth client secrets 파일 경로
        """
        self.oauth = GoogleOAuth(client_secrets_file)

    def _get_drive_api(self, user_id: str) -> Optional[DriveAPI]:
        """
        DriveAPI 인스턴스 생성
        
        Args:
            user_id: 사용자 ID
            
        Returns:
            DriveAPI 인스턴스 또는 None
        """
        credentials = self.oauth.get_credentials(user_id, service="google_drive")
        if not credentials:
            return None
        return DriveAPI(credentials)

    # ========== Tool-call 함수들 ==========

    def drive_create_folder(
        self,
        user_id: str,
        name: str,
        parent_folder_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        폴더 생성 tool-call
        
        Args:
            user_id: 사용자 ID
            name: 폴더 이름
            parent_folder_id: 부모 폴더 ID
            
        Returns:
            {"folder_id": str, "success": bool}
        """
        api = self._get_drive_api(user_id)
        if not api:
            return {
                "success": False,
                "error": "인증되지 않은 사용자입니다. OAuth 인증이 필요합니다."
            }
        
        return api.create_folder(name, parent_folder_id)

    def drive_upload_file(
        self,
        user_id: str,
        local_path: str,
        folder_id: Optional[str] = None,
        filename: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        파일 업로드 tool-call
        
        Args:
            user_id: 사용자 ID
            local_path: 로컬 파일 경로
            folder_id: 업로드할 폴더 ID
            filename: 저장할 파일명
            
        Returns:
            {"file_id": str, "success": bool}
        """
        api = self._get_drive_api(user_id)
        if not api:
            return {
                "success": False,
                "error": "인증되지 않은 사용자입니다. OAuth 인증이 필요합니다."
            }
        
        return api.upload_file(local_path, folder_id, filename)

    def drive_download_file(
        self,
        user_id: str,
        file_id: str
    ) -> Dict[str, Any]:
        """
        파일 다운로드 tool-call
        
        Args:
            user_id: 사용자 ID
            file_id: 다운로드할 파일 ID
            
        Returns:
            {"filename": str, "data": str (base64), "success": bool}
        """
        api = self._get_drive_api(user_id)
        if not api:
            return {
                "success": False,
                "error": "인증되지 않은 사용자입니다. OAuth 인증이 필요합니다."
            }
        
        return api.download_file(file_id)

    def drive_search(
        self,
        user_id: str,
        query: str,
        max_results: int = 10
    ) -> Dict[str, Any]:
        """
        파일 검색 tool-call
        
        Args:
            user_id: 사용자 ID
            query: 검색 쿼리
            max_results: 최대 결과 수
            
        Returns:
            {"files": List[dict], "success": bool}
        """
        api = self._get_drive_api(user_id)
        if not api:
            return {
                "success": False,
                "error": "인증되지 않은 사용자입니다. OAuth 인증이 필요합니다."
            }
        
        return api.search_files(query, max_results)

    def drive_read(
        self,
        user_id: str,
        file_id: str
    ) -> Dict[str, Any]:
        """
        파일 읽기 tool-call (바이너리, base64)
        
        Args:
            user_id: 사용자 ID
            file_id: 읽을 파일 ID
            
        Returns:
            {"data": str (base64), "success": bool}
        """
        api = self._get_drive_api(user_id)
        if not api:
            return {
                "success": False,
                "error": "인증되지 않은 사용자입니다. OAuth 인증이 필요합니다."
            }
        
        return api.read_file(file_id)

    def drive_list_files(
        self,
        user_id: str,
        folder_id: Optional[str] = None,
        max_results: int = 20
    ) -> Dict[str, Any]:
        """
        파일 목록 조회 tool-call
        
        Args:
            user_id: 사용자 ID
            folder_id: 폴더 ID
            max_results: 최대 결과 수
            
        Returns:
            {"files": List[dict], "success": bool}
        """
        api = self._get_drive_api(user_id)
        if not api:
            return {
                "success": False,
                "error": "인증되지 않은 사용자입니다. OAuth 인증이 필요합니다."
            }
        
        return api.list_files(folder_id, max_results)

    def drive_delete_file(
        self,
        user_id: str,
        file_id: str
    ) -> Dict[str, Any]:
        """
        파일 삭제 tool-call
        
        Args:
            user_id: 사용자 ID
            file_id: 삭제할 파일 ID
            
        Returns:
            {"success": bool}
        """
        api = self._get_drive_api(user_id)
        if not api:
            return {
                "success": False,
                "error": "인증되지 않은 사용자입니다. OAuth 인증이 필요합니다."
            }
        
        return api.delete_file(file_id)

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
        success = self.oauth.exchange_code_for_token(code, user_id, "google_drive", redirect_uri)
        return {"success": success}

    def revoke_user_access(self, user_id: str) -> Dict[str, Any]:
        """
        사용자 액세스 취소
        
        Args:
            user_id: 사용자 ID
            
        Returns:
            {"success": bool}
        """
        success = self.oauth.revoke_token(user_id, "google_drive")
        return {"success": success}

