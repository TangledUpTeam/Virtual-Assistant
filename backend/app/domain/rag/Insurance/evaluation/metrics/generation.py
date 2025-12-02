"""
Generation evaluation metrics
"""
from typing import List, Tuple
import re
import numpy as np


class GenerationMetrics:
    """답변 생성 성능 평가 지표"""
    
    @staticmethod
    def calculate_semantic_similarity(
        embedding1: List[float],
        embedding2: List[float]
    ) -> float:
        """
        코사인 유사도 계산
        
        Args:
            embedding1: 첫 번째 임베딩
            embedding2: 두 번째 임베딩
            
        Returns:
            코사인 유사도 (0~1)
        """
        vec1 = np.array(embedding1)
        vec2 = np.array(embedding2)
        
        return float(np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2)))
    
    @staticmethod
    def calculate_keyword_hit(
        ground_truth: str,
        generated_answer: str,
        min_hits: int = 2
    ) -> Tuple[bool, int, List[str]]:
        """
        키워드 일치도 평가
        
        Args:
            ground_truth: 정답
            generated_answer: 생성된 답변
            min_hits: 최소 일치 키워드 개수
            
        Returns:
            (적중 여부, 적중 개수, 매칭된 키워드 리스트)
        """
        gt_keywords = GenerationMetrics._extract_keywords(ground_truth)
        
        if not gt_keywords:
            return True, 0, []
        
        matched_keywords = [kw for kw in gt_keywords if kw in generated_answer]
        hit_count = len(matched_keywords)
        is_hit = hit_count >= min_hits
        
        return is_hit, hit_count, matched_keywords
    
    @staticmethod
    def _extract_keywords(text: str, min_length: int = 2) -> List[str]:
        """키워드 추출"""
        text = re.sub(r'[^\w\s가-힣]', ' ', text)
        tokens = text.split()
        
        stopwords = {
            '은', '는', '이', '가', '을', '를', '의', '에', '와', '과', '도',
            '으로', '로', '입니다', '있습니다', '합니다', '한다', '된다', '이다',
            '것', '수', '등', 'the', 'a', 'an', 'and', 'or', 'but', 'in',
            'on', 'at', 'to', 'for', 'of', 'with'
        }
        
        keywords = [
            token for token in tokens
            if len(token) >= min_length and token.lower() not in stopwords
        ]
        
        return list(set(keywords))
