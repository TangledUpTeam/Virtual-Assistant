"""
Custom exceptions for Insurance RAG system
"""


class InsuranceRAGException(Exception):
    """Base exception for Insurance RAG system"""
    
    def __init__(self, message: str, details: dict = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}
    
    def __str__(self):
        if self.details:
            return f"{self.message} | Details: {self.details}"
        return self.message


class VectorStoreException(InsuranceRAGException):
    """Vector store related exceptions"""
    pass


class EmbeddingException(InsuranceRAGException):
    """Embedding generation exceptions"""
    pass


class LLMException(InsuranceRAGException):
    """LLM generation exceptions"""
    pass


class DocumentProcessingException(InsuranceRAGException):
    """Document processing exceptions"""
    pass


class RetrievalException(InsuranceRAGException):
    """Retrieval related exceptions"""
    pass


class GenerationException(InsuranceRAGException):
    """Answer generation exceptions"""
    pass


class ConfigurationException(InsuranceRAGException):
    """Configuration related exceptions"""
    pass


class ValidationException(InsuranceRAGException):
    """Validation related exceptions"""
    pass
