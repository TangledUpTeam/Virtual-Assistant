"""
Google OAuth 핸들러 (Gmail용)
"""

import os
from typing import Optional, Dict, Any
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request

# MCP 토큰 저장소 import
import sys
from pathlib import Path
mcp_root = Path(__file__).parent.parent
sys.path.insert(0, str(mcp_root))
from token_storage import TokenStore


class GoogleOAuth:
    """Google OAuth 인증 핸들러"""

    # Gmail에 필요한 scope
    SCOPES = [
        'https://www.googleapis.com/auth/gmail.send',
        'https://www.googleapis.com/auth/gmail.readonly',
        'https://www.googleapis.com/auth/gmail.compose',
        'https://www.googleapis.com/auth/gmail.modify'
    ]

    def __init__(self, client_secrets_file: Optional[str] = None):
        """
        Args:
            client_secrets_file: Google OAuth client secrets JSON 파일 경로
        """
        if client_secrets_file is None:
            # 기본 경로: mcp/gmail/client_secrets.json
            client_secrets_file = os.path.join(
                os.path.dirname(__file__), "client_secrets.json"
            )
        
        self.client_secrets_file = client_secrets_file
        self.token_store = TokenStore()

    def get_authorization_url(self, redirect_uri: str = "urn:ietf:wg:oauth:2.0:oob") -> str:
        """
        OAuth 인증 URL 생성
        
        Args:
            redirect_uri: 리다이렉트 URI
            
        Returns:
            인증 URL
        """
        flow = Flow.from_client_secrets_file(
            self.client_secrets_file,
            scopes=self.SCOPES,
            redirect_uri=redirect_uri
        )
        
        auth_url, _ = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent'
        )
        
        return auth_url

    def exchange_code_for_token(
        self,
        code: str,
        user_id: str,
        service: str = "gmail",
        redirect_uri: str = "urn:ietf:wg:oauth:2.0:oob"
    ) -> bool:
        """
        인증 코드를 토큰으로 교환하고 저장
        
        Args:
            code: OAuth 인증 코드
            user_id: 사용자 ID
            service: 서비스 이름
            redirect_uri: 리다이렉트 URI
            
        Returns:
            성공 여부
        """
        try:
            flow = Flow.from_client_secrets_file(
                self.client_secrets_file,
                scopes=self.SCOPES,
                redirect_uri=redirect_uri
            )
            
            flow.fetch_token(code=code)
            credentials = flow.credentials
            
            # 토큰 데이터 저장
            token_data = {
                'token': credentials.token,
                'refresh_token': credentials.refresh_token,
                'token_uri': credentials.token_uri,
                'client_id': credentials.client_id,
                'client_secret': credentials.client_secret,
                'scopes': credentials.scopes,
                'expiry': credentials.expiry.isoformat() if credentials.expiry else None
            }
            
            return self.token_store.save_token(user_id, service, token_data)
        
        except Exception as e:
            print(f"토큰 교환 실패: {e}")
            return False

    def get_credentials(self, user_id: str, service: str = "gmail") -> Optional[Credentials]:
        """
        저장된 토큰으로 Credentials 객체 생성
        
        Args:
            user_id: 사용자 ID
            service: 서비스 이름
            
        Returns:
            Credentials 객체 또는 None
        """
        token_data = self.token_store.load_token(user_id, service)
        if not token_data:
            return None
        
        try:
            credentials = Credentials(
                token=token_data.get('token'),
                refresh_token=token_data.get('refresh_token'),
                token_uri=token_data.get('token_uri'),
                client_id=token_data.get('client_id'),
                client_secret=token_data.get('client_secret'),
                scopes=token_data.get('scopes')
            )
            
            # 토큰 갱신 필요 시 자동 갱신
            if credentials.expired and credentials.refresh_token:
                credentials.refresh(Request())
                
                # 갱신된 토큰 저장
                token_data['token'] = credentials.token
                if credentials.expiry:
                    token_data['expiry'] = credentials.expiry.isoformat()
                self.token_store.save_token(user_id, service, token_data)
            
            return credentials
        
        except Exception as e:
            print(f"Credentials 생성 실패: {e}")
            return None

    def revoke_token(self, user_id: str, service: str = "gmail") -> bool:
        """
        토큰 취소 및 삭제
        
        Args:
            user_id: 사용자 ID
            service: 서비스 이름
            
        Returns:
            성공 여부
        """
        credentials = self.get_credentials(user_id, service)
        if credentials:
            try:
                credentials.revoke(Request())
            except Exception as e:
                print(f"토큰 취소 실패: {e}")
        
        return self.token_store.delete_token(user_id, service)

