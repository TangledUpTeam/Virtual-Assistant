from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from urllib.parse import urlencode

from app.infrastructure.database import get_db
from app.domain.auth.service import AuthService
from app.domain.auth.schemas import OAuthCallbackResponse, RefreshTokenRequest, Token
from app.infrastructure.oauth import google_oauth, kakao_oauth, naver_oauth

router = APIRouter()


# ========================================
# Google OAuth
# ========================================

@router.get("/google/login")
async def google_login():
    """
    Google OAuth 로그인 URL 반환
    
    프론트엔드에서 이 URL로 리다이렉트
    """
    authorization_url = google_oauth.get_authorization_url()
    return {"authorization_url": authorization_url}


@router.get("/google/callback")
async def google_callback(
    code: str = Query(..., description="Google Authorization Code"),
    db: Session = Depends(get_db)
):
    """
    Google OAuth 콜백
    
    Google 로그인 후 리다이렉트되는 엔드포인트
    로그인 성공 시 토큰과 함께 로그인 페이지로 리다이렉트
    """
    try:
        # Access Token 받기
        token_data = await google_oauth.get_access_token(code)
        access_token = token_data["access_token"]
        
        # 사용자 정보 가져오기
        user_info = await google_oauth.get_user_info(access_token)
        
        # 로그인 처리 (사용자 조회/생성 + JWT 발급)
        auth_service = AuthService(db)
        result = auth_service.oauth_login(user_info)
        
        # 로그인 페이지로 리다이렉트 (토큰을 쿼리 파라미터로 전달)
        params = {
            'access_token': result.access_token,
            'refresh_token': result.refresh_token,
            'user': result.user.email,
            'name': result.user.name or '',
        }
        redirect_url = f"/start?{urlencode(params)}"
        return RedirectResponse(url=redirect_url)
    
    except Exception as e:
        # 에러 발생 시 로그인 페이지로 리다이렉트 (에러 메시지 포함)
        error_params = {'error': str(e)}
        redirect_url = f"/?{urlencode(error_params)}"
        return RedirectResponse(url=redirect_url)


# ========================================
# Kakao OAuth
# ========================================

@router.get("/kakao/login")
async def kakao_login():
    """Kakao OAuth 로그인 URL 반환"""
    authorization_url = kakao_oauth.get_authorization_url()
    return {"authorization_url": authorization_url}


@router.get("/kakao/callback")
async def kakao_callback(
    code: str = Query(..., description="Kakao Authorization Code"),
    db: Session = Depends(get_db)
):
    """Kakao OAuth 콜백"""
    try:
        # Access Token 받기
        token_data = await kakao_oauth.get_access_token(code)
        access_token = token_data["access_token"]
        
        # 사용자 정보 가져오기
        user_info = await kakao_oauth.get_user_info(access_token)
        
        # 로그인 처리
        auth_service = AuthService(db)
        result = auth_service.oauth_login(user_info)
        
        # 로그인 페이지로 리다이렉트
        params = {
            'access_token': result.access_token,
            'refresh_token': result.refresh_token,
            'user': result.user.email,
            'name': result.user.name or '',
        }
        redirect_url = f"/start?{urlencode(params)}"
        return RedirectResponse(url=redirect_url)
    
    except Exception as e:
        error_params = {'error': str(e)}
        redirect_url = f"/?{urlencode(error_params)}"
        return RedirectResponse(url=redirect_url)


# ========================================
# Naver OAuth
# ========================================

@router.get("/naver/login")
async def naver_login():
    """Naver OAuth 로그인 URL 반환"""
    authorization_url = naver_oauth.get_authorization_url()
    return {"authorization_url": authorization_url}


@router.get("/naver/callback")
async def naver_callback(
    code: str = Query(..., description="Naver Authorization Code"),
    state: str = Query(..., description="CSRF State"),
    db: Session = Depends(get_db)
):
    """Naver OAuth 콜백"""
    try:
        # Access Token 받기
        token_data = await naver_oauth.get_access_token(code, state)
        access_token = token_data["access_token"]
        
        # 사용자 정보 가져오기
        user_info = await naver_oauth.get_user_info(access_token)
        
        # 로그인 처리
        auth_service = AuthService(db)
        result = auth_service.oauth_login(user_info)
        
        # 로그인 페이지로 리다이렉트
        params = {
            'access_token': result.access_token,
            'refresh_token': result.refresh_token,
            'user': result.user.email,
            'name': result.user.name or '',
        }
        redirect_url = f"/start?{urlencode(params)}"
        return RedirectResponse(url=redirect_url)
    
    except Exception as e:
        error_params = {'error': str(e)}
        redirect_url = f"/?{urlencode(error_params)}"
        return RedirectResponse(url=redirect_url)


# ========================================
# Token Refresh
# ========================================

@router.post("/refresh", response_model=Token)
async def refresh_token(
    request: RefreshTokenRequest,
    db: Session = Depends(get_db)
):
    """
    Refresh Token으로 새 Access Token 발급
    """
    auth_service = AuthService(db)
    return auth_service.refresh_access_token(request.refresh_token)
