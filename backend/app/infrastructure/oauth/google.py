from typing import Optional
from authlib.integrations.httpx_client import AsyncOAuth2Client
import httpx

from app.core.config import settings
from app.domain.auth.schemas import OAuthUserInfo


class GoogleOAuthClient:
    """Google OAuth 클라이언트"""
    
    AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
    TOKEN_URL = "https://oauth2.googleapis.com/token"
    USER_INFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"
    
    def __init__(self):
        self.client_id = settings.GOOGLE_CLIENT_ID
        self.client_secret = settings.GOOGLE_CLIENT_SECRET
        self.redirect_uri = settings.GOOGLE_REDIRECT_URI
    
    def get_authorization_url(self, state: Optional[str] = None) -> str:
        """
        Google OAuth 로그인 URL 생성
        
        Returns:
            Google 로그인 페이지 URL
        """
            client_id=self.client_id,
            redirect_uri=self.redirect_uri,
            scope="openid email profile https://www.googleapis.com/auth/gmail.send https://www.googleapis.com/auth/gmail.readonly https://www.googleapis.com/auth/drive"
        )
        
        # access_type='offline'로 Refresh Token 받기
        # prompt='select_account'로 계정 선택 화면만 표시 (권한은 첫 로그인 시에만)
        import secrets
        url, _ = client.create_authorization_url(
            self.AUTHORIZE_URL,
            state=state or secrets.token_urlsafe(16),
            access_type="offline",  # Refresh Token 받기
            prompt="select_account",  # 계정 선택 화면만 표시
            include_granted_scopes="true"  # 기존 권한 포함
        )
        
        return url
    
    async def get_access_token(self, code: str) -> dict:
        """
        Authorization Code로 Access Token 받기
        
        Args:
            code: Google에서 받은 Authorization Code
        
        Returns:
            토큰 정보 dict
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.TOKEN_URL,
                data={
                    "code": code,
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "redirect_uri": self.redirect_uri,
                    "grant_type": "authorization_code"
                }
            )
            response.raise_for_status()
            return response.json()
    
    async def get_user_info(self, access_token: str) -> OAuthUserInfo:
        """
        Access Token으로 사용자 정보 가져오기
        
        Args:
            access_token: Google Access Token
        
        Returns:
            OAuthUserInfo 객체
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                self.USER_INFO_URL,
                headers={"Authorization": f"Bearer {access_token}"}
            )
            response.raise_for_status()
            data = response.json()
            
            return OAuthUserInfo(
                email=data["email"],
                name=data.get("name"),
                profile_image=data.get("picture"),
                oauth_id=data["id"],
                oauth_provider="google"
            )


# 싱글톤 인스턴스
google_oauth = GoogleOAuthClient()
