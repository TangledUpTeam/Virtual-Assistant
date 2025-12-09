"""
심리 상담 모듈 초기화

Vector DB에 심리 상담 데이터가 없으면 자동 생성합니다.
이미 있으면 스킵합니다.
"""

from pathlib import Path
import sys

# 심리 상담 모듈 초기화
def init_therapy() -> bool:

    # 경로 설정
    base_dir = Path(__file__).parent.parent.parent.parent
    councel_dir = base_dir / "backend" / "councel"
    
    if str(councel_dir) not in sys.path:
        sys.path.insert(0, str(councel_dir))
    
    try:
        from sourcecode.automatic_save import automatic_save
        
        success = automatic_save()
        
        if success:
            return True
        else:
            print("초기화 실패")
            return False
            
    except Exception as e:
        print(f"초기화 오류")
        return False


# 직접 실행 테스트
if __name__ == "__main__":
    success = init_therapy()

