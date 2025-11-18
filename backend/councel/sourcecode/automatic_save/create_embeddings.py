"""
BAAI/bge-m3 모델을 사용하여 청크 파일의 임베딩을 생성하는 스크립트
생성날짜: 2025.11.17
"""

import json
import torch
from transformers import AutoModel, AutoTokenizer
from tqdm import tqdm
import numpy as np
import os

# 설정
from pathlib import Path

# 기본 경로 설정 (sourcecode/automatic_save 기준)
BASE_DIR = Path(__file__).parent.parent.parent

# 청크 파일 목록
CHUNK_FILES = [
    # str(BASE_DIR / "dataset/rogers/chunk/rogers_theory_chunks.json"),
    # str(BASE_DIR / "dataset/rogers/chunk/rogers_examples_chunks.json")
    str(BASE_DIR / "dataset/rogers/chunk/rogers_chunks_phrasing.json")
]
OUTPUT_FILE = str(BASE_DIR / "dataset/rogers/embedding/rogers_emb_phr_bge_m3.json") # 출력 파일 위치 및 파일명
MODEL_NAME = "BAAI/bge-m3" # 모델명
BATCH_SIZE = 32 # 배치 사이즈(한번에 처리하는 데이터 개수)

# mean pooling 함수
def mean_pooling(model_output, attention_mask):
    """
    Mean Pooling 전략을 사용하여 임베딩 벡터 추출
    """
    token_embeddings = model_output[0]  # 모델이 출력한 모든 토큰의 임베딩 값을 가지고 옴
    input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
    return torch.sum(token_embeddings * input_mask_expanded, 1) / torch.clamp(input_mask_expanded.sum(1), min=1e-9) # 유효한 토큰들의 벡터 값의 합 / 유효한 토큰들의 개수

# 3번째 순서: 청크파일 로드
def load_chunks(file_paths):
    """
    여러 청크 파일을 로드하여 하나의 리스트로 병합
    """
    all_chunks = []
    for file_path in file_paths:
        with open(file_path, 'r', encoding='utf-8') as file:
            chunks = json.load(file)
            all_chunks.extend(chunks) # 파일에서 로드한 청크데이터를 하나의 리스트로 병합

    return all_chunks

# 4번째 순서: 임베딩 생성
def create_embeddings(chunks, model, tokenizer, device, batch_size=32): # 배치 사이즈: 32
    """
    배치 처리를 통해 청크 텍스트의 임베딩 생성
    """
    embeddings = []
    texts = [chunk['text'] for chunk in chunks] # 청크데이터의 text 필드 값을 추출
    
    # 배치 단위로 처리
    # tqdm를 사용하여 진행률 표시
    for i in tqdm(range(0, len(texts), batch_size), desc="임베딩 생성 중"):
        batch_texts = texts[i:i + batch_size] # 배치 크기 만큼 청크데이터를 분할
        
        # 토큰화
        encoded_input = tokenizer(
            batch_texts, # 분할한 청크데이터를 토큰화
            padding=True, # 입력 문장의 길이를 맞추는 역할
            truncation=True, # 너무 긴 입력은 잘라서 모델 크기에 맞게 해주는 역할
            return_tensors='pt', # 토큰화 결과를 PyTorch 텐서 형태로 반환
            max_length=512 # 최대 토큰 길이
        )
        
        # GPU로 이동
        encoded_input = {k: v.to(device) for k, v in encoded_input.items()} # 토큰화 결과를 GPU/CPU로 이동
        
        # 임베딩 생성 (추론 모드)
        with torch.no_grad(): # 그래디언트 계산을 실행하지 않은 명령어, 학습 실행 X, 추론 모드로 설정
            model_output = model(**encoded_input) # 모델에 토큰화 결과를 전달 -> model_output에 저장
            batch_embeddings = mean_pooling(model_output, encoded_input['attention_mask']) # 평균 풀링 사용해서 임베딩 벡터 추출
            
            # CPU로 이동 및 NumPy 변환
            batch_embeddings = batch_embeddings.cpu().numpy() # 임베딩 벡터를 NumPy 배열로 변환
            embeddings.extend(batch_embeddings) # 임베딩 벡터를 하나의 리스트로 병합
    
    return embeddings

# 5번째 순서: 임베딩 저장
def save_embeddings(chunks, embeddings, output_file):
    """
    청크 데이터에 임베딩을 추가하여 JSON 파일로 저장
    """
    # 출력 디렉토리 생성
    os.makedirs(os.path.dirname(output_file), exist_ok=True) # 출력 파일 경로가 없을 경우 폴더 생성
    
    # 임베딩 추가
    result = []
    for chunk, embedding in zip(chunks, embeddings): # 청크 데이터와 임베딩 데이터를 하나로 병합
        chunk_with_embedding = chunk.copy()
        # NumPy 배열을 Python 리스트로 변환 (JSON 직렬화 가능)
        chunk_with_embedding['embedding'] = embedding.tolist()
        result.append(chunk_with_embedding)
    
    # JSON 파일로 저장
    with open(output_file, 'w', encoding='utf-8') as file:
        json.dump(result, file, ensure_ascii=False, indent=2)

def main():
    
    # 1. 디바이스 설정
    # default는 cuda를 사용하고 만약 cuda가 사용이 불가능 할 경우 cpu를 사용
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu') # GPU/CPU 선택
    
    # 2. 모델 및 토크나이저 로드
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME) # 토크나이저 로드
    model = AutoModel.from_pretrained(MODEL_NAME) # 모델 로드
    model.to(device) # 모델을 선택한 디바이스로 이동
    model.eval()  # 평가/추론 모드로 설정
    
    # 3. 청크 파일 로드
    chunks = load_chunks(CHUNK_FILES)
    
    # 4. 임베딩 생성
    embeddings = create_embeddings(chunks, model, tokenizer, device, BATCH_SIZE)
    
    # 5. 결과 저장
    save_embeddings(chunks, embeddings, OUTPUT_FILE)

if __name__ == "__main__":
    main()

