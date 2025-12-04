from __future__ import annotations

from typing import Any, Dict, List, Optional

from ingestion.embed import get_embedding_service

from app.domain.report.core.chunker import ChunkValidationError, validate_metadata
from app.infrastructure.vector_store_report import get_report_vector_store

BATCH_SIZE = 64


class EmbeddingPipeline:
    """Generate embeddings for chunks and store them in the report vector store."""

    def __init__(
        self,
        vector_store=None,
        embedding_model_type: Optional[str] = None,
    ) -> None:
        self.vector_store = vector_store or get_report_vector_store()
        self.embedding_service = get_embedding_service(model_type=embedding_model_type)

    def embed_texts(self, texts: List[str], batch_size: int = BATCH_SIZE) -> List[List[float]]:
        return self.embedding_service.embed_texts(texts, batch_size=batch_size)

    def process_and_store(
        self,
        chunks: List[Dict[str, Any]],
        batch_size: int = BATCH_SIZE,
    ) -> Dict[str, Any]:
        if not chunks:
            raise ChunkValidationError("No chunks provided for embedding")

        validated_chunks: List[Dict[str, Any]] = []
        for chunk in chunks:
            if "id" not in chunk or "text" not in chunk or "metadata" not in chunk:
                raise ChunkValidationError("Chunk must contain id, text, and metadata fields")

            metadata = validate_metadata(dict(chunk["metadata"]))
            validated_chunks.append(
                {
                    "id": chunk["id"],
                    "text": chunk["text"],
                    "metadata": metadata,
                }
            )

        texts = [chunk["text"] for chunk in validated_chunks]
        embeddings = self.embed_texts(texts, batch_size=batch_size)

        self.vector_store.upsert_chunks(validated_chunks, embeddings)
        total_documents = self.vector_store.get_collection().count()

        return {
            "success": True,
            "chunks_processed": len(validated_chunks),
            "embeddings_created": len(embeddings),
            "total_documents": total_documents,
        }


_embedding_pipeline: Optional[EmbeddingPipeline] = None


def get_embedding_pipeline(model_type: Optional[str] = None) -> EmbeddingPipeline:
    global _embedding_pipeline
    if _embedding_pipeline is None:
        _embedding_pipeline = EmbeddingPipeline(embedding_model_type=model_type)
    return _embedding_pipeline
