from __future__ import annotations

import os
from typing import List, Optional

from openai import OpenAI
from sentence_transformers import SentenceTransformer

DEFAULT_HF_MODEL = "sentence-transformers/all-MiniLM-L12-v2"
DEFAULT_HF_DIM = 384
DEFAULT_BATCH = 100


class EmbeddingService:
    """Shared embedding service (HF or OpenAI)."""

    def __init__(self, model_type: Optional[str] = None, api_key: Optional[str] = None) -> None:
        self.model_type = model_type or os.getenv("REPORT_EMBEDDING_MODEL_TYPE", "hf")
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")

        if self.model_type == "hf":
            self.model = SentenceTransformer(DEFAULT_HF_MODEL)
            self.dimension = DEFAULT_HF_DIM
        else:
            if not self.api_key:
                raise ValueError("OPENAI_API_KEY is required for OpenAI embeddings")
            self.client = OpenAI(api_key=self.api_key)
            self.model = os.getenv("OPENAI_EMBED_MODEL", "text-embedding-3-large")
            self.dimension = 3072

    def embed_text(self, text: str) -> List[float]:
        if self.model_type == "hf":
            return self.model.encode(text, convert_to_numpy=True).tolist()

        response = self.client.embeddings.create(
            model=self.model,
            input=text,
            encoding_format="float",
        )
        return response.data[0].embedding

    def embed_texts(self, texts: List[str], batch_size: int = DEFAULT_BATCH) -> List[List[float]]:
        embeddings: List[List[float]] = []
        total = len(texts)

        for i in range(0, total, batch_size):
            batch = texts[i : i + batch_size]
            if self.model_type == "hf":
                embeddings.extend(self.model.encode(batch, convert_to_numpy=True).tolist())
            else:
                response = self.client.embeddings.create(
                    model=self.model,
                    input=batch,
                    encoding_format="float",
                )
                embeddings.extend([item.embedding for item in response.data])

        return embeddings


_embedding_service: Optional[EmbeddingService] = None


def get_embedding_service(api_key: Optional[str] = None, model_type: Optional[str] = None) -> EmbeddingService:
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService(api_key=api_key, model_type=model_type)
    return _embedding_service


def embed_text(text: str, api_key: Optional[str] = None, model_type: Optional[str] = None) -> List[float]:
    return get_embedding_service(api_key=api_key, model_type=model_type).embed_text(text)


def embed_texts(
    texts: List[str],
    api_key: Optional[str] = None,
    batch_size: int = DEFAULT_BATCH,
    model_type: Optional[str] = None,
) -> List[List[float]]:
    return get_embedding_service(api_key=api_key, model_type=model_type).embed_texts(texts, batch_size=batch_size)
