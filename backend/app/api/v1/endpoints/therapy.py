"""
심리 상담 API Endpoints

아들러 개인심리학 기반 RAG 상담 시스템
- 사용자 입력을 받아 심리 상담 응답 생성
- Vector DB 기반 관련 자료 검색
- 아들러 페르소나 적용
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional

from app.domain.therapy.service import TherapyService

router = APIRouter()

# TherapyService 싱글톤 인스턴스
therapy_service = TherapyService()

# 심리 상담 요청 클래스
class TherapyRequest(BaseModel):
    message: str
    enable_scoring: Optional[bool] = True  # 답변 품질 스코어링 활성화 (기본값: True)

# 심리 상담 응답 클래스
class TherapyResponse(BaseModel):
    answer: str
    mode: str
    used_chunks: List[str]
    continue_conversation: bool 

# 심리 상담 채팅 엔드포인트
@router.post("/chat", response_model=TherapyResponse)
async def chat_therapy(request: TherapyRequest):

    try:
        # 서비스 사용 가능 여부 확인
        if not therapy_service.is_available():
            raise HTTPException(
                status_code=503, 
                detail="심리 상담 시스템이 현재 사용 불가능합니다. Vector DB를 확인해주세요."
            )
        
        # 상담 진행 (스코어링 옵션 전달)
        response = therapy_service.chat(
            request.message, 
            enable_scoring=request.enable_scoring
        )
        
        return TherapyResponse(
            answer=response["answer"],
            mode=response["mode"],
            used_chunks=response.get("used_chunks", []),
            continue_conversation=response.get("continue_conversation", True)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"상담 처리 중 오류가 발생했습니다: {str(e)}"
        )

# 심리 상담 시스템 확인 엔드포인트
@router.get("/status")
async def get_therapy_status():

    return {
        "available": therapy_service.is_available(),
        "system": "RAG 기반 아들러 심리 상담",
        "persona": "Alfred Adler (개인심리학)"
    }