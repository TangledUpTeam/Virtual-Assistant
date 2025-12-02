"""
OpenAI LLM provider implementation
"""
from typing import List, Dict, Any, Optional
from openai import OpenAI

from .base import BaseLLMProvider
from ...core.config import config
from ...core.exceptions import LLMException


class OpenAILLMProvider(BaseLLMProvider):
    """OpenAI LLM 구현체"""
    
    def __init__(
        self,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ):
        """
        OpenAI LLM 제공자 초기화
        
        Args:
            model: 모델 이름
            temperature: 기본 온도
            max_tokens: 기본 최대 토큰
        """
        self.model = model or config.llm_model
        self.default_temperature = temperature or config.llm_temperature
        self.default_max_tokens = max_tokens or config.llm_max_tokens
        
        try:
            self.client = OpenAI(**config.get_openai_kwargs())
        except Exception as e:
            raise LLMException(
                f"Failed to initialize OpenAI client: {str(e)}"
            )
    
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> str:
        """텍스트 생성"""
        messages = []
        
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        messages.append({"role": "user", "content": prompt})
        
        return self.generate_with_messages(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )
    
    def generate_with_messages(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> str:
        """메시지로 텍스트 생성"""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature or self.default_temperature,
                max_tokens=max_tokens or self.default_max_tokens,
                **kwargs
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            raise LLMException(
                f"Failed to generate text: {str(e)}",
                details={"model": self.model, "num_messages": len(messages)}
            )
    
    def get_model_name(self) -> str:
        """모델 이름 반환"""
        return self.model
