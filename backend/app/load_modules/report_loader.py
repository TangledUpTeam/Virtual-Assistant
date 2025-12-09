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
    ingestion 모듈 실행 (ChromaDB + PostgreSQL)
    
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
        project_root = BASE_DIR.parent  # Virtual-Assistant 루트
        env["PYTHONPATH"] = str(project_root) + os.pathsep + env.get("PYTHONPATH", "")
        
        print(f"   📍 실행 경로: {BASE_DIR}")
        print(f"   📍 Python: {python_exe}")
        print(f"   📍 REPORT_OWNER: {env.get('REPORT_OWNER', 'N/A')}")
        
        # 1. ChromaDB ingestion
        print("   🔄 ChromaDB 목업 데이터 로드 중...")
        result1 = subprocess.run(
            [python_exe, "-m", "ingestion.ingest_mock_reports"],
            cwd=str(BASE_DIR),
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8"
        )
        
        if result1.returncode != 0:
            print(f"   ❌ ChromaDB Ingestion 실패 (exit code: {result1.returncode})")
            if result1.stderr:
                print(f"      오류 메시지:")
                for line in result1.stderr.strip().split('\n'):
                    if line.strip():
                        print(f"         {line}")
            if result1.stdout:
                print(f"      stdout:")
                for line in result1.stdout.strip().split('\n')[-10:]:
                    if line.strip():
                        print(f"         {line}")
            return False
        
        print("   ✅ ChromaDB Ingestion 완료")
        if result1.stdout:
            # 출력이 있으면 마지막 몇 줄만 표시
            lines = result1.stdout.strip().split('\n')
            for line in lines[-3:]:
                if line.strip():
                    print(f"      {line}")
        
        # 2. PostgreSQL ingestion
        print("   🔄 PostgreSQL 목업 데이터 로드 중...")
        bulk_ingest_script = BASE_DIR / "tools" / "bulk_daily_ingest.py"
        
        result2 = subprocess.run(
            [python_exe, str(bulk_ingest_script)],
            cwd=str(project_root),  # 프로젝트 루트에서 실행
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8"
        )
        
        if result2.returncode != 0:
            print(f"   ⚠️  PostgreSQL Ingestion 실패 (exit code: {result2.returncode})")
            if result2.stderr:
                print(f"      오류 메시지:")
                for line in result2.stderr.strip().split('\n'):
                    if line.strip():
                        print(f"         {line}")
            if result2.stdout:
                print(f"      stdout:")
                for line in result2.stdout.strip().split('\n')[-10:]:
                    if line.strip():
                        print(f"         {line}")
            # ChromaDB는 성공했으므로 부분 성공으로 처리
            print("   ⚠️  ChromaDB는 성공했지만 PostgreSQL 초기화 실패")
            return True
        
        print("   ✅ PostgreSQL Ingestion 완료")
        if result2.stdout:
            # 출력이 있으면 전체 표시 (에러 확인을 위해)
            lines = result2.stdout.strip().split('\n')
            # 에러가 있는지 확인
            has_errors = any("에러" in line or "ERROR" in line or "❌" in line for line in lines)
            if has_errors:
                print("      전체 출력:")
                for line in lines:
                    if line.strip():
                        print(f"         {line}")
            else:
                # 에러가 없으면 마지막 몇 줄만 표시
                for line in lines[-5:]:
                    if line.strip():
                        print(f"      {line}")
        
        return True
            
    except Exception as e:
        print(f"   ❌ Ingestion 실행 오류: {e}")
        import traceback
        traceback.print_exc()
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

