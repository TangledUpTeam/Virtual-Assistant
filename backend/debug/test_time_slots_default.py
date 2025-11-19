"""
시간대 기본값 테스트

서비스 기본 시간대(09:00~18:00)가 제대로 생성되는지 확인

실행 방법:
    python -m debug.test_time_slots_default
"""
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from app.domain.daily.time_slots import generate_time_slots


def test_default_slots():
    """기본값 테스트"""
    print("="*80)
    print(" 서비스 기본 시간대 테스트")
    print("="*80)
    print()
    
    # 기본값으로 생성 (09:00~18:00, 60분 간격)
    slots = generate_time_slots()
    
    print(f"기본값으로 생성된 시간대: {len(slots)}개")
    print()
    
    print("생성된 시간대 목록:")
    for i, slot in enumerate(slots, 1):
        print(f"  [{i:2d}] {slot}")
    
    print()
    print("="*80)
    print(f"[OK] 기본 시간대: 09:00~18:00 (총 {len(slots)}개 슬롯)")
    print("="*80)
    
    # 예상: 09:00~10:00, 10:00~11:00, ..., 17:00~18:00 = 9개
    assert len(slots) == 9, f"예상 9개, 실제 {len(slots)}개"
    assert slots[0] == "09:00~10:00"
    assert slots[-1] == "17:00~18:00"
    
    print("\n[OK] 모든 검증 통과!")


if __name__ == "__main__":
    test_default_slots()

