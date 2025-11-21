"""
RAG 기반 상담 시스템
생성날짜: 2025.11.18
설명: 사용자의 질문을 받아 관련 상담 데이터 청크를 검색하고, 이를 바탕으로 적절한 답변 또는 상담을 진행
"""

import json
import chromadb
from pathlib import Path
from typing import List, Dict, Any
import torch
from transformers import AutoModel, AutoTokenizer


# RAG 기반 상담 시스템
class RAGTherapySystem:
    
    # 초기화 함수
    def __init__(self, vector_db_path: str, model_name: str = "BAAI/bge-m3"):

        # Vector DB 경로 설정
        self.db_path = Path(vector_db_path)
        
        # Vector DB 존재 확인
        if not self.db_path.exists():
            raise FileNotFoundError(f"Vector DB 경로가 존재하지 않습니다: {self.db_path}")
        
        # ChromaDB 클라이언트 초기화
        self.client = chromadb.PersistentClient(path=str(self.db_path))
        
        # 컬렉션 이름 매핑
        self.collection_map = {
            1: "paragraph_vec",  # 문단 기반
            2: "semantic_vec"    # 의미 기반
        }
        
        # 디바이스 설정 (GPU/CPU)
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        
        # 임베딩 모델 및 토크나이저 로드
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModel.from_pretrained(model_name)
        self.model.to(self.device)
        self.model.eval()
        
        # 현재 선택된 컬렉션
        self.current_collection = None
    
    # 평균 풀링 함수 - 자세한건 automatic_save/create_embeddings.py 30~36줄 참고
    def mean_pooling(self, model_output, attention_mask):
        token_embeddings = model_output[0]
        input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
        return torch.sum(token_embeddings * input_mask_expanded, 1) / torch.clamp(input_mask_expanded.sum(1), min=1e-9)
    
    # 사용자 질문을 임베딩 벡터로 변환하는 함수
    def create_query_embedding(self, query_text: str) -> List[float]:

        # 토큰화
        encoded_input = self.tokenizer(
            query_text,
            padding=True,
            truncation=True,
            return_tensors='pt',
            max_length=512
        )                  
        
        # GPU/CPU로 이동
        encoded_input = {k: v.to(self.device) for k, v in encoded_input.items()}
        
        # 임베딩 생성
        with torch.no_grad():
            model_output = self.model(**encoded_input)
            embedding = self.mean_pooling(model_output, encoded_input['attention_mask'])
            embedding = embedding.cpu().numpy()[0]
        
        return embedding.tolist()
    
    # 어떤 Vector DB를 사용할건지 선택하는 함수
    def select_collection(self, db_choice: int) -> bool:

        # 만약 잘못된 값 입력 시 예외처리
        if db_choice not in self.collection_map:
            print(f"[오류] 잘못된 DB 선택입니다. 1 또는 2를 입력해주세요.")
            return False
        
        # 선택한 DB 이름을 변수에 저장
        collection_name = self.collection_map[db_choice]
        
        try:
            self.current_collection = self.client.get_collection(name=collection_name)
            collection_type = "문단 기반" if db_choice == 1 else "의미 기반"
            print(f"\n✓ '{collection_type}' Vector DB 선택 완료 (컬렉션: {collection_name})") # console 출력 용도, 나중에 삭제 예정
            return True
        except Exception as e:
            print(f"[오류] 컬렉션을 찾을 수 없습니다: {collection_name}")
            print(f"상세: {e}")
            return False
    
    # 사용자 질문과 관련된 데이터를 상담 청크로부터 검색하는 함수
    def retrieve_chunks(self, user_input: str, n_results: int = 5) -> List[Dict[str, Any]]:

        if self.current_collection is None:
            print("[오류] Vector DB가 선택되지 않았습니다.")
            return []
        
        # 질문을 임베딩으로 변환
        query_embedding = self.create_query_embedding(user_input)
        
        # 유사도 검색
        results = self.current_collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results
        )
        
        # 결과 포맷팅
        retrieved_chunks = []
        if results['ids'] and results['ids'][0]:
            for i in range(len(results['ids'][0])):
                chunk = {
                    'id': results['ids'][0][i],
                    'text': results['documents'][0][i],
                    'metadata': results['metadatas'][0][i],
                    'distance': results['distances'][0][i] if 'distances' in results else None
                }
                retrieved_chunks.append(chunk)
        
        return retrieved_chunks
    
    # 검색된 청크를 바탕으로 상담 답변 생성
    def generate_response(self, user_input: str, retrieved_chunks: List[Dict[str, Any]]) -> Dict[str, Any]:

        # 검색된 청크가 없는 경우
        if not retrieved_chunks:
            return {
                "answer": "죄송합니다. 관련된 상담 자료를 찾을 수 없습니다. 다른 질문을 해주시겠어요?",
                "used_chunks": [],
                "continue_conversation": True
            }
        
        # 청크 기반 답변 생성
        # Rule 1: 사용자의 감정을 먼저 공감하고 반영
        # Rule 2: retrieved_chunks 안의 정보만 사용해 답변 작성
        # Rule 3: RAG 청크를 기반으로 명확한 정보 제공
        # Rule 4: 불필요한 장황한 설명이나 개인적 의견은 배제
        # Rule 5: 답변은 한국어로 자연스럽게 작성
        # Rule 6: 대화 톤은 중립적이고 상담적이며 친절하게 유지
        # Rule 10: 출처 표시
        
        # 답변 구성
        answer_parts = []
        
        # 공감 표현
        answer_parts.append("말씀해주신 내용을 잘 들었습니다.")
        
        # 청크 기반 답변 작성
        answer_parts.append("\n\n관련 상담 내용을 바탕으로 말씀드리겠습니다:\n")
        
        used_chunks = []
        for i, chunk in enumerate(retrieved_chunks[:3], 1):  # 상위 3개 청크 사용
            chunk_text = chunk['text']
            source = chunk['metadata'].get('source', '알 수 없음')
            
            # 청크 내용 추가
            answer_parts.append(f"\n{i}. {chunk_text}")
            answer_parts.append(f"   (출처: {source})")
            
            # 사용된 청크 요약
            used_chunks.append(f"{source}: {chunk_text[:50]}...")
        
        # 마무리 멘트
        answer_parts.append("\n\n더 궁금하신 점이 있으시면 언제든 말씀해주세요.")
        
        answer = "".join(answer_parts)
        
        return {
            "answer": answer,
            "used_chunks": used_chunks,
            "continue_conversation": True
        }
    
    # 상담 함수 
    def chat(self, user_input: str) -> Dict[str, Any]:

        # exit 입력 확인 (Rule 9)
        if user_input.strip().lower() == "exit":
            return {
                "answer": "상담을 종료합니다. 언제든 다시 찾아주세요. 감사합니다.",
                "used_chunks": [],
                "continue_conversation": False
            }
        
        # 1. 관련 청크 검색
        print("\n🔍 관련 상담 자료 검색 중...")
        retrieved_chunks = self.retrieve_chunks(user_input, n_results=5)
        print(f"✓ {len(retrieved_chunks)}개의 관련 자료를 찾았습니다.\n")
        
        # 2. 답변 생성
        response = self.generate_response(user_input, retrieved_chunks)
        
        return response

# 메인
def main():
    
    # console 출력 용도, 나중에 삭제 예정
    print("=" * 70)
    print("RAG 기반 상담 시스템")
    print("=" * 70)
    
    # 경로 설정 (sourcecode/rag 기준)
    base_dir = Path(__file__).parent.parent.parent
    vector_db_dir = base_dir / "vector_db"
    
    try:
        # RAG 상담 시스템 초기화
        print("\n시스템 초기화 중...\n") # console 출력 용도, 나중에 삭제 예정
        rag_system = RAGTherapySystem(str(vector_db_dir))
        
        # DB 선택
        print("\n" + "=" * 70)
        print("Vector DB 선택")
        print("=" * 70)
        print("1. 문단 기반 (paragraph_vec)")
        print("2. 의미 기반 (semantic_vec)")
        print("=" * 70)
        
        while True:
            db_choice = input("\nDB 번호를 선택하세요 (1 또는 2): ").strip()
            
            if db_choice in ['1', '2']:
                if rag_system.select_collection(int(db_choice)):
                    break
            else:
                print("[오류] 1 또는 2를 입력해주세요.")
        
        # 상담 시작
        print("\n" + "=" * 70)
        print("상담 시작")
        print("=" * 70)
        print("고민이나 질문을 자유롭게 말씀해주세요.")
        print("종료하시려면 'exit'를 입력하세요.")
        print("=" * 70)
        
        # 대화 루프
        while True:
            print("\n" + "-" * 70)
            user_input = input("\n[사용자] ").strip()
            
            if not user_input:
                print("[알림] 질문을 입력해주세요.")
                continue
            
            # 상담 진행
            response = rag_system.chat(user_input)
            
            # 답변 출력
            print("\n[상담사]")
            print(response['answer'])
            
            # 사용된 청크 정보 (디버깅용, 필요시 주석 해제)
            if response['used_chunks']:
                print("\n[참고한 자료]")
                for i, chunk in enumerate(response['used_chunks'], 1):
                    print(f"  {i}. {chunk}")
            
            # 종료 확인
            if not response['continue_conversation']:
                break
        
        print("\n" + "=" * 70)
        print("프로그램을 종료합니다.")
        print("=" * 70)
    
    except KeyboardInterrupt:
        print("\n\n프로그램이 사용자에 의해 중단되었습니다.")
    
    except Exception as e:
        print(f"\n[오류] 예상치 못한 오류 발생: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

