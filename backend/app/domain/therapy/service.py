"""
심리 상담 서비스
생성날짜: 2025.11.24
설명: RAG 기반 아들러 심리 상담 시스템 서비스 레이어
"""

import sys
from pathlib import Path
from typing import Dict, Any, Optional

# councel 디렉토리를 Python 경로에 추가
COUNCEL_DIR = Path(__file__).parent.parent.parent.parent / "councel"
sys.path.insert(0, str(COUNCEL_DIR))

from sourcecode.persona.rag_therapy import RAGTherapySystem


class TherapyService:
    """
    심리 상담 서비스 (싱글톤)
    
    RAGTherapySystem을 래핑하여 FastAPI 엔드포인트에서 사용할 수 있도록 합니다.
    """
    
    _instance: Optional['TherapyService'] = None
    _rag_system: Optional[RAGTherapySystem] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """서비스 초기화"""
        if self._rag_system is None:
            # Vector DB 경로 설정
            base_dir = Path(__file__).parent.parent.parent.parent
            vector_db_dir = base_dir / "councel" / "vector_db"
            
            try:
                # RAG 상담 시스템 초기화
                self._rag_system = RAGTherapySystem(str(vector_db_dir))
                print("✅ RAG 심리 상담 시스템 초기화 완료")
            except Exception as e:
                print(f"⚠️  RAG 심리 상담 시스템 초기화 실패: {e}")
                self._rag_system = None
    
    def is_available(self) -> bool:
        """
        상담 시스템 사용 가능 여부 확인
        
        Returns:
            bool: 사용 가능 여부
        """
        return self._rag_system is not None
    
    def chat(self, user_input: str) -> Dict[str, Any]:
        """
        사용자 입력을 받아 상담 응답 생성
        
        Args:
            user_input: 사용자 입력 메시지
            
        Returns:
            Dict[str, Any]: {
                "answer": str,
                "used_chunks": List[str],
                "mode": str,
                "continue_conversation": bool
            }
        """
        if not self.is_available():
            return {
                "answer": "죄송합니다. 심리 상담 시스템이 현재 사용 불가능합니다.",
                "used_chunks": [],
                "mode": "error",
                "continue_conversation": False
            }
        
        try:
            # RAG 시스템으로 상담 진행
            response = self._rag_system.chat(user_input)
            return response
        except Exception as e:
            print(f"❌ 상담 처리 중 오류: {e}")
            return {
                "answer": f"죄송합니다. 상담 처리 중 오류가 발생했습니다: {str(e)}",
                "used_chunks": [],
                "mode": "error",
                "continue_conversation": True
            }

