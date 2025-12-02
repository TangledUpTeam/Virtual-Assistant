"""
End-to-end RAG evaluation metrics
"""
from typing import Dict, List, Any
import numpy as np


class EndToEndMetrics:
    """전체 RAG 시스템 평가 지표"""
    
    @staticmethod
    def calculate_overall_score(
        retrieval_hit_rate: float,
        semantic_similarity: float,
        judge_score: float,
        keyword_hit_rate: float,
        weights: Dict[str, float] = None
    ) -> float:
        """
        전체 성능 점수 계산 (가중 평균)
        
        Args:
            retrieval_hit_rate: 검색 적중률
            semantic_similarity: 의미 유사도
            judge_score: LLM 판단 점수 (0~2 → 0~1로 정규화)
            keyword_hit_rate: 키워드 적중률
            weights: 각 지표별 가중치
            
        Returns:
            전체 점수 (0~1)
        """
        if weights is None:
            weights = {
                "retrieval": 0.35,
                "similarity": 0.25,
                "judge": 0.25,
                "keyword": 0.15
            }
        
        normalized_judge = judge_score / 2.0
        
        overall = (
            retrieval_hit_rate * weights["retrieval"] +
            semantic_similarity * weights["similarity"] +
            normalized_judge * weights["judge"] +
            keyword_hit_rate * weights["keyword"]
        )
        
        return float(overall)
    
    @staticmethod
    def summarize_results(results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        평가 결과 요약
        
        Args:
            results: 개별 평가 결과 리스트
            
        Returns:
            요약 통계
        """
        if not results:
            return {}
        
        total = len(results)
        
        retrieval_hits = sum(1 for r in results if r.get('retrieval_hit', False))
        similarity_hits = sum(1 for r in results if r.get('similarity_hit', False))
        keyword_hits = sum(1 for r in results if r.get('keyword_hit', False))
        
        avg_similarity = np.mean([r.get('semantic_similarity', 0) for r in results])
        avg_judge_score = np.mean([r.get('judge_score', 0) for r in results])
        
        failures = [
            r for r in results
            if not r.get('retrieval_hit', False)
            and not r.get('similarity_hit', False)
            and r.get('judge_score', 0) < 1
        ]
        
        return {
            'total_questions': total,
            'retrieval_hit_rate': retrieval_hits / total,
            'retrieval_hit_count': retrieval_hits,
            'semantic_similarity_avg': float(avg_similarity),
            'similarity_hit_rate': similarity_hits / total,
            'similarity_hit_count': similarity_hits,
            'judge_score_avg': float(avg_judge_score),
            'keyword_hit_rate': keyword_hits / total,
            'keyword_hit_count': keyword_hits,
            'failure_count': len(failures),
            'failures': failures
        }
