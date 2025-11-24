from fastapi import Depends, HTTPException, status, Request, Cookie
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Optional

from app.infrastructure.database import get_db
from app.domain.user.models import User

# Bearer Token 스킴 (Optional로 변경)
security = HTTPBearer(auto_error=False)


def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    access_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
) -> User:
    """
    현재 인증된 사용자 가져오기
    
    토큰을 다음 순서로 확인:
    1. Authorization 헤더 (Bearer Token)
    2. 쿠키 (access_token)
    
    FastAPI 엔드포인트에서 사용:
    @app.get("/me")
    def get_me(current_user: User = Depends(get_current_user)):
        return current_user
    
    Args:
        request: FastAPI Request 객체
        credentials: Bearer Token (Optional)
        access_token: 쿠키의 access_token (Optional)
        db: 데이터베이스 세션
    
    Returns:
        User 객체
    
    Raises:
        HTTPException: 인증 실패 시
    """
    # Circular import 방지를 위해 함수 안에서 import
    from app.domain.auth.service import AuthService
    from app.domain.user.service import UserService
    
    # 토큰 추출 (Authorization 헤더 우선, 없으면 쿠키)
    token = None
    if credentials:
        token = credentials.credentials
    elif access_token:
        token = access_token
    
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 토큰에서 사용자 ID 추출
    auth_service = AuthService(db)
    user_id = auth_service.get_current_user_id(token)
    
    # 사용자 조회
    user_service = UserService(db)
    user = user_service.get_user_by_id(user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return user


def get_current_user_optional(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    access_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
) -> User | None:
    """
    현재 사용자 가져오기 (Optional)
    
    토큰이 없거나 유효하지 않아도 예외를 발생시키지 않음
    
    Returns:
        User 객체 또는 None
    """
    try:
        return get_current_user(request, credentials, access_token, db)
    except Exception as e:
        # 모든 예외를 잡아서 None 반환 (게스트 모드)
        print(f"ℹ️  사용자 인증 실패 (게스트 모드): {type(e).__name__}")
        return None
