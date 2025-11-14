from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.infrastructure.database import get_db
from app.domain.user.models import User

# Bearer Token 스킴
security = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    현재 인증된 사용자 가져오기
    
    FastAPI 엔드포인트에서 사용:
    @app.get("/me")
    def get_me(current_user: User = Depends(get_current_user)):
        return current_user
    
    Args:
        credentials: Bearer Token
        db: 데이터베이스 세션
    
    Returns:
        User 객체
    
    Raises:
        HTTPException: 인증 실패 시
    """
    # Circular import 방지를 위해 함수 안에서 import
    from app.domain.auth.service import AuthService
    from app.domain.user.service import UserService
    
    token = credentials.credentials
    
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
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User | None:
    """
    현재 사용자 가져오기 (Optional)
    
    토큰이 없거나 유효하지 않아도 예외를 발생시키지 않음
    
    Returns:
        User 객체 또는 None
    """
    try:
        return get_current_user(credentials, db)
    except HTTPException:
        return None
