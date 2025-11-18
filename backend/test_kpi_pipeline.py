"""
KPI 파이프라인 End-to-End 테스트 스크립트

Usage:
    python test_kpi_pipeline.py <pdf_file_path>
    
Example:
    python test_kpi_pipeline.py "Data/보험사_KPI_자료.pdf"
"""
import sys
import json
import os
import codecs
from pathlib import Path
from dotenv import load_dotenv

# Windows CMD에서 UTF-8 출력 설정
if sys.platform == "win32":
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.buffer, "strict")

# 프로젝트 루트를 Python Path에 추가
sys.path.insert(0, str(Path(__file__).parent))

from app.domain.kpi import (
    KPIVisionService,
    normalize_kpi_document,
    get_normalization_stats,
    build_kpi_chunks,
    get_chunk_statistics,
    enhance_chunks_with_metadata,
    get_metadata_summary
)


def main():
    """메인 함수"""
    # .env 파일 로드
    load_dotenv()
    
    # 명령행 인자 확인
    if len(sys.argv) < 2:
        print("=" * 70)
        print("KPI 파이프라인 테스트")
        print("=" * 70)
        print()
        print("사용법: python test_kpi_pipeline.py <pdf_file_path>")
        print()
        print("예시:")
        print('  python test_kpi_pipeline.py "Data/보험사_KPI_자료.pdf"')
        print('  python test_kpi_pipeline.py "Data/KPI_PDF.pdf"')
        print()
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
    
    print("=" * 70)
    print("🚀 KPI 파이프라인 테스트 시작")
    print("=" * 70)
    print(f"📂 파일: {pdf_path}")
    print()
    
    try:
        # ========================================
        # Step 1: PDF → Vision → Raw JSON
        # ========================================
        print("=" * 70)
        print("⏳ Step 1: Vision API로 PDF 처리 중...")
        print("=" * 70)
        
        service = KPIVisionService(api_key=api_key)
        raw_doc = service.process_pdf(pdf_path)
        
        print(f"📄 문서 제목: {raw_doc.title}")
        print(f"📄 총 페이지: {raw_doc.total_pages}")
        print(f"📄 처리된 페이지: {len(raw_doc.pages)}")
        print()
        
        # ========================================
        # Step 2: Raw JSON → CanonicalKPI
        # ========================================
        print("=" * 70)
        print("⏳ Step 2: Canonical KPI 변환 중...")
        print("=" * 70)
        
        canonical_kpis = normalize_kpi_document(raw_doc)
        
        # 정규화 통계
        norm_stats = get_normalization_stats(canonical_kpis)
        print(f"📊 총 KPI 수: {norm_stats['total_kpis']}")
        print(f"📊 카테고리별:")
        for category, count in norm_stats['by_category'].items():
            print(f"   - {category}: {count}개")
        print(f"📊 표 포함 KPI: {norm_stats['with_table']}개")
        print(f"📊 증감 정보 포함: {norm_stats['with_delta']}개")
        print()
        
        # ========================================
        # Step 3: CanonicalKPI → 청크
        # ========================================
        print("=" * 70)
        print("⏳ Step 3: 청킹 생성 중...")
        print("=" * 70)
        
        chunks = build_kpi_chunks(canonical_kpis)
        
        # 청크 통계
        chunk_stats = get_chunk_statistics(chunks)
        print(f"📊 총 청크 수: {chunk_stats['total_chunks']}")
        print(f"📊 평균 길이: {chunk_stats['avg_text_length']:.0f}자")
        print(f"📊 최대 길이: {chunk_stats['max_text_length']}자")
        print(f"📊 최소 길이: {chunk_stats['min_text_length']}자")
        print()
        
        # ========================================
        # Step 4: 메타데이터 추가
        # ========================================
        print("=" * 70)
        print("⏳ Step 4: 메타데이터 추가 중...")
        print("=" * 70)
        
        final_chunks = enhance_chunks_with_metadata(chunks)
        
        # 메타데이터 통계
        meta_summary = get_metadata_summary(final_chunks)
        print(f"📊 고유 KPI 이름: {meta_summary['unique_kpi_names']}개")
        print(f"📊 고유 카테고리: {meta_summary['unique_categories']}개")
        print(f"📊 고유 단위: {meta_summary['unique_units']}개")
        print()
        
        # ========================================
        # 샘플 출력
        # ========================================
        print("=" * 70)
        print("📋 청크 샘플 (처음 3개)")
        print("=" * 70)
        
        for idx, chunk in enumerate(final_chunks[:3], 1):
            print(f"\n[청크 #{idx}]")
            print(f"ID: {chunk['chunk_id']}")
            print(f"KPI ID: {chunk['kpi_id']}")
            print(f"페이지: {chunk['page_index'] + 1}")
            print(f"태그: {', '.join(chunk['tags'])}")
            print(f"메타데이터: {json.dumps(chunk['metadata'], ensure_ascii=False, indent=2)}")
            print(f"\n텍스트 (처음 200자):")
            print(chunk['text'][:200] + "..." if len(chunk['text']) > 200 else chunk['text'])
            print("-" * 70)
        
        # ========================================
        # 파일 저장
        # ========================================
        print()
        print("=" * 70)
        print("💾 결과 파일 저장 중...")
        print("=" * 70)
        
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)
        
        pdf_filename = Path(pdf_path).stem
        
        # 1. Raw JSON 저장
        raw_output_path = output_dir / f"{pdf_filename}_kpi_raw.json"
        with open(raw_output_path, "w", encoding="utf-8") as f:
            json.dump(raw_doc.model_dump(mode='json'), f, ensure_ascii=False, indent=2, default=str)
        
        # 2. Canonical KPI 저장
        canonical_output_path = output_dir / f"{pdf_filename}_kpi_canonical.json"
        with open(canonical_output_path, "w", encoding="utf-8") as f:
            canonical_data = [kpi.model_dump(mode='json') for kpi in canonical_kpis]
            json.dump(canonical_data, f, ensure_ascii=False, indent=2, default=str)
        
        # 3. 최종 청크 저장
        chunks_output_path = output_dir / f"{pdf_filename}_kpi_chunks.json"
        with open(chunks_output_path, "w", encoding="utf-8") as f:
            json.dump(final_chunks, f, ensure_ascii=False, indent=2, default=str)
        
        print(f"1. Raw JSON: {raw_output_path}")
        print(f"2. Canonical KPI: {canonical_output_path}")
        print(f"3. 최종 청크: {chunks_output_path}")
        print()
        
        # ========================================
        # TODO: VectorDB 연동
        # ========================================
        print("=" * 70)
        print("📝 다음 단계")
        print("=" * 70)
        print("TODO: VectorDB 업서트 연동 예정")
        print()
        print("예시 코드:")
        print("""
import chromadb

# ChromaDB 클라이언트
client = chromadb.Client()
collection = client.create_collection("kpi_documents")

# 청크 추가
for chunk in final_chunks:
    collection.add(
        ids=[chunk["chunk_id"]],
        documents=[chunk["text"]],
        metadatas=[chunk["metadata"]]
    )
        """)
        print()
        
        print("=" * 70)
        print("✅ KPI 파이프라인 테스트 완료!")
        print("=" * 70)
        
    except Exception as e:
        print()
        print("=" * 70)
        print("❌ 오류 발생")
        print("=" * 70)
        print(f"오류 내용: {str(e)}")
        print()
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

