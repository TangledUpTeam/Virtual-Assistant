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
print("✅ Therapy Service 초기화 완료")


class TherapyRequest(BaseModel):
    """심리 상담 요청"""
    message: str


class TherapyResponse(BaseModel):
    """심리 상담 응답"""
    answer: str
    mode: str
    used_chunks: List[str]
    continue_conversation: bool


@router.post("/chat", response_model=TherapyResponse)
async def chat_therapy(request: TherapyRequest):
    """
    심리 상담 채팅
    
    Args:
        request: 사용자 메시지
        
    Returns:
        TherapyResponse: 상담사 응답
    """
    try:
        # 서비스 사용 가능 여부 확인
        if not therapy_service.is_available():
            raise HTTPException(
                status_code=503, 
                detail="심리 상담 시스템이 현재 사용 불가능합니다. Vector DB를 확인해주세요."
            )
        
        # 상담 진행
        response = therapy_service.chat(request.message)
        
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


@router.get("/status")
async def get_therapy_status():
    """
    심리 상담 시스템 상태 확인
    
    Returns:
        dict: 시스템 상태 정보
    """
    return {
        "available": therapy_service.is_available(),
        "system": "RAG 기반 아들러 심리 상담",
        "persona": "Alfred Adler (개인심리학)"
    }

