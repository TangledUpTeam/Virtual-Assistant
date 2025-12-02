"""
Insurance Manual PDF 추출 테스트
"""
import sys
from pathlib import Path

# 백엔드 루트 경로 추가
backend_path = Path(__file__).parents[4]
sys.path.insert(0, str(backend_path))

# 환경변수 설정
import os
os.environ.setdefault("OPENAI_API_KEY", "your-key-here")

def main():
    # Insurance 경로 직접 참조
    insurance_path = Path(__file__).parent
    sys.path.insert(0, str(insurance_path))
    
    # 직접 import (상대경로 문제 회피)
    from services.document_processor.extractor import PDFExtractor
    from core.config import config
    
    # PDF 경로
    pdf_path = insurance_path / "documents" / "insurance_manual.pdf"
    
    if not pdf_path.exists():
        print(f"❌ PDF 파일을 찾을 수 없습니다: {pdf_path}")
        return
    
    print(f"📄 PDF 파일: {pdf_path}")
    print(f"📊 처리 시작...\n")
    
    # Extractor 초기화
    extractor = PDFExtractor(config)
    
    # PDF 추출
    results = extractor.extract_pdf(str(pdf_path), use_vision=True)
    
    print(f"\n{'='*60}")
    print(f"✅ 추출 완료: {len(results)}페이지")
    print(f"{'='*60}\n")
    
    # 샘플 출력 (처음 3페이지)
    for i, result in enumerate(results[:3], 1):
        print(f"페이지 {result.page}:")
        print(f"  - 모드: {result.mode}")
        print(f"  - 텍스트 길이: {len(result.content)} chars")
        print(f"  - 테이블: {result.has_tables}")
        print(f"  - 이미지: {result.has_images}")
        print(f"  - 내용 미리보기: {result.content[:100]}...")
        print()

if __name__ == "__main__":
    main()
