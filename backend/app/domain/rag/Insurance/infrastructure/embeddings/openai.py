"""
OpenAI embedding provider implementation
"""
from typing import List
from openai import OpenAI

from .base import BaseEmbeddingProvider
from ...core.config import config
from ...core.exceptions import EmbeddingException


class OpenAIEmbeddingProvider(BaseEmbeddingProvider):
    """OpenAI 임베딩 구현체"""
    
    def __init__(
        self,
        model: str = None,
        dimensions: int = None
    ):
        """
        OpenAI 임베딩 제공자 초기화
        
        Args:
            model: 임베딩 모델 이름
            dimensions: 임베딩 차원 수
        """
        self.model = model or config.embedding_model
        self.dimensions = dimensions or config.embedding_dimensions
        
        try:
            self.client = OpenAI(**config.get_openai_kwargs())
        except Exception as e:
            raise EmbeddingException(
                f"Failed to initialize OpenAI client: {str(e)}"
            )
    
    def embed_text(self, text: str) -> List[float]:
        """단일 텍스트 임베딩"""
        try:
            text = text.replace("\n", " ").strip()
            
            response = self.client.embeddings.create(
                model=self.model,
                input=[text]
            )
            
            return response.data[0].embedding
            
        except Exception as e:
            raise EmbeddingException(
                f"Failed to embed text: {str(e)}",
                details={"text_length": len(text)}
            )
    
    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """여러 텍스트 배치 임베딩"""
        if not texts:
            return []
        
        try:
            # 텍스트 전처리
            cleaned_texts = [text.replace("\n", " ").strip() for text in texts]
            
            # 배치 처리
            embeddings = []
            batch_size = config.embedding_batch_size
            
            for i in range(0, len(cleaned_texts), batch_size):
                batch = cleaned_texts[i:i + batch_size]
                
                response = self.client.embeddings.create(
                    model=self.model,
                    input=batch
                )
                
                batch_embeddings = [item.embedding for item in response.data]
                embeddings.extend(batch_embeddings)
            
            return embeddings
            
        except Exception as e:
            raise EmbeddingException(
                f"Failed to embed texts: {str(e)}",
                details={"num_texts": len(texts)}
            )
    
    def get_embedding_dimension(self) -> int:
        """임베딩 차원 반환"""
        return self.dimensions
    
    def get_model_name(self) -> str:
        """모델 이름 반환"""
        return self.model
