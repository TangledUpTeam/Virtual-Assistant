"""
Insurance RAG core utilities
"""
import logging
from typing import Optional


def get_logger(name: str, level: Optional[str] = None) -> logging.Logger:
    """
    Insurance RAG 시스템용 로거 생성
    
    Args:
        name: 로거 이름
        level: 로그 레벨 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        
    Returns:
        logging.Logger: 설정된 로거
    """
    logger = logging.getLogger(name)
    
    if not logger.handlers:
        # 핸들러가 없을 때만 설정
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
        # 로그 레벨 설정
        if level:
            logger.setLevel(getattr(logging, level.upper()))
        else:
            # 기본값: INFO
            logger.setLevel(logging.INFO)
    
    return logger


__all__ = ["get_logger"]
