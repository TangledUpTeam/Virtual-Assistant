"""Insurance RAG Services Layer"""
from .document_processor.extractor import PDFExtractor, PageAnalysis, PageResult
from .document_processor.chunker import TextChunker
from .retriever import Retriever
from .generator import Generator
try:
    # Avoid importing heavy or deprecated modules at package import time
    from .rag_pipeline import RAGPipeline  # noqa: F401
except Exception:
    # Make services import resilient for scripts that only need extractor
    RAGPipeline = None

__all__ = [
    "PDFExtractor",
    "PageAnalysis",
    "PageResult",
    "TextChunker",
    "Retriever",
    "Generator",
    "RAGPipeline",
]
