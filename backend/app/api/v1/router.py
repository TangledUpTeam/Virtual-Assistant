from fastapi import APIRouter
from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.users import router as users_router
from app.api.v1.endpoints.reports import router as reports_router
from app.api.v1.endpoints.plan import router as plan_router
from app.api.v1.endpoints.daily import router as daily_router
from app.api.v1.endpoints.rag import router as rag_router

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

# Plan 엔드포인트
api_router.include_router(
    plan_router,
    tags=["Plan"]
)

# Daily 엔드포인트
api_router.include_router(
    daily_router,
    tags=["Daily"]
)

# RAG 엔드포인트
api_router.include_router(
    rag_router,
    prefix="/rag",
    tags=["RAG"]
)
