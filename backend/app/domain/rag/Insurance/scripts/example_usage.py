#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
간단한 RAG 파이프라인 실행 예제
"""
import sys
import os

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../../../../'))
sys.path.insert(0, project_root)

from backend.app.domain.rag.Insurance.services import RAGPipeline


def main():
    """메인 실행 함수"""
    print("="*80)
    print("보험 RAG 파이프라인 예제")
    print("="*80)
    
    # 파이프라인 생성
    pipeline = RAGPipeline()
    
    # 파이프라인 정보 출력
    info = pipeline.get_pipeline_info()
    print("\n[파이프라인 구성]")
    print(f"  - Vector Store: {info['vector_store']}")
    print(f"  - Embedding Model: {info['embedding_model']}")
    print(f"  - LLM Model: {info['llm_model']}")
    print(f"  - 문서 수: {info['vector_store_info']['count']}")
    
    # 질문 예시
    questions = [
        "자동차 보험 청구 절차는?",
        "보험금은 언제 지급되나요?",
        "보험 가입 조건은 무엇인가요?"
    ]
    
    print("\n[질의응답 테스트]")
    for i, question in enumerate(questions, 1):
        print(f"\n[질문 {i}] {question}")
        
        try:
            result = pipeline.run(question=question)
            print(f"[답변] {result.answer[:200]}...")
            print(f"[신뢰도] {result.confidence_score:.2f}")
            print(f"[소요시간] {result.generation_time_ms:.0f}ms")
        except Exception as e:
            print(f"[ERROR] {str(e)}")
    
    print("\n" + "="*80)


if __name__ == "__main__":
    main()
