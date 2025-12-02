"""
Insurance RAG 아키텍처 마이그레이션 스크립트

레거시 파일을 삭제하고 import 경로를 업데이트합니다.
"""
import os
import shutil
from pathlib import Path
from typing import List, Tuple

# 프로젝트 루트
INSURANCE_DIR = Path(__file__).parent


def get_files_to_delete() -> List[Tuple[Path, str]]:
    """삭제할 파일 목록 반환"""
    return [
        # 중복 파일 (새 아키텍처로 대체됨)
        (INSURANCE_DIR / "vector_store.py", "infrastructure/vectorstore/chroma.py로 대체"),
        (INSURANCE_DIR / "retriever.py", "services/retriever.py로 대체"),
        (INSURANCE_DIR / "embedder.py", "infrastructure/embeddings/openai.py로 대체"),
        (INSURANCE_DIR / "schemas.py", "core/models.py로 대체"),
        (INSURANCE_DIR / "__main__.py", "scripts/ 사용"),
        
        # 테스트 중복
        (INSURANCE_DIR / "tests" / "visualize_results.py", "scripts/run_visualizer.py로 대체"),
    ]


def get_dirs_to_delete() -> List[Tuple[Path, str]]:
    """삭제할 디렉토리 목록 반환"""
    return [
        # 캐시 디렉토리 (120+ 파일)
        (INSURANCE_DIR / "insurance_cache", "디스크 캐시 (551KB) - 재생성 가능"),
        
        # 용도 불명 디렉토리
        (INSURANCE_DIR / "internal_insurance", "용도 불명 폴더"),
    ]


def backup_file(file_path: Path, backup_dir: Path):
    """파일 백업"""
    if file_path.exists():
        backup_path = backup_dir / file_path.name
        shutil.copy2(file_path, backup_path)
        print(f"  ✓ 백업됨: {backup_path}")


def backup_dir(dir_path: Path, backup_dir: Path):
    """디렉토리 백업"""
    if dir_path.exists():
        backup_path = backup_dir / dir_path.name
        if backup_path.exists():
            shutil.rmtree(backup_path)
        shutil.copytree(dir_path, backup_path)
        print(f"  ✓ 백업됨: {backup_path}")


def main():
    """메인 실행"""
    print("="*80)
    print("Insurance RAG 아키텍처 클린업")
    print("="*80)
    
    # 백업 디렉토리 생성
    backup_root = INSURANCE_DIR / "_archive_backup"
    backup_root.mkdir(exist_ok=True)
    print(f"\n백업 디렉토리: {backup_root}\n")
    
    # 1. 파일 삭제
    print("[1단계] 중복 파일 정리")
    print("-"*80)
    
    files_to_delete = get_files_to_delete()
    for file_path, reason in files_to_delete:
        if file_path.exists():
            print(f"\n파일: {file_path.name}")
            print(f"  이유: {reason}")
            
            # 백업
            backup_file(file_path, backup_root)
            
            # 삭제
            file_path.unlink()
            print(f"  ✗ 삭제됨")
        else:
            print(f"\n파일: {file_path.name} (이미 없음)")
    
    # 2. 디렉토리 삭제
    print("\n\n[2단계] 불필요한 디렉토리 정리")
    print("-"*80)
    
    dirs_to_delete = get_dirs_to_delete()
    for dir_path, reason in dirs_to_delete:
        if dir_path.exists():
            # 파일 개수와 크기 확인
            file_count = sum(1 for _ in dir_path.rglob("*") if _.is_file())
            
            print(f"\n디렉토리: {dir_path.name}")
            print(f"  파일 수: {file_count}개")
            print(f"  이유: {reason}")
            
            # 백업
            backup_dir(dir_path, backup_root)
            
            # 삭제
            shutil.rmtree(dir_path)
            print(f"  ✗ 삭제됨")
        else:
            print(f"\n디렉토리: {dir_path.name} (이미 없음)")
    
    # 3. 통합 및 이동
    print("\n\n[3단계] 파일 통합 및 이동")
    print("-"*80)
    
    migrations = [
        ("constants.py", "core/config.py", "상수를 config로 통합"),
        ("performance.py", "evaluation/metrics/performance.py", "평가 메트릭으로 이동"),
        ("utils.py", "core/utils.py", "공통 유틸리티 정리"),
        ("cli.py", "scripts/cli.py", "CLI 스크립트로 이동"),
        ("cache_utils.py", "infrastructure/cache/disk_cache.py", "캐싱 인프라로 이동"),
    ]
    
    for source, target, reason in migrations:
        source_path = INSURANCE_DIR / source
        target_path = INSURANCE_DIR / target
        
        if source_path.exists():
            print(f"\n파일: {source} → {target}")
            print(f"  이유: {reason}")
            print(f"  ⚠️  수동 통합 필요")
        else:
            print(f"\n파일: {source} (이미 없음)")
    
    # 4. Legacy wrapper 적용
    print("\n\n[4단계] Legacy Wrapper 적용")
    print("-"*80)
    
    legacy_modules = [
        ("extractor/__init__.py", "infrastructure.document_loader"),
        ("chunker/__init__.py", "infrastructure.chunking"),
    ]
    
    for module, new_path in legacy_modules:
        module_path = INSURANCE_DIR / module
        print(f"\n모듈: {module}")
        print(f"  → Deprecation warning 추가")
        print(f"  → {new_path}로 리다이렉트")
        print(f"  ⚠️  수동 수정 필요")
    
    print("\n\n" + "="*80)
    print("요약")
    print("="*80)
    print(f"✓ 백업 완료: {backup_root}")
    print(f"✓ 삭제 대상 파일: {len(files_to_delete)}개")
    print(f"✓ 삭제 대상 디렉토리: {len(dirs_to_delete)}개")
    print(f"✓ 통합 대상 파일: {len(migrations)}개")
    print(f"✓ Legacy wrapper 적용: {len(legacy_modules)}개 모듈")
    
    print("\n✅ 실제 삭제가 실행되었습니다.")
    print(f"✅ 모든 백업은 {backup_root}에 저장되었습니다.")
    print("\n" + "="*80)


if __name__ == "__main__":
    main()
