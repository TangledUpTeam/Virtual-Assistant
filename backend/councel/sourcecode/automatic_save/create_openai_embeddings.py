"""
OpenAI 임베딩 모델을 사용하여 청크 파일의 임베딩을 생성하는 스크립트
생성날짜: 2025.11.21
리팩토링: 2025.11.25 - 1차 코드 리팩토링(쓸데 없는 print문 제거 및 코드 정리)
수정날짜: 2025.11.28 - Parent-Child Chunking 지원 (Parent와 Child 모두 임베딩 생성)
설명: text-embedding-3-large 모델을 사용하여 Adler 청크 파일의 임베딩 생성
      Parent와 Child 청크 모두 개별적으로 임베딩을 생성하며 메타데이터 보존
"""

import json
import os
import sys
from pathlib import Path
from typing import List, Dict, Any
from openai import OpenAI
from tqdm import tqdm
from dotenv import load_dotenv

# 프로젝트 루트 경로 설정 (.env 파일 위치)
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent
ENV_FILE = PROJECT_ROOT / ".env"

# .env 파일 로드
if ENV_FILE.exists():
    load_dotenv(ENV_FILE)
else:
    print(f"경고: .env 파일을 찾을 수 없습니다") # env파일이 있는지 없는지 확인하기 위해 남겨놓음

# 기본 경로 설정 (sourcecode/automatic_save 기준)
BASE_DIR = Path(__file__).parent.parent.parent

# 입력/출력 경로
CHUNK_DIR = BASE_DIR / "dataset" / "adler" / "chunkfiles"
OUTPUT_DIR = BASE_DIR / "dataset" / "adler" / "embeddings"

# OpenAI 설정
MODEL_NAME = "text-embedding-3-large" # OpenAI 임베딩 모델 이름
BATCH_SIZE = 100  # OpenAI API는 한 번에 여러 텍스트 처리 가능


# 청크 파일 로드 함수
# 예외처리 print문은 배포 전 삭제 예정
def load_chunks(file_path: str) -> List[Dict[str, Any]]:

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            chunks = json.load(f)
        return chunks
    except FileNotFoundError:
        print(f"파일을 찾을 수 없습니다")
        return []
    except json.JSONDecodeError as e:
        print(f"JSON 파싱 오류: {e}")
        return []
    except Exception as e:
        print(f"파일 로드 중 오류 발생: {e}")
        return []

# 임베딩 파일 생성 함수
def create_embeddings(chunks: List[Dict[str, Any]], model_name: str) -> List[List[float]]:

    try:
        # OpenAI 클라이언트 초기화 (.env 파일에서 API 키 로드)
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY가 환경 변수에 설정되지 않았습니다.")
        client = OpenAI(api_key=api_key)
        
        embeddings = []
        texts = [chunk['text'] for chunk in chunks]
        
        # 배치 단위로 처리
        for i in tqdm(range(0, len(texts), BATCH_SIZE), desc="진행률"):
            batch_texts = texts[i:i + BATCH_SIZE]
            
            try:
                # OpenAI API 호출
                response = client.embeddings.create(
                    input=batch_texts,
                    model=model_name
                )
                
                # 임베딩 추출
                batch_embeddings = [item.embedding for item in response.data]
                embeddings.extend(batch_embeddings)
                
            except Exception as e:
                print(f"\n배치 {i//BATCH_SIZE + 1} 처리 중 오류: {e}") # 배포 전 삭제 예정
                # 오류 발생 시 빈 임베딩으로 채우기
                embeddings.extend([[] for _ in batch_texts])
        
        return embeddings
        
    except Exception as e:
        print(f"임베딩 생성 중 오류 발생: {e}") # 배포 전 삭제 예정
        return []

# 생성된 임베딩 파일을 JSON 파일로 저장하는 함수
def save_embeddings(chunks: List[Dict[str, Any]], embeddings: List[List[float]], 
                   output_path: str) -> bool:

    try:
        # 출력 디렉토리 생성
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # 임베딩 추가
        result = []
        for chunk, embedding in zip(chunks, embeddings):
            chunk_with_embedding = chunk.copy()
            # 임베딩은 이미 Python 리스트 형태 (OpenAI API 반환값)
            chunk_with_embedding['embedding'] = embedding
            result.append(chunk_with_embedding)
        
        # JSON 파일로 저장
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        return True
        
    except Exception as e:
        print(f"파일 저장 중 오류 발생: {e}") # 배포 전 삭제 예정
        return False

# 메인 함수
# 쓸데 없는 print문 및 예외처리 print문은 나중에 삭제 예정
def main():
    
    # API 키 확인
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("오류: OPENAI_API_KEY가 설정되지 않았습니다.")
        return

    # 청크 파일 목록 가져오기
    if not CHUNK_DIR.exists():
        print(f"오류: 입력 디렉토리가 존재하지 않습니다")
        return
    
    chunk_files = sorted(CHUNK_DIR.glob("*_chunks.json"))
    
    if not chunk_files:
        print(f"오류: 청크 파일을 찾을 수 없습니다")
        return
    
    # 각 파일 처리
    total_processed = 0
    total_failed = 0
    
    for chunk_file in chunk_files:
        
        try:
            # 1. 청크 파일 로드
            chunks = load_chunks(str(chunk_file))
            
            if not chunks:
                print(f"건너뛰기: 청크 데이터가 없습니다.") # 배포 전 삭제 예정
                total_failed += 1
                continue
            
            # 2. 임베딩 생성
            embeddings = create_embeddings(chunks, MODEL_NAME)
            
            if not embeddings or len(embeddings) != len(chunks):
                print(f"건너뛰기: 임베딩 생성 실패") # 배포 전 삭제 예정
                total_failed += 1
                continue
            
            # 3. 출력 파일명 생성
            output_filename = chunk_file.stem.replace("_chunks", "_embeddings") + ".json"
            output_path = OUTPUT_DIR / output_filename
            
            # 4. 결과 저장
            if save_embeddings(chunks, embeddings, str(output_path)):
                total_processed += 1
            else:
                total_failed += 1
                
        except Exception as e:
            print(f"파일 처리 중 예외 발생: {e}") # 예외처리 print문은 배포 전 삭제 예정
            total_failed += 1

# 호출
if __name__ == "__main__":
    main()