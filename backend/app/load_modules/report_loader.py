"""
보고서 모듈 초기화

ChromaDB에 보고서 데이터가 없으면 자동으로 목업 데이터를 로드합니다.
이미 있으면 스킵합니다.
"""

import os
import subprocess
import sys
from pathlib import Path

# 프로젝트 루트 경로 설정
BASE_DIR = Path(__file__).resolve().parent.parent.parent  # backend/


def check_chromadb_has_data() -> bool:
    """
    ChromaDB reports 컬렉션에 데이터가 있는지 확인
    
    Returns:
        bool: 데이터가 있으면 True, 없거나 확인 실패하면 False
    """
    try:
        from app.infrastructure.vector_store_report import get_report_vector_store
        
        vector_store = get_report_vector_store()
        collection = vector_store.get_collection()
        count = collection.count()
        
        return count > 0
    except Exception as e:
        print(f"   ⚠️  ChromaDB 확인 실패: {e}")
        return False


def run_ingestion() -> bool:
    """
    ingestion 모듈 실행
    
    Returns:
        bool: 성공 여부
    """
    try:
        # REPORT_OWNER 환경변수 설정 (기본값: "김준경")
        env = os.environ.copy()
        if "REPORT_OWNER" not in env or not env["REPORT_OWNER"]:
            env["REPORT_OWNER"] = "김준경"
        
        # Python 실행 경로
        python_exe = sys.executable
        
        # ingestion 모듈 실행
        # backend 디렉토리에서 실행해야 하므로 cwd 설정
        result = subprocess.run(
            [python_exe, "-m", "ingestion.ingest_mock_reports"],
            cwd=str(BASE_DIR),
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8"
        )
        
        if result.returncode == 0:
            print("   ✅ Ingestion 완료")
            if result.stdout:
                # 출력이 있으면 마지막 몇 줄만 표시
                lines = result.stdout.strip().split('\n')
                for line in lines[-5:]:
                    if line.strip():
                        print(f"      {line}")
            return True
        else:
            print(f"   ❌ Ingestion 실패 (exit code: {result.returncode})")
            if result.stderr:
                print(f"      오류: {result.stderr[:200]}")
            return False
            
    except Exception as e:
        print(f"   ❌ Ingestion 실행 오류: {e}")
        return False


def init_reports() -> bool:
    """
    보고서 RAG 초기화
    
    - ChromaDB 컬렉션이 비어있으면: ingestion 실행
    - 이미 데이터가 있으면: 스킵
    
    Returns:
        bool: 성공 여부
    """
    print("\n📊 [보고서] RAG 초기화 체크...")
    
    # 1. ChromaDB 데이터 확인
    try:
        has_data = check_chromadb_has_data()
        
        if has_data:
            print("   ✅ 이미 데이터 존재 - 스킵")
            return True
        else:
            print("   📝 데이터 없음 - Ingestion 시작")
    except Exception as e:
        print(f"   ⚠️  ChromaDB 확인 실패, Ingestion 실행: {e}")
        # 확인 실패 시에도 ingestion 실행 (fallback)
    
    # 2. Ingestion 실행
    print("   🔄 목업 데이터 로드 중...")
    success = run_ingestion()
    
    if success:
        print("   ✅ 보고서 RAG 초기화 완료")
        return True
    else:
        print("   ⚠️  보고서 RAG 초기화 실패")
        return False


# 직접 실행 테스트
if __name__ == "__main__":
    success = init_reports()
    print(f"\n결과: {'성공' if success else '실패'}")

