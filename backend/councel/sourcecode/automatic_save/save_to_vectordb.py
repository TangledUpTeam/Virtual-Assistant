"""
Vector DB 저장 스크립트
생성날짜: 2025.11.18
설명: rogers/embedding 폴더의 임베딩 파일들을 ChromaDB에 저장
"""

import os
import json
import sys
from pathlib import Path
from typing import List, Dict, Any
import chromadb
from chromadb.config import Settings

# Vector DB 매니저
class VectorDBManager:
    def __init__(self, db_path: str):

        # 경로 설정
        self.db_path = Path(db_path) # Vector DB 저장 경로
        self.db_path.mkdir(parents=True, exist_ok=True) # 경로가 없으면 폴더 생성
        
        # ChromaDB 클라이언트 초기화
        self.client = chromadb.PersistentClient( # PersistentClient: 파일을 영구적으로 저장
            path=str(self.db_path), # 경로
            settings=Settings( # 세팅
                anonymized_telemetry=False, # 중복 추적 방지
                allow_reset=True # 컬렉션 재생성 허용, 개발/테스트 단계에서만 True
            )
        )
    
    # 임베딩 파일 로드
    # 밑에 있는 주석은 디버깅 과정에서만 남겨놓고 나중에 삭제 예정
    def load_embedding_file(self, filepath: Path) -> List[Dict[str, Any]]:

        try:
            with open(filepath, 'r', encoding='utf-8') as file:
                data = json.load(file) # Json 파일 로드 후 data에 저장
            return data
        except FileNotFoundError:
            print(f"[ERROR] 파일을 찾을 수 없습니다: {filepath}")
            raise
        except json.JSONDecodeError as e:
            print(f"[ERROR] JSON 파싱 오류: {filepath} - {e}")
            raise
        except Exception as e:
            print(f"[ERROR] 파일 로드 오류: {filepath} - {e}")
            raise
    
    # 컬렉션 생성 또는 재생성
    def create_or_reset_collection(self, collection_name: str):

        try:
            
            try:
                self.client.delete_collection(name=collection_name) # 기존 컬렉션이 있으면 삭제
            except Exception:
                pass  # 컬렉션이 없으면 무시
            
            # 새 컬렉션 생성
            collection = self.client.create_collection(
                name=collection_name, # 컬렉션 이름은 매개변수로 전달해준 이름 사용
                metadata={"hnsw:space": "cosine"}  # 코사인 유사도 사용
            )

            return collection
        
        except Exception as e:
            print(f"[ERROR] 컬렉션 생성 오류: {collection_name} - {e}") # 이 부분도 나중에 삭제 예정
            raise
    
    # 컬렉션 저장 함수
    def save_to_collection(self, collection_name: str, data: List[Dict[str, Any]]):

        try:
            # 컬렉션 생성/재생성
            collection = self.create_or_reset_collection(collection_name)
            
            # 데이터 준비
            ids = [] # id
            embeddings = [] # 임베딩 데이터
            documents = [] # 문서 데이터
            metadatas = [] # 메타데이터 
            
            for item in data:

                # 각 리스트에 데이터 추가
                ids.append(item['id'])
                embeddings.append(item['embedding'])
                documents.append(item['text'])
                
                # 메타데이터 처리 (ChromaDB는 list를 지원하지 않으므로 변환)
                metadata = item['metadata'].copy()
                if 'tags' in metadata and isinstance(metadata['tags'], list): # tags가 리스트 형태면 문자열로 변환
                    metadata['tags'] = ', '.join(metadata['tags'])  # 리스트를 문자열로 변환
                metadatas.append(metadata)
            
            # 배치로 저장 (ChromaDB는 한 번에 많은 데이터를 처리할 수 있음)
            batch_size = 1000
            total_batches = (len(ids) + batch_size - 1) // batch_size # 배치 수 계산
            
            for i in range(0, len(ids), batch_size):
                batch_num = i // batch_size + 1
                end_idx = min(i + batch_size, len(ids)) # 끝 인덱스
                
                # 컬렉션에 앞에서 저장한 데이터들 추가
                collection.add(
                    ids=ids[i:end_idx],
                    embeddings=embeddings[i:end_idx],
                    documents=documents[i:end_idx],
                    metadatas=metadatas[i:end_idx]
                )
            
            return collection
        
        except Exception as e:
            print(f"[ERROR] 데이터 저장 오류: {collection_name} - {e}") # 나중에 삭제 예정
            raise
    
    # 컬렉션 검증 함수
    # 상태 및 무결성 보장 역할
    def verify_collection(self, collection_name: str):

        try:
            collection = self.client.get_collection(name=collection_name) # 컬렉션 이름으로 해당 컬렉션 가져오기
            count = collection.count() # 컬렉션 안에 있는 데이터 개수 가지고 오기
            
            # 샘플 데이터 조회
            sample = collection.peek(limit=1) # 컬렉션 안에 있는 데이터들 중 하나 샘플로 가지고오기
            if sample['ids']: # ids가 있으면 샘플 아이디 출력
                print(f"  샘플 ID: {sample['ids'][0]}") # 나중에 삭제 예정
            
            return count
        
        except Exception as e:
            print(f"[ERROR] 컬렉션 검증 오류: {collection_name} - {e}") # 나중에 삭제 예정
            raise


def main():

    # 경로 설정 (sourcecode/automatic_save 기준)
    base_dir = Path(__file__).parent.parent.parent # councel 폴더
    embedding_dir = base_dir / "dataset" / "rogers" / "embedding"
    vector_db_dir = base_dir / "vector_db"
    
    # 입력 디렉토리 확인
    if not embedding_dir.exists():
        print(f"[ERROR] 오류: 입력 디렉토리가 존재하지 않습니다: {embedding_dir}") # 나중에 삭제 예정
        sys.exit(1) # 오류 발생시 종료
    
    try:
        # Vector DB 매니저 초기화
        db_manager = VectorDBManager(str(vector_db_dir))
        
        # 임베딩 파일 매핑
        file_mappings = []
        
        # 파일명에 'phr'이 포함되면 의미기반, 아니면 문단기반 
        # 의미 기반 컬렉션명: semantic_vec / 문단 기반 컬렉션명: paragraph_vec
        for emb_file in embedding_dir.glob("*.json"):

            # 파일명에 phr이 포함되어있는지 확인
            if "phr" in emb_file.stem.lower():
                collection_name = "semantic_vec"
                file_type = "의미기반"
            else:
                collection_name = "paragraph_vec"
                file_type = "문단기반"
            
            # 파일 매핑 리스트에 추가
            file_mappings.append({
                "file": emb_file, # 임베딩 파일
                "collection": collection_name, # 컬렉션 이름
                "type": file_type # 파일 타입
            })
        
        # 파일 매핑이 실패할 경우
        if not file_mappings:
            print("[ERROR] 오류: 임베딩 파일을 찾을 수 없습니다.") # 나중에 삭제 예정
            sys.exit(1) # 오류 발생시 종료
        
        # 각 파일 처리
        results = {}
        
        for mapping in file_mappings:
            
            # 데이터 로드
            data = db_manager.load_embedding_file(mapping['file'])
            
            # Vector DB에 저장
            db_manager.save_to_collection(mapping['collection'], data)
            
            # 결과 저장
            results[mapping['collection']] = len(data)
        
        # 검증
        
        # 만들어진 컬렉션 검증
        for collection_name in results.keys():
            db_manager.verify_collection(collection_name)
        
        # 최종 결과
        for collection_name, count in results.items():
            print(f"  - {collection_name}: {count}개 항목") # 나중에 삭제 예정, 임시로 확인용도
        
    # 작업 중단 시 예외처리    
    except KeyboardInterrupt:
        print("\n\n작업이 사용자에 의해 중단되었습니다.") # 나중에 삭제 예정
        sys.exit(1)
    
    # 예외처리
    except Exception as e:
        print(f"\n[ERROR] 치명적 오류 발생: {e}") # 나중에 삭제 예정
        import traceback # 예외 추적
        traceback.print_exc() # 예외 추적 결과 출력
        sys.exit(1)


if __name__ == "__main__":
    main()

