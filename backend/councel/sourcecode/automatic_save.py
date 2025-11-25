"""
자동 저장 통합 스크립트
생성날짜: 2025.11.24
설명: 청크 생성, 임베딩 생성, Vector DB 저장을 순차적으로 실행하는 통합 스크립트
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path
from typing import Tuple, Optional

# 자동 저장 관리 클래스
class AutomaticSaveManager:
    
    def __init__(self):
        # 기본 경로 설정
        self.base_dir = Path(__file__).parent.parent
        self.dataset_dir = self.base_dir / "dataset" / "adler"
        self.chunkfiles_dir = self.dataset_dir / "chunkfiles"
        self.embeddings_dir = self.dataset_dir / "embeddings"
        self.vector_db_dir = self.base_dir / "vector_db"
        
        # 스크립트 경로 설정
        self.scripts_dir = Path(__file__).parent / "automatic_save"
        self.chunk_script = self.scripts_dir / "create_chunk_files.py"
        self.embedding_script = self.scripts_dir / "create_openai_embeddings.py"
        self.vectordb_script = self.scripts_dir / "save_to_vectordb.py"
        
        # 롤백을 위한 생성된 디렉토리 추적
        self.created_dirs = []
    
    # 폴더와 파일 존재 여부 확인 -> 없으면 생성 있으면 건너뛰기
    def check_folder_and_files(self, folder_path: Path, file_pattern: str = "*") -> Tuple[bool, bool]:

        # 폴더 여부 확인 -> 존재하면 True, 없으면 false
        folder_exists = folder_path.exists()
        files_exist = False
        
        # 폴더가 존재할 경우 파일 여부 확인
        if folder_exists:
            files = list(folder_path.glob(file_pattern))
            files_exist = len(files) > 0 # 파일이 있으면 True, 없으면 False
        
        return folder_exists, files_exist
    
    # 폴더가 없으면 폴더 생성
    def create_folder_if_not_exists(self, folder_path: Path) -> None:

        if not folder_path.exists():
            folder_path.mkdir(parents=True, exist_ok=True)
            self.created_dirs.append(folder_path)
    
    # 에러 발생 시 생성된 폴더 및 파일 삭제
    def rollback(self) -> None:
        
        for dir_path in reversed(self.created_dirs):
            if dir_path.exists():
                try:
                    shutil.rmtree(dir_path)
                except Exception as e:
                    print(f"삭제 실패: {dir_path} - {e}") # 배포 전 삭제 예정
    
    # Python 스크립트 실행
    def run_script(self, script_path: Path) -> bool:

        # 스크립트 파일이 없으면 False 리턴
        if not script_path.exists():
            print(f"오류: 스크립트 파일을 찾을 수 없습니다: {script_path}") # 배포 전 삭제 예정
            return False
        
        try:
            # Python 인터프리터로 스크립트 실행
            result = subprocess.run(
                [sys.executable, str(script_path)],
                cwd=str(script_path.parent),
                capture_output=False,
                text=True
            )
            return result.returncode == 0
        except Exception as e:
            print(f"스크립트 실행 중 오류: {e}") # 배포 전 삭제 예정
            return False
    
    # 청크 파일 생성 함수(create_chunk_files.py 실행)
    def step1_create_chunks(self) -> bool:

        print("Step 1: 청크 파일 생성")

        # 폴더 및 파일 확인
        folder_exists, files_exist = self.check_folder_and_files(
            self.chunkfiles_dir, 
            "*_chunks.json"
        )
        
        # 폴더가 있고 파일도 있으면 건너뛰기
        if folder_exists and files_exist:
            print("청크 파일이 이미 존재합니다. 건너뛰기...")
            return True
        
        # 폴더가 없으면 생성
        if not folder_exists:
            self.create_folder_if_not_exists(self.chunkfiles_dir)
        
        # 청크 파일 생성 실행
        try:
            print("\n청크 파일 생성 시작...")
            if self.run_script(self.chunk_script):
                print("\n청크 파일 생성 완료!")
                return True
            else:
                print("\n청크 파일 생성 실패!")
                return False
        except Exception as e:
            print(f"\n청크 파일 생성 중 오류 발생: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def step2_create_embeddings(self) -> bool:
        """
        Step 2: 임베딩 파일 생성
        
        Returns:
            성공 여부
        """
        print("\n" + "="*60)
        print("Step 2: 임베딩 파일 생성")
        print("="*60)
        
        # 폴더 및 파일 확인
        folder_exists, files_exist = self.check_folder_and_files(
            self.embeddings_dir,
            "*_embeddings.json"
        )
        
        # 폴더가 있고 파일도 있으면 건너뛰기
        if folder_exists and files_exist:
            print("임베딩 파일이 이미 존재합니다. 건너뛰기...")
            return True
        
        # 폴더가 없으면 생성
        if not folder_exists:
            self.create_folder_if_not_exists(self.embeddings_dir)
        
        # 임베딩 파일 생성 실행
        try:
            print("\n임베딩 파일 생성 시작...")
            if self.run_script(self.embedding_script):
                print("\n임베딩 파일 생성 완료!")
                return True
            else:
                print("\n임베딩 파일 생성 실패!")
                return False
        except Exception as e:
            print(f"\n임베딩 파일 생성 중 오류 발생: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def step3_save_to_vectordb(self) -> bool:
        """
        Step 3: Vector DB에 저장
        
        Returns:
            성공 여부
        """
        print("\n" + "="*60)
        print("Step 3: Vector DB에 저장")
        print("="*60)
        
        # Vector DB 폴더 확인
        folder_exists = self.vector_db_dir.exists()
        
        # 폴더가 있으면 컬렉션 확인
        if folder_exists:
            try:
                import chromadb
                from chromadb.config import Settings
                
                client = chromadb.PersistentClient(
                    path=str(self.vector_db_dir),
                    settings=Settings(
                        anonymized_telemetry=False,
                        allow_reset=False
                    )
                )
                
                # 컬렉션 존재 여부 확인
                try:
                    collection = client.get_collection(name="vector_adler")
                    count = collection.count()
                    if count > 0:
                        print(f"Vector DB에 이미 데이터가 존재합니다 ({count}개). 건너뛰기...")
                        return True
                except Exception:
                    # 컬렉션이 없으면 계속 진행
                    pass
            except Exception as e:
                print(f"Vector DB 확인 중 오류: {e}")
        
        # 폴더가 없으면 생성
        if not folder_exists:
            self.create_folder_if_not_exists(self.vector_db_dir)
        
        # Vector DB 저장 실행
        try:
            print("\nVector DB 저장 시작...")
            if self.run_script(self.vectordb_script):
                print("\nVector DB 저장 완료!")
                return True
            else:
                print("\nVector DB 저장 실패!")
                return False
        except Exception as e:
            print(f"\nVector DB 저장 중 오류 발생: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def run(self) -> bool:
        """
        전체 프로세스 실행
        
        Returns:
            성공 여부
        """
        print("\n" + "="*60)
        print("자동 저장 프로세스 시작")
        print("="*60)
        
        try:
            # Step 1: 청크 파일 생성
            if not self.step1_create_chunks():
                raise Exception("청크 파일 생성 실패")
            
            # Step 2: 임베딩 파일 생성
            if not self.step2_create_embeddings():
                raise Exception("임베딩 파일 생성 실패")
            
            # Step 3: Vector DB 저장
            if not self.step3_save_to_vectordb():
                raise Exception("Vector DB 저장 실패")
            
            # 성공
            print("\n" + "="*60)
            print("전체 프로세스 완료!")
            print("="*60)
            return True
            
        except Exception as e:
            print(f"\n프로세스 실패: {e}")
            self.rollback()
            return False


def automatic_save() -> bool:
    """
    외부에서 호출 가능한 함수
    
    Returns:
        성공 여부
    """
    manager = AutomaticSaveManager()
    return manager.run()


def main():
    """메인 함수 (단독 실행용)"""
    success = automatic_save()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

