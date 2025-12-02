"""
Base interface for LLM providers
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional


class BaseLLMProvider(ABC):
    """LLM 제공자 추상 인터페이스"""
    
    @abstractmethod
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> str:
        """
        텍스트 생성
        
        Args:
            prompt: 사용자 프롬프트
            system_prompt: 시스템 프롬프트
            temperature: 생성 온도
            max_tokens: 최대 토큰 수
            **kwargs: 추가 파라미터
            
        Returns:
            생성된 텍스트
        """
        pass
    
    @abstractmethod
    def generate_with_messages(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> str:
        """
        메시지 리스트로 텍스트 생성
        
        Args:
            messages: 대화 메시지 리스트
            temperature: 생성 온도
            max_tokens: 최대 토큰 수
            **kwargs: 추가 파라미터
            
        Returns:
            생성된 텍스트
        """
        pass
    
    @abstractmethod
    def get_model_name(self) -> str:
        """
        사용 중인 모델 이름 반환
        
        Returns:
            모델 이름
        """
        pass
