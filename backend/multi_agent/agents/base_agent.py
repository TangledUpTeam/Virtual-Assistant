"""
Base Agent 클래스

모든 전문 에이전트의 기본 클래스
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class BaseAgent(ABC):
    """
    모든 전문 에이전트의 기본 클래스
    
    각 전문 에이전트는 이 클래스를 상속받아 구현합니다.
    """
    
    def __init__(self, name: str, description: str):
        """
        초기화
        
        Args:
            name: 에이전트 이름
            description: 에이전트 설명
        """
        self.name = name
        self.description = description
    
    @abstractmethod
    async def process(self, query: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        질문 처리 (추상 메서드)
        
        Args:
            query: 사용자 질문
            context: 추가 컨텍스트 (세션 ID, 사용자 ID 등)
            
        Returns:
            str: 에이전트 응답
        """
        pass
    
    def get_name(self) -> str:
        """에이전트 이름 반환"""
        return self.name
    
    def get_description(self) -> str:
        """에이전트 설명 반환"""
        return self.description
    
    def get_capabilities(self) -> list:
        """
        에이전트 기능 목록 반환
        
        서브클래스에서 오버라이드하여 구체적인 기능 목록 제공
        """
        return []
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name='{self.name}')"

