"""
Chatbot API Endpoints

채팅봇 기능을 제공하는 FastAPI 엔드포인트
- 세션 생성/삭제
- 메시지 전송 및 응답
- 대화 히스토리 조회
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List
from datetime import datetime

from app.domain.chatbot.service import ChatService

router = APIRouter()

# ChatService 싱글톤 인스턴스
chat_service = ChatService()
print("✅ Chatbot ChatService 초기화 완료")


class SessionResponse(BaseModel):
    """세션 생성 응답"""
    session_id: str
    message: str


class MessageRequest(BaseModel):
    """메시지 전송 요청"""
    session_id: str
    message: str


class MessageResponse(BaseModel):
    """메시지 전송 응답"""
    session_id: str
    user_message: str
    assistant_message: str
    timestamp: str


class HistoryResponse(BaseModel):
    """히스토리 조회 응답"""
    session_id: str
    messages: List[dict]
    total_count: int


@router.post("/session", response_model=SessionResponse)
async def create_session():
    """
    새로운 채팅 세션 생성
    
    Returns:
        SessionResponse: 생성된 세션 ID
    """
    try:
        session_id = chat_service.create_session()
        return SessionResponse(
            session_id=session_id,
            message="세션이 생성되었습니다."
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"세션 생성 실패: {str(e)}")


@router.post("/message", response_model=MessageResponse)
async def send_message(request: MessageRequest):
    """
    메시지 전송 및 AI 응답 받기
    
    Args:
        request: 세션 ID와 사용자 메시지
        
    Returns:
        MessageResponse: 사용자 메시지와 AI 응답
    """
    try:
        # 세션 존재 확인
        if not chat_service.session_manager.session_exists(request.session_id):
            raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다.")
        
        # AI 응답 생성
        assistant_message = chat_service.process_message(
            session_id=request.session_id,
            user_message=request.message
        )
        
        return MessageResponse(
            session_id=request.session_id,
            user_message=request.message,
            assistant_message=assistant_message,
            timestamp=datetime.now().isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"메시지 처리 실패: {str(e)}")


@router.get("/history/{session_id}", response_model=HistoryResponse)
async def get_history(session_id: str):
    """
    대화 히스토리 조회
    
    Args:
        session_id: 세션 ID
        
    Returns:
        HistoryResponse: 대화 히스토리 (최대 15개)
    """
    try:
        # 세션 존재 확인
        if not chat_service.session_manager.session_exists(session_id):
            raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다.")
        
        # 히스토리 조회
        history = chat_service.session_manager.get_history(session_id)
        
        return HistoryResponse(
            session_id=session_id,
            messages=history,
            total_count=len(history)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"히스토리 조회 실패: {str(e)}")


@router.delete("/session/{session_id}")
async def delete_session(session_id: str):
    """
    세션 삭제
    
    Args:
        session_id: 삭제할 세션 ID
        
    Returns:
        dict: 삭제 완료 메시지
    """
    try:
        # 세션 존재 확인
        if not chat_service.session_manager.session_exists(session_id):
            raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다.")
        
        # 세션 삭제
        chat_service.session_manager.delete_session(session_id)
        
        return {"message": "세션이 삭제되었습니다.", "session_id": session_id}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"세션 삭제 실패: {str(e)}")


@router.get("/session/{session_id}/info")
async def get_session_info(session_id: str):
    """
    세션 정보 조회 (메타데이터)
    
    Args:
        session_id: 세션 ID
        
    Returns:
        dict: 세션 정보 (생성 시간, 마지막 활동, 메시지 수)
    """
    try:
        # 세션 존재 확인
        if not chat_service.session_manager.session_exists(session_id):
            raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다.")
        
        # 세션 정보 조회
        info = chat_service.session_manager.get_session_info(session_id)
        
        if info is None:
            raise HTTPException(status_code=404, detail="세션 정보를 찾을 수 없습니다.")
        
        return info
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"세션 정보 조회 실패: {str(e)}")

