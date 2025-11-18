from fastapi import APIRouter
from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.users import router as users_router
from app.api.v1.endpoints.reports import router as reports_router

api_router = APIRouter()

# Auth 엔드포인트
api_router.include_router(
    auth_router,
    prefix="/auth",
    tags=["Authentication"]
)

# Users 엔드포인트
api_router.include_router(
    users_router,
    prefix="/users",
    tags=["Users"]
)

# Reports 엔드포인트
api_router.include_router(
    reports_router,
    tags=["Reports"]
)
