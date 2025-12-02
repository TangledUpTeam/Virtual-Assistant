#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
보험 RAG 평가 실행 스크립트
"""
import sys
import os

# 프로젝트 루트를 sys.path에 추가
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../../../../'))
sys.path.insert(0, project_root)

from backend.app.domain.rag.Insurance.evaluation import RAGEvaluator


def main():
    """메인 실행 함수"""
    print("="*80)
    print("보험 문서 RAG 성능 평가")
    print("="*80)
    
    # 평가기 생성
    evaluator = RAGEvaluator()
    
    # 평가 실행
    evaluation_data = evaluator.evaluate(
        top_k=5,
        similarity_threshold=0.75
    )
    
    # 결과 출력
    evaluator.print_summary(evaluation_data['summary'])
    
    # 결과 저장
    evaluator.save_results(evaluation_data)
    
    print("\n[OK] 평가 완료!")


if __name__ == "__main__":
    main()
