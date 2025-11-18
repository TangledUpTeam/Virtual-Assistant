"""
보고서 파싱 테스트 CLI 스크립트

Usage:
    python test_report_parser.py <pdf_file_path>
    
Example:
    python test_report_parser.py "backend/Data/일일 업무 보고서.pdf"
"""
import sys
import json
import os
from pathlib import Path

# 프로젝트 루트를 Python Path에 추가
sys.path.insert(0, str(Path(__file__).parent))

from app.domain.report.service import ReportProcessingService
from app.domain.report.chunker import chunk_report, get_chunk_statistics
from dotenv import load_dotenv


def main():
    """메인 함수"""
    # .env 파일 로드
    load_dotenv()
    
    # 명령행 인자 확인
    if len(sys.argv) < 2:
        print("❌ 사용법: python test_report_parser.py <pdf_file_path>")
        print("\n📋 예시:")
        print('  python test_report_parser.py "backend/Data/일일 업무 보고서.pdf"')
        print('  python test_report_parser.py "backend/Data/주간 업무 보고서.pdf"')
        print('  python test_report_parser.py "backend/Data/월간 업무 보고서.pdf"')
        print('  python test_report_parser.py "backend/Data/실적 보고서 양식.pdf"')
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    
    # 파일 존재 확인
    if not os.path.exists(pdf_path):
        print(f"❌ 파일을 찾을 수 없습니다: {pdf_path}")
        sys.exit(1)
    
    # OpenAI API 키 확인
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ OPENAI_API_KEY 환경변수가 설정되지 않았습니다.")
        print("💡 .env 파일에 OPENAI_API_KEY를 추가하세요.")
        sys.exit(1)
    
    print("=" * 60)
    print("📄 보고서 파싱 시작")
    print("=" * 60)
    print(f"📂 파일: {pdf_path}")
    print()
    
    try:
        # 보고서 처리 서비스 초기화
        service = ReportProcessingService(api_key=api_key)
        
        # 1단계: 보고서 처리 (Vision API → Raw JSON)
        print("⏳ Step 1: Vision API로 PDF 파싱 중...")
        report_type, raw_json = service.process_report(pdf_path)
        
        print()
        print("=" * 60)
        print("✅ Step 1 완료: Raw JSON 추출")
        print("=" * 60)
        print(f"📊 보고서 타입: {report_type.value}")
        print()
        print("📋 Raw JSON 데이터:")
        print("-" * 60)
        print(json.dumps(raw_json, ensure_ascii=False, indent=2))
        print("-" * 60)
        
        # 2단계: Raw JSON → Canonical JSON 변환
        print()
        print("⏳ Step 2: Canonical JSON 변환 중...")
        canonical_report = service.normalize_report(report_type, raw_json)
        
        print()
        print("=" * 60)
        print("✅ Step 2 완료: Canonical JSON 생성")
        print("=" * 60)
        print("📋 Canonical JSON 데이터:")
        print("-" * 60)
        # Pydantic 모델을 dict로 변환
        canonical_dict = canonical_report.model_dump(mode='json')
        print(json.dumps(canonical_dict, ensure_ascii=False, indent=2, default=str))
        print("-" * 60)
        
        # JSON 파일로 저장
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)
        
        pdf_filename = Path(pdf_path).stem
        
        # Raw JSON 저장
        raw_output_path = output_dir / f"{pdf_filename}_{report_type.value}_raw.json"
        with open(raw_output_path, "w", encoding="utf-8") as f:
            json.dump(raw_json, f, ensure_ascii=False, indent=2)
        
        # Canonical JSON 저장
        canonical_output_path = output_dir / f"{pdf_filename}_{report_type.value}_canonical.json"
        with open(canonical_output_path, "w", encoding="utf-8") as f:
            json.dump(canonical_dict, f, ensure_ascii=False, indent=2, default=str)
        
        # 통합 JSON 저장 (Raw + Canonical)
        combined_output_path = output_dir / f"{pdf_filename}_{report_type.value}_combined.json"
        with open(combined_output_path, "w", encoding="utf-8") as f:
            combined = {
                "report_type": report_type.value,
                "raw": raw_json,
                "canonical": canonical_dict
            }
            json.dump(combined, f, ensure_ascii=False, indent=2, default=str)
        
        print()
        print("=" * 60)
        print("💾 파일 저장 완료")
        print("=" * 60)
        print(f"1. Raw JSON: {raw_output_path}")
        print(f"2. Canonical JSON: {canonical_output_path}")
        print(f"3. Combined JSON: {combined_output_path}")
        print()
        
        # Step 3: Canonical → Chunks (RAG용 청킹)
        print()
        print("=" * 60)
        print("⏳ Step 3: RAG 청킹 생성 중...")
        print("=" * 60)
        chunks = chunk_report(canonical_report, include_summary=True)
        
        print(f"✅ 총 {len(chunks)}개 청크 생성됨")
        print()
        
        # 청크 통계
        stats = get_chunk_statistics(chunks)
        print("📊 청크 통계:")
        print(f"  - 총 청크 수: {stats['total_chunks']}")
        print(f"  - 평균 길이: {stats['avg_text_length']:.0f}자")
        print(f"  - 최대 길이: {stats['max_text_length']}자")
        print(f"  - 최소 길이: {stats['min_text_length']}자")
        print(f"  - 타입별 분포:")
        for chunk_type, count in stats['chunk_types'].items():
            print(f"    • {chunk_type}: {count}개")
        print()
        
        # 첫 3개 청크 출력
        print("=" * 60)
        print("📋 청크 샘플 (첫 3개)")
        print("=" * 60)
        for idx, chunk in enumerate(chunks[:3], 1):
            print(f"\n[청크 #{idx}]")
            print(f"ID: {chunk['id']}")
            print(f"타입: {chunk['metadata'].get('chunk_type')}")
            print(f"길이: {len(chunk['text'])}자")
            print(f"텍스트:\n{chunk['text']}")
            print("-" * 60)
        
        # 청크 JSON 파일로 저장
        chunks_output_path = output_dir / f"{pdf_filename}_{report_type.value}_chunks.json"
        with open(chunks_output_path, "w", encoding="utf-8") as f:
            json.dump(chunks, f, ensure_ascii=False, indent=2, default=str)
        
        print()
        print(f"💾 청크 파일 저장됨: {chunks_output_path}")
        print()
        
    except Exception as e:
        print()
        print("=" * 60)
        print("❌ 오류 발생")
        print("=" * 60)
        print(f"오류 내용: {str(e)}")
        print()
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

