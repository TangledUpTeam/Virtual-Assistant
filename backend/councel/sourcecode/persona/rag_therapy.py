"""
RAG 기반 상담 시스템
생성날짜: 2025.11.18
수정날짜: 2025.11.21
설명: 사용자의 질문을 받아 관련 상담 데이터 청크를 검색하고, 이를 바탕으로 적절한 답변 또는 상담을 진행
OpenAI API를 사용한 임베딩 및 답변 생성
"""

import os
import json
import chromadb
from pathlib import Path
from typing import List, Dict, Any, Optional
from openai import OpenAI
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

# RAG 기반 상담 시스템
class RAGTherapySystem:
    
    # 초기화 함수
    def __init__(self, vector_db_path: str):

        # Vector DB 경로 설정
        self.db_path = Path(vector_db_path)
        
        # Vector DB 존재 확인
        if not self.db_path.exists():
            raise FileNotFoundError(f"Vector DB 경로가 존재하지 않습니다") # 나중에 삭제 예정
        
        # ChromaDB 클라이언트 초기화
        self.client = chromadb.PersistentClient(path=str(self.db_path))
        
        # 컬렉션 이름 (save_to_vectordb.py와 동일)
        self.collection_name = "vector_adler"
        
        # OpenAI 클라이언트 초기화
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY가 환경 변수에 설정되지 않았습니다.")
        self.openai_client = OpenAI(api_key=api_key)
        
        # 컬렉션 로드
        try:
            self.collection = self.client.get_collection(name=self.collection_name)
            print(f"컬렉션 로드 완료")
        except Exception as e:
            raise ValueError(f"컬렉션 '{self.collection_name}'을 찾을 수 없습니다: {e}")
        
        # 감정/상담 키워드 목록
        self.counseling_keywords = [
            "힘들어", "상담", "짜증", "우울", "불안", "스트레스", 
            "고민", "걱정", "슬프", "외로", "화나", "답답",
            "counseling", "therapy", "help", "depressed", "anxious"
        ]
        
        # 대화 히스토리 (단기 기억)
        self.chat_history = []
        
        # 페르소나 프롬프트 정의
        self.adler_persona = """당신은 알프레드 아들러(Alfred Adler)의 개인심리학을 따르는 심리학자입니다.

핵심 원칙:
1. 열등감과 보상: 모든 인간은 열등감을 느끼며, 이를 극복하려는 우월성 추구가 성장의 동력입니다.
2. 사회적 관심: 인간은 본질적으로 사회적 존재이며, 공동체 감각이 중요합니다.
3. 생활양식: 개인의 독특한 생활양식이 행동과 사고를 결정합니다.
4. 목적론적 관점: 과거보다는 미래의 목표가 현재 행동을 결정합니다.
5. 격려: 용기를 북돋우는 것이 치료의 핵심입니다.

답변 방식:
- 열등감을 인정하고 이를 성장의 기회로 재해석
- 사회적 관심과 공동체 감각 강조
- 개인의 창조적 힘과 선택 능력 강조
- 격려와 용기를 주는 톤
- 목표 지향적 관점 제시
- **반드시 2-3문장 이내로 간결하게 답변**

말투:
- 격려적이고 희망적인 표현 사용
- "~할 수 있습니다", "~의 기회입니다" 등 긍정적 표현
- 명확하고 실용적인 조언
- 불필요한 설명은 생략하고 핵심만 전달"""
    
    # 사용자 입력을 영어로 번역하는 함수
    def translate_to_english(self, text: str) -> str:
        """사용자 입력을 영어로 번역"""
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a translator. Translate the following text to English. Only output the translation, nothing else."},
                    {"role": "user", "content": text}
                ],
                temperature=0.3,
                max_tokens=500
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"[경고] 번역 실패: {e}")
            return text  # 번역 실패 시 원문 반환
    
    # 사용자 질문을 임베딩 벡터로 변환하는 함수 (OpenAI)
    def create_query_embedding(self, query_text: str) -> List[float]:
        """OpenAI text-embedding-3-large를 사용하여 임베딩 생성"""
        try:
            response = self.openai_client.embeddings.create(
                model="text-embedding-3-large",
                input=query_text
            )
            return response.data[0].embedding
        except Exception as e:
            print(f"[오류] 임베딩 생성 실패: {e}")
            raise
    
    # 사용자 입력 분류 함수
    def classify_input(self, user_input: str) -> str:
        """
        사용자 입력을 분류
        Returns:
            - "adler": 아들러 관련 질문
            - "counseling": 상담/감정 관련 질문
            - "general": 일반 질문
        """
        user_input_lower = user_input.lower()
        
        # 아들러 키워드 체크
        if "아들러" in user_input or "adler" in user_input_lower:
            return "adler"
        
        # 감정/상담 키워드 체크
        for keyword in self.counseling_keywords:
            if keyword in user_input_lower:
                return "counseling"
        
        return "general"
    
    
    # 사용자 질문과 관련된 데이터를 상담 청크로부터 검색하는 함수
    def retrieve_chunks(self, user_input: str, n_results: int = 5) -> List[Dict[str, Any]]:
        """
        Vector DB에서 관련 청크 검색
        Args:
            user_input: 검색할 텍스트 (영어)
            n_results: 반환할 결과 수
        """
        # 질문을 임베딩으로 변환
        query_embedding = self.create_query_embedding(user_input)
        
        # 유사도 검색
        results = self.collection.query(
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
    
    # 페르소나 기반 답변 생성 (RAG + Persona)
    def generate_response_with_persona(self, user_input: str, retrieved_chunks: List[Dict[str, Any]], mode: str = "adler") -> Dict[str, Any]:
        """
        페르소나를 적용한 RAG 기반 답변 생성
        Args:
            user_input: 사용자 입력 (원문, 한국어)
            retrieved_chunks: 검색된 청크 리스트
            mode: "adler" 또는 "counseling"
        """
        # 검색된 청크가 없는 경우
        if not retrieved_chunks:
            return {
                "answer": "죄송합니다. 관련된 자료를 찾을 수 없습니다. 다른 질문을 해주시겠어요?",
                "used_chunks": [],
                "continue_conversation": True
            }
        
        # 컨텍스트 구성
        context_parts = []
        used_chunks = []
        
        for i, chunk in enumerate(retrieved_chunks[:3], 1):  # 상위 3개 청크 사용
            chunk_text = chunk['text']
            source = chunk['metadata'].get('source', '알 수 없음')
            context_parts.append(f"[자료 {i}]\n{chunk_text}\n(출처: {source})")
            used_chunks.append(f"{source}: {chunk_text[:50]}...")
        
        context = "\n\n".join(context_parts)
        
        # 아들러 페르소나 사용
        persona_prompt = self.adler_persona
        user_message = f"""참고 자료:
{context}

사용자 질문: {user_input}

위 자료를 바탕으로 아들러 개인심리학 관점에서 답변해주세요.
격려와 용기를 주는 톤으로, 열등감을 성장의 기회로 재해석하고 사회적 관심을 강조해주세요.

**중요: 답변은 2-3문장 이내로 간결하게 작성해주세요.**"""
        
        # 대화 히스토리 추가 (단기 기억)
        messages = [{"role": "system", "content": persona_prompt}]
        
        # 최근 2개의 대화만 포함 (컨텍스트 길이 관리)
        for history in self.chat_history[-2:]:
            messages.append({"role": "user", "content": history["user"]})
            messages.append({"role": "assistant", "content": history["assistant"]})
        
        messages.append({"role": "user", "content": user_message})
        
        # OpenAI API 호출
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                temperature=0.7,
                max_tokens=200  # 답변 길이 제한 (1000 -> 200)
            )
            
            answer = response.choices[0].message.content.strip()
            
            return {
                "answer": answer,
                "used_chunks": used_chunks,
                "mode": mode,
                "continue_conversation": True
            }
        
        except Exception as e:
            print(f"[오류] OpenAI 답변 생성 실패: {e}")
            return {
                "answer": "죄송합니다. 답변 생성 중 오류가 발생했습니다. 다시 시도해주세요.",
                "used_chunks": [],
                "mode": mode,
                "continue_conversation": True
            }
    
    # 상담 함수 
    def chat(self, user_input: str) -> Dict[str, Any]:
        """
        사용자 입력을 받아 페르소나 기반 답변 생성
        """
        # exit 입력 확인
        if user_input.strip().lower() == "exit":
            return {
                "answer": "상담을 마무리하겠습니다. 오늘 함께 시간을 보내주셔서 감사합니다. 언제든 다시 찾아주세요.",
                "used_chunks": [],
                "mode": "exit",
                "continue_conversation": False
            }
        
        # 1. 입력 분류
        input_type = self.classify_input(user_input)
        mode_name = {"adler": "아들러 모드", "counseling": "상담 모드", "general": "일반 모드"}
        print(f"\n📋 입력 유형: {mode_name.get(input_type, input_type)}")
        
        # 2. 영어로 번역 (Vector DB 검색용)
        print("🌐 영어로 번역 중...")
        english_input = self.translate_to_english(user_input)
        print(f"✓ 번역 완료: {english_input[:50]}...")
        
        # 3. 입력 유형에 따른 처리 (모든 모드에서 아들러 페르소나 사용)
        print("\n🔍 관련 자료 검색 중...")
        retrieved_chunks = self.retrieve_chunks(english_input, n_results=5)
        print(f"✓ {len(retrieved_chunks)}개의 관련 자료를 찾았습니다.")
        print("🎭 아들러 페르소나 적용 중...\n")
        
        response = self.generate_response_with_persona(user_input, retrieved_chunks, mode=input_type)
        
        # 대화 히스토리에 추가 (단기 기억)
        self.chat_history.append({
            "user": user_input,
            "assistant": response["answer"]
        })
        
        # 히스토리가 너무 길어지면 오래된 것 제거 (최대 10개 유지)
        if len(self.chat_history) > 10:
            self.chat_history = self.chat_history[-10:]
        
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
        print("\n시스템 초기화 중...")
        print("- OpenAI API 연결 확인")
        print("- Vector DB 로드")
        rag_system = RAGTherapySystem(str(vector_db_dir))
        print("✓ 초기화 완료\n")
        
        # 상담 시작
        print("\n" + "=" * 70)
        print("🎭 아들러 페르소나 기반 RAG 상담 시스템")
        print("=" * 70)
        print("\n💬 대화 모드:")
        print("  • 아들러 모드: '아들러' 키워드 포함 시")
        print("  • 상담 모드: 감정/고민 표현 시")
        print("  • 일반 모드: 기타 질문")
        print("  (모든 모드에서 아들러 페르소나 적용)")
        print("\n✨ 특징:")
        print("  • 다국어 자동 번역 지원")
        print("  • 대화 히스토리 기반 맥락 유지 (단기 기억)")
        print("  • 아들러 개인심리학 기반 답변")
        print("\n종료하시려면 'exit'를 입력하세요.")
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
            print(f"\n[🎭 아들러 상담사]")
            print(response['answer'])
            
            # 사용된 청크 정보 (디버깅용, 필요시 주석 해제)
            if response.get('used_chunks'):
                print("\n[📚 참고한 자료]")
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

