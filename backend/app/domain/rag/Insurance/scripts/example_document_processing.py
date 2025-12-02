#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
PDF 문서 로딩 및 청킹 예제
"""
import sys
import os

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../../../../'))
sys.path.insert(0, project_root)

from backend.app.domain.rag.Insurance.services import DocumentProcessor
from backend.app.domain.rag.Insurance.infrastructure.document_loader import PDFDocumentLoader
from backend.app.domain.rag.Insurance.infrastructure.chunking import TokenChunker, SemanticChunker


def main():
    """메인 실행 함수"""
    print("="*80)
    print("PDF 문서 처리 예제")
    print("="*80)
    
    # 예제 1: 기본 DocumentProcessor (Token Chunker 사용)
    print("\n[예제 1] 기본 Token Chunker 사용")
    processor = DocumentProcessor(use_token_chunker=True)
    info = processor.get_info()
    print(f"  - Document Loader: {info['document_loader']}")
    print(f"  - Chunker: {info['chunker']}")
    print(f"  - Strategy: {info['chunking_strategy']}")
    
    # 예제 2: Semantic Chunker 사용
    print("\n[예제 2] Semantic Chunker 사용")
    processor_semantic = DocumentProcessor(use_token_chunker=False)
    info = processor_semantic.get_info()
    print(f"  - Document Loader: {info['document_loader']}")
    print(f"  - Chunker: {info['chunker']}")
    print(f"  - Strategy: {info['chunking_strategy']}")
    
    # 예제 3: 커스텀 조합
    print("\n[예제 3] 커스텀 Document Loader + Chunker")
    custom_loader = PDFDocumentLoader(use_vision=True, resume=False)
    custom_chunker = TokenChunker(max_tokens=300, overlap_tokens=50)
    processor_custom = DocumentProcessor(
        document_loader=custom_loader,
        chunker=custom_chunker
    )
    info = processor_custom.get_info()
    print(f"  - Document Loader: {info['document_loader']}")
    print(f"  - Chunker: {info['chunker']}")
    print(f"  - Strategy: {info['chunking_strategy']}")
    
    # 예제 4: 간단한 텍스트 청킹
    print("\n[예제 4] 텍스트 직접 청킹")
    sample_text = """
    제1조 (목적) 이 약관은 보험계약의 내용 및 조건을 정함을 목적으로 합니다.
    
    제2조 (정의) 이 약관에서 사용하는 용어의 정의는 다음과 같습니다.
    1. 보험계약자: 보험회사와 계약을 체결하는 자
    2. 피보험자: 보험사고 발생 시 보상받는 자
    
    제3조 (보험금의 지급) 보험금은 다음과 같이 지급됩니다.
    1. 사고 발생 시 30일 이내 지급
    2. 필요 서류 제출 후 처리
    """
    
    chunks = processor.process_document(
        content=sample_text,
        metadata={"document_type": "insurance_terms"},
        doc_id="sample_001"
    )
    
    print(f"  - 생성된 청크 수: {len(chunks)}")
    for i, chunk in enumerate(chunks[:2], 1):  # 처음 2개만 표시
        print(f"\n  [청크 {i}]")
        print(f"    ID: {chunk.id}")
        print(f"    내용 미리보기: {chunk.content[:100]}...")
        print(f"    메타데이터: {chunk.metadata}")
    
    print("\n" + "="*80)


if __name__ == "__main__":
    main()
