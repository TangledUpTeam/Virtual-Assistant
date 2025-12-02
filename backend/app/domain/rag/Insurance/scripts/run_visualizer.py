#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
보험 RAG 시각화 실행 스크립트
"""
import sys
import os

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../../../../'))
sys.path.insert(0, project_root)

from backend.app.domain.rag.Insurance.evaluation import ResultsVisualizer
from backend.app.domain.rag.Insurance.core.config import config


def main():
    """메인 실행 함수"""
    print("="*80)
    print("RAG 평가 결과 시각화")
    print("="*80)
    
    results_file = os.path.join(
        config.eval_output_full_path,
        "evaluation_results.json"
    )
    
    if not os.path.exists(results_file):
        print(f"\n[ERROR] 평가 결과 파일을 찾을 수 없습니다: {results_file}")
        print("먼저 run_evaluation.py를 실행하세요.")
        return
    
    visualizer = ResultsVisualizer()
    visualizer.create_all_visualizations(results_file)
    
    print("\n[OK] 시각화 완료!")


if __name__ == "__main__":
    main()
