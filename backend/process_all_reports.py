"""
모든 보고서 PDF를 파싱하고 청킹하는 스크립트
"""
import sys
import codecs
import json
from pathlib import Path
from dotenv import load_dotenv

# Windows CMD에서 UTF-8 출력 설정
if sys.platform == "win32":
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.buffer, "strict")

# 프로젝트 루트를 Python Path에 추가
sys.path.insert(0, str(Path(__file__).parent))

from app.domain.report.service import ReportProcessingService
from app.domain.report.chunker import chunk_report, get_chunk_statistics

def process_report(pdf_path: str, service: ReportProcessingService):
    """단일 보고서 처리"""
    pdf_file = Path(pdf_path)
    
    if not pdf_file.exists():
        print(f"⚠️  파일을 찾을 수 없습니다: {pdf_path}")
        return False
    
    print(f"\n{'='*70}")
    print(f"📄 처리 중: {pdf_file.name}")
    print("="*70)
    
    # 1. PDF 파싱
    print("⏳ Step 1: PDF → Raw JSON")
    report_type, raw_json = service.process_report(str(pdf_file))
    print(f"✅ Raw JSON 생성 완료 (타입: {report_type})")
    
    # 2. Canonical 변환
    print("⏳ Step 2: Raw JSON → Canonical JSON")
    canonical_report = service.normalize_report(report_type, raw_json)
    print(f"✅ Canonical JSON 변환 완료")
    print(f"  - Report Type: {canonical_report.report_type}")
    print(f"  - Tasks: {len(canonical_report.tasks)}개")
    print(f"  - KPIs: {len(canonical_report.kpis)}개")
    
    # 3. Chunking
    print("⏳ Step 3: Canonical → Chunks")
    chunks = chunk_report(canonical_report)
    stats = get_chunk_statistics(chunks)
    print(f"✅ 청킹 완료")
    print(f"  - 총 청크: {stats['total_chunks']}개")
    print(f"  - 타입별 청크: {stats['chunk_types']}")
    
    # 4. 파일 저장
    output_dir = Path("output/reports")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    base_name = pdf_file.stem
    report_type = canonical_report.report_type
    
    # Raw JSON
    raw_path = output_dir / f"{base_name}_{report_type}_raw.json"
    with open(raw_path, "w", encoding="utf-8") as f:
        json.dump(raw_json, f, ensure_ascii=False, indent=2)
    print(f"💾 저장: {raw_path}")
    
    # Canonical JSON
    canonical_path = output_dir / f"{base_name}_{report_type}_canonical.json"
    with open(canonical_path, "w", encoding="utf-8") as f:
        json.dump(canonical_report.model_dump(mode='json'), f, ensure_ascii=False, indent=2, default=str)
    print(f"💾 저장: {canonical_path}")
    
    # Chunks JSON
    chunks_path = output_dir / f"{base_name}_{report_type}_chunks.json"
    with open(chunks_path, "w", encoding="utf-8") as f:
        json.dump(chunks, f, ensure_ascii=False, indent=2, default=str)
    print(f"💾 저장: {chunks_path}")
    
    return True


def main():
    """모든 보고서 처리"""
    print("="*70)
    print("🚀 전체 보고서 파싱 및 청킹 시작")
    print("="*70)
    
    # .env 파일 로드
    load_dotenv()
    
    # 서비스 초기화
    service = ReportProcessingService()
    
    # 처리할 보고서 목록
    reports = [
        "Data/reports/일일 업무 보고서.pdf",
        "Data/reports/주간 업무 보고서.pdf",
        "Data/reports/월간 업무 보고서.pdf",
        "Data/reports/실적 보고서 양식.pdf"
    ]
    
    success_count = 0
    fail_count = 0
    
    for report_path in reports:
        try:
            if process_report(report_path, service):
                success_count += 1
            else:
                fail_count += 1
        except Exception as e:
            print(f"❌ 오류 발생: {e}")
            fail_count += 1
    
    # 최종 요약
    print(f"\n{'='*70}")
    print("✅ 전체 처리 완료")
    print("="*70)
    print(f"성공: {success_count}개")
    print(f"실패: {fail_count}개")
    print()
    print("💡 다음 단계:")
    print("  python ingestion/init_ingest.py  # 모든 청크를 로컬 ChromaDB에 업로드")
    print()


if __name__ == "__main__":
    main()

