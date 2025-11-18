"""
통합 Canonical 파이프라인 테스트 스크립트

전체 변환 프로세스를 테스트합니다:
- CanonicalReport → UnifiedCanonical
- CanonicalKPI → UnifiedCanonical
- UnifiedCanonical → Chunks

사용법:
    python -m debug.test_unified_pipeline
"""
import sys
from pathlib import Path
from datetime import date

# 프로젝트 루트 설정
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from app.domain.report.schemas import CanonicalReport, TaskItem, KPIItem
from app.domain.kpi.schemas import CanonicalKPI
from app.services.canonical.merge_normalizer import (
    report_to_unified,
    kpi_to_unified,
    text_to_unified
)
from app.domain.common.unified_chunker import chunk_unified, get_chunk_statistics


def test_report_to_unified():
    """CanonicalReport → UnifiedCanonical 변환 테스트"""
    print("=" * 80)
    print("Test 1: CanonicalReport → UnifiedCanonical")
    print("=" * 80)
    print()
    
    # 샘플 CanonicalReport 생성
    canonical_report = CanonicalReport(
        report_id="test_daily_001",
        report_type="daily",
        owner="김보험",
        period_start=date(2024, 11, 1),
        period_end=None,
        tasks=[
            TaskItem(
                task_id="task_1",
                title="고객 상담",
                description="이** 고객 실손 갱신 상담",
                time_start="09:00",
                time_end="10:00",
                status="완료",
                note=""
            ),
            TaskItem(
                task_id="task_2",
                title="보장 분석",
                description="현재 보험 보장 범위 검토",
                time_start="10:00",
                time_end="11:00",
                status="진행중",
                note=""
            )
        ],
        kpis=[
            KPIItem(
                kpi_name="상담 건수",
                value="3",
                unit="건",
                category="영업",
                note=""
            )
        ],
        issues=["박** 고객 청구 확인 대기"],
        plans=["암보험 설계안 전달 및 실손 문의 대응"],
        metadata={"source_file": "test.txt"}
    )
    
    # UnifiedCanonical로 변환
    unified = report_to_unified(canonical_report)
    
    print(f"✅ 변환 성공")
    print(f"   - doc_id: {unified.doc_id}")
    print(f"   - doc_type: {unified.doc_type}")
    print(f"   - title: {unified.title}")
    print(f"   - single_date: {unified.single_date}")
    print(f"   - owner: {unified.owner}")
    print(f"   - tasks: {len(unified.sections.tasks)}개")
    print(f"   - kpis: {len(unified.sections.kpis)}개")
    print(f"   - issues: {len(unified.sections.issues)}개")
    print(f"   - plans: {len(unified.sections.plans)}개")
    
    # JSON 직렬화 테스트
    try:
        json_str = unified.model_dump_json(indent=2)
        print(f"   - JSON 직렬화: 성공 ({len(json_str)} bytes)")
    except Exception as e:
        print(f"   - JSON 직렬화: 실패 ({e})")
    print()
    
    return unified


def test_kpi_to_unified():
    """CanonicalKPI → UnifiedCanonical 변환 테스트"""
    print("=" * 80)
    print("Test 2: CanonicalKPI → UnifiedCanonical")
    print("=" * 80)
    print()
    
    # 샘플 CanonicalKPI 생성
    canonical_kpi = CanonicalKPI(
        kpi_id="kpi_test_001",
        page_index=1,
        kpi_name="신규 계약 건수",
        category="영업 실적",
        unit="건",
        values="125",
        delta="+15%",
        description="전월 대비 신규 계약 건수 증가",
        table=None,
        raw_text_summary="2024년 11월 영업 실적 개선",
        metadata={"source": "KPI 자료.pdf"}
    )
    
    # UnifiedCanonical로 변환
    unified = kpi_to_unified(canonical_kpi)
    
    print(f"✅ 변환 성공")
    print(f"   - doc_id: {unified.doc_id}")
    print(f"   - doc_type: {unified.doc_type}")
    print(f"   - title: {unified.title}")
    print(f"   - kpis: {len(unified.sections.kpis)}개")
    print(f"   - summary: {unified.sections.summary}")
    print()
    
    return unified


def test_text_to_unified():
    """Raw Text → UnifiedCanonical 변환 테스트"""
    print("=" * 80)
    print("Test 3: Raw Text → UnifiedCanonical")
    print("=" * 80)
    print()
    
    # 샘플 텍스트
    raw_text = """
    보험 업무 가이드라인
    
    1. 고객 상담 시 주의사항
       - 고객의 현재 보험 상태 파악
       - 보장 범위 상세 설명
       - 청약서 작성 지원
    
    2. 청구 처리 절차
       - 필요 서류 안내
       - 청구서 접수
       - 보험금 지급 확인
    """
    
    # UnifiedCanonical로 변환
    unified = text_to_unified(
        text=raw_text,
        title="보험 업무 가이드라인",
        source_file="guide.pdf",
        doc_type="template"
    )
    
    print(f"✅ 변환 성공")
    print(f"   - doc_id: {unified.doc_id}")
    print(f"   - doc_type: {unified.doc_type}")
    print(f"   - title: {unified.title}")
    print(f"   - raw_text 길이: {len(unified.raw_text)}자")
    print()
    
    return unified


def test_chunking(unified):
    """UnifiedCanonical → Chunks 변환 테스트"""
    print("=" * 80)
    print("Test 4: UnifiedCanonical → Chunks")
    print("=" * 80)
    print()
    
    # 청킹
    chunks = chunk_unified(unified, include_summary=True)
    
    print(f"✅ 청킹 성공")
    print(f"   - 총 청크 수: {len(chunks)}개")
    print()
    
    # 청크 상세 정보
    print("📊 청크 상세:")
    for i, chunk in enumerate(chunks[:5], 1):  # 처음 5개만
        metadata = chunk['metadata']
        print(f"   {i}. ID: {chunk['id'][:16]}...")
        print(f"      타입: {metadata.get('chunk_type')}")
        print(f"      텍스트 길이: {len(chunk['text'])}자")
        print(f"      텍스트 미리보기: {chunk['text'][:50]}...")
        print()
    
    if len(chunks) > 5:
        print(f"   ... 외 {len(chunks) - 5}개 청크")
        print()
    
    # 통계
    stats = get_chunk_statistics(chunks)
    print("📈 청크 통계:")
    print(f"   - 총 청크 수: {stats['total_chunks']}")
    print(f"   - 청크 타입별:")
    for chunk_type, count in stats["chunk_types"].items():
        print(f"     • {chunk_type}: {count}")
    print(f"   - 평균 텍스트 길이: {stats['avg_text_length']:.1f}자")
    print(f"   - 최대 텍스트 길이: {stats['max_text_length']}자")
    print(f"   - 최소 텍스트 길이: {stats['min_text_length']}자")
    print()
    
    return chunks


def main():
    """메인 테스트 함수"""
    print()
    print("=" * 80)
    print("🧪 통합 Canonical 파이프라인 테스트")
    print("=" * 80)
    print()
    
    try:
        # Test 1: Report 변환
        report_unified = test_report_to_unified()
        
        # Test 2: KPI 변환
        kpi_unified = test_kpi_to_unified()
        
        # Test 3: Text 변환
        text_unified = test_text_to_unified()
        
        # Test 4: Report 청킹
        report_chunks = test_chunking(report_unified)
        
        # Test 5: KPI 청킹
        kpi_chunks = test_chunking(kpi_unified)
        
        print("=" * 80)
        print("✅ 모든 테스트 통과!")
        print("=" * 80)
        print(f"Report 청크: {len(report_chunks)}개")
        print(f"KPI 청크: {len(kpi_chunks)}개")
        print()
        print("통합 Canonical 파이프라인이 정상 작동합니다.")
        print()
    
    except Exception as e:
        print()
        print("=" * 80)
        print(f"❌ 테스트 실패: {e}")
        print("=" * 80)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

