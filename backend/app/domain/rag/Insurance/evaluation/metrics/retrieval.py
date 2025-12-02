"""
Retrieval evaluation metrics
"""
from typing import List
import re


class RetrievalMetrics:
    """검색 성능 평가 지표"""
    
    @staticmethod
    def calculate_hit_rate(
        retrieved_chunks: List[str],
        ground_truth: str,
        min_keyword_match: int = 3
    ) -> tuple[bool, List[int]]:
        """
        검색된 chunk에 정답 관련 내용이 있는지 확인
        
        Args:
            retrieved_chunks: 검색된 chunk 리스트
            ground_truth: 정답
            min_keyword_match: 최소 키워드 매칭 개수
            
        Returns:
            (적중 여부, 적중한 chunk 인덱스 리스트)
        """
        gt_keywords = RetrievalMetrics._extract_keywords(ground_truth)
        
        if not gt_keywords:
            return False, []
        
        hit_chunks = []
        for i, chunk in enumerate(retrieved_chunks):
            matched = sum(1 for kw in gt_keywords if kw in chunk)
            if matched >= min_keyword_match or ground_truth[:20] in chunk:
                hit_chunks.append(i)
        
        return len(hit_chunks) > 0, hit_chunks
    
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
