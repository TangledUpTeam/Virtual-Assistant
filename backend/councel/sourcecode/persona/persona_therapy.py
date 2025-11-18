"""
Persona 기반 상담 시스템
생성날짜: 2025.11.18
설명: 사용자의 입력을 받아 질문인지 상담인지 판단하고, 
      RAG 엔진에서 검색된 답변을 기반으로 칼 로저스 스타일의 Persona를 입혀 답변을 생성
"""

import json
import chromadb
from pathlib import Path
from typing import List, Dict, Any
import torch
from transformers import AutoModel, AutoTokenizer
import re


# 칼 로저스 상담 스타일 Persona 지침
PERSONA_INSTRUCTIONS = """
당신은 칼 로저스(Carl Rogers)의 인간중심 상담 이론을 따르는 상담사입니다.

핵심 원칙:
1. 무조건적 긍정적 존중 (Unconditional Positive Regard): 사용자를 있는 그대로 수용하고 존중합니다.
2. 공감적 이해 (Empathic Understanding): 사용자의 감정과 경험을 깊이 이해하려 노력합니다.
3. 진솔성 (Genuineness): 진실되고 일치된 태도로 대합니다.

상담 방식:
- Reflective Listening: 사용자의 말을 반영하고 재진술합니다
- 감정 공감: 사용자의 감정을 먼저 인식하고 공감합니다
- 비지시적 접근: 조언보다는 사용자 스스로 답을 찾도록 돕습니다
- 따뜻하고 수용적인 톤: 판단하지 않고 따뜻하게 대합니다

말투:
- "~하시는군요", "~하시는 것 같네요" 등 부드럽고 존중하는 표현 사용
- "제가 이해한 바로는..." 등으로 reflective listening 표현
- 짧고 간결하게, 그러나 따뜻하게
"""


# Persona 기반 상담 시스템
class PersonaTherapySystem:
    
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
        
        # 대화 기록 저장
        self.chat_history = []
        
        # Persona 지침
        self.persona_instructions = PERSONA_INSTRUCTIONS
    
    # 평균 풀링 함수
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
            print(f"\n✓ '{collection_type}' Vector DB 선택 완료 (컬렉션: {collection_name})")
            return True
        except Exception as e:
            print(f"[오류] 컬렉션을 찾을 수 없습니다: {collection_name}")
            print(f"상세: {e}")
            return False
    
    # 입력이 질문인지 상담인지 자동 판단하는 함수 (Rule 2 - 자동 판단)
    def classify_input_type_auto(self, user_input: str) -> str:
        """
        사용자 입력이 질문인지 상담인지 자동으로 판단
        감정 표현, 고민, 심리적 어려움이 포함되면 'counseling'
        정보 요청, 사실 확인 등은 'question'
        """
        # 감정/고민 키워드 (상담 판단용)
        counseling_patterns = [
            r'힘들', r'어렵', r'괴롭', r'우울', r'불안', r'슬프', r'화가', r'외로', r'무섭',
            r'고민', r'걱정', r'두렵', r'답답', r'속상', r'짜증', r'스트레스', r'피곤',
            r'지쳐', r'좌절', r'실망', r'후회', r'미안', r'죄책감',
            r'어떻게 해야', r'조언', r'도움', r'상담', r'이야기 들어',
            r'나는.*느낀다', r'나는.*생각한다', r'내가.*하는데'
        ]
        
        # 질문 패턴 (질문 판단용)
        question_patterns = [
            r'무엇', r'무슨', r'어떤', r'언제', r'어디', r'누가', r'왜', r'어떻게',
            r'이란', r'란', r'이다', r'인가', r'입니까',
            r'\?', r'알려', r'설명', r'정의', r'의미', r'차이', r'방법'
        ]
        
        # 상담 패턴 매칭 점수
        counseling_score = sum(1 for pattern in counseling_patterns if re.search(pattern, user_input))
        
        # 질문 패턴 매칭 점수
        question_score = sum(1 for pattern in question_patterns if re.search(pattern, user_input))
        
        # 점수 기반 판단
        if counseling_score > question_score:
            return "counseling"
        elif question_score > counseling_score:
            return "question"
        else:
            # 동점이거나 둘 다 0인 경우, 문장 길이와 구조로 판단
            # 긴 문장이고 감정 표현이 있으면 상담으로 간주
            if len(user_input) > 30 and any(char in user_input for char in ['..', '...']):
                return "counseling"
            # 짧고 물음표가 있으면 질문으로 간주
            elif '?' in user_input or len(user_input) < 30:
                return "question"
            else:
                # 기본값은 상담으로 간주 (안전한 선택)
                return "counseling"
    
    # 입력이 질문인지 상담인지 키워드 기반 판단하는 함수 (Rule 2 - 키워드 기반, 주석처리)
    """
    def classify_input_type_keyword(self, user_input: str) -> str:
        
        # 상담 키워드
        counseling_keywords = [
            '힘들어', '어려워', '괴로워', '우울', '불안', '슬퍼', '화가', '외로워',
            '고민', '걱정', '두려워', '답답', '속상', '스트레스', '지쳐', '상담'
        ]
        
        # 질문 키워드
        question_keywords = [
            '무엇', '무슨', '어떤', '언제', '어디', '왜', '어떻게',
            '알려', '설명', '정의', '의미', '차이', '방법'
        ]
        
        # 키워드 매칭
        is_counseling = any(keyword in user_input for keyword in counseling_keywords)
        is_question = any(keyword in user_input for keyword in question_keywords)
        
        if is_counseling and not is_question:
            return "counseling"
        elif is_question and not is_counseling:
            return "question"
        else:
            # 애매한 경우 문장 구조로 판단
            if '?' in user_input or user_input.endswith('인가') or user_input.endswith('인가요'):
                return "question"
            else:
                return "counseling"
    """
    
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
    
    # RAG 엔진에서 기본 답변 생성 (Persona 적용 전)
    def generate_rag_answer(self, user_input: str, retrieved_chunks: List[Dict[str, Any]]) -> str:
        """
        RAG 엔진에서 검색된 청크를 기반으로 기본 답변 생성
        """
        if not retrieved_chunks:
            return "관련된 정보를 찾을 수 없습니다."
        
        # 상위 3개 청크를 사용하여 답변 구성
        rag_answer_parts = []
        for i, chunk in enumerate(retrieved_chunks[:3], 1):
            chunk_text = chunk['text']
            rag_answer_parts.append(chunk_text)
        
        return "\n\n".join(rag_answer_parts)
    
    # 질문 타입에 맞춰 최종 답변 생성 (Rule 3, 4)
    def generate_final_answer(
        self, 
        user_input: str, 
        input_type: str, 
        rag_answer: str, 
        retrieved_chunks: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        입력 타입에 따라 최종 답변 생성
        - question: 정확하고 간결한 정보 제공
        - counseling: Persona 스타일을 입혀 공감적 상담 진행
        """
        
        # Rule 3: 질문인 경우 - 정확하고 간결하게 답변 (Rule 6: 장황한 설명 피하기)
        if input_type == "question":
            if not retrieved_chunks:
                answer = "죄송합니다. 관련된 정보를 찾을 수 없습니다. 다른 질문을 해주시겠어요?"
            else:
                # RAG 답변을 기반으로 정확한 정보 제공
                answer_parts = []
                answer_parts.append(f"질문해주신 '{user_input}'에 대해 말씀드리겠습니다.\n")
                answer_parts.append(rag_answer)
                answer_parts.append("\n\n더 궁금하신 점이 있으시면 언제든 물어보세요.")
                answer = "".join(answer_parts)
        
        # Rule 4: 상담인 경우 - Persona 스타일 적용 (Rule 5: 공감, reflective listening)
        else:  # counseling
            if not retrieved_chunks:
                # 검색 결과가 없어도 공감적으로 응답
                answer = f"말씀해주신 '{user_input}'에 대해 함께 생각해보고 싶습니다. 지금 느끼시는 감정을 조금 더 자세히 들려주시겠어요?"
            else:
                # Persona 스타일 적용: 칼 로저스 방식의 공감적 상담
                answer_parts = []
                
                # 1. Reflective Listening: 사용자 말 반영
                answer_parts.append(f"말씀하신 것을 들으니, {self._extract_emotion(user_input)} 느끼고 계시는 것 같네요.")
                
                # 2. 공감 표현
                answer_parts.append(" 그런 상황이라면 충분히 그렇게 느끼실 수 있을 것 같습니다.")
                
                # 3. RAG 기반 상담 내용 제공 (부드럽고 수용적인 톤으로)
                answer_parts.append("\n\n제가 이해한 바로는, 이런 관점도 도움이 될 수 있을 것 같습니다:\n")
                
                # 청크 내용을 따뜻한 톤으로 재구성
                for i, chunk in enumerate(retrieved_chunks[:2], 1):  # 상위 2개만 사용 (간결하게)
                    chunk_text = chunk['text']
                    # 청크를 부드럽게 재표현
                    answer_parts.append(f"\n{chunk_text}")
                
                # 4. 마무리: 비지시적 접근 (조언보다는 탐색 유도)
                answer_parts.append("\n\n이런 이야기들이 지금의 상황에서 어떻게 느껴지시나요? 더 나누고 싶으신 이야기가 있으시면 편하게 말씀해주세요.")
                
                answer = "".join(answer_parts)
        
        # Rule 6: chat_history를 참고하여 일관성 유지
        if self.chat_history:
            # 대화 기록이 있으면 이전 대화와 연결
            answer = self._add_history_context(answer)
        
        return {
            "input_type": input_type,
            "answer": answer,
            "used_rag_answer": rag_answer[:100] + "..." if len(rag_answer) > 100 else rag_answer,
            "continue_conversation": True
        }
    
    # 감정 추출 헬퍼 함수 (Rule 5: 감정 공감)
    def _extract_emotion(self, user_input: str) -> str:
        """
        사용자 입력에서 감정을 추출하여 reflective listening에 활용
        """
        emotion_keywords = {
            '힘들': '힘드시게',
            '어려': '어려우시게',
            '괴롭': '괴로우시게',
            '우울': '우울하시게',
            '불안': '불안하시게',
            '슬프': '슬프시게',
            '화가': '화가 나시게',
            '외로': '외로우시게',
            '걱정': '걱정되시게',
            '두렵': '두려우시게',
            '답답': '답답하시게',
            '속상': '속상하시게',
            '스트레스': '스트레스를 받으시게',
            '지쳐': '지치시게',
        }
        
        for keyword, emotion in emotion_keywords.items():
            if keyword in user_input:
                return emotion
        
        # 기본 감정 표현
        return "여러 감정을"
    
    # 대화 기록 기반 맥락 추가 (Rule 6)
    def _add_history_context(self, answer: str) -> str:
        """
        이전 대화 기록을 참고하여 답변에 맥락을 추가
        """
        # 간단한 예시: 이전 대화가 있으면 연결 표현 추가
        if len(self.chat_history) > 0:
            last_exchange = self.chat_history[-1]
            # 필요시 이전 대화 내용을 참고하여 답변 수정
            # 현재는 단순히 연결 표현만 추가
            pass
        
        return answer
    
    # 메인 상담 함수
    def chat(self, user_input: str) -> Dict[str, Any]:
        """
        사용자 입력을 받아 전체 상담 프로세스 진행
        """
        
        # Rule 9: exit 입력 확인
        if user_input.strip().lower() == "exit":
            return {
                "input_type": "exit",
                "answer": "상담을 마무리하겠습니다. 오늘 함께 시간을 보내주셔서 감사합니다. 언제든 다시 찾아주세요.",
                "used_rag_answer": "",
                "continue_conversation": False
            }
        
        # Rule 1: 입력 타입 자동 판단
        input_type = self.classify_input_type_auto(user_input)
        print(f"\n🔍 입력 분석: {'상담' if input_type == 'counseling' else '질문'} 모드")
        
        # RAG 엔진: 관련 청크 검색
        print("🔍 관련 자료 검색 중...")
        retrieved_chunks = self.retrieve_chunks(user_input, n_results=5)
        print(f"✓ {len(retrieved_chunks)}개의 관련 자료를 찾았습니다.\n")
        
        # RAG 기본 답변 생성
        rag_answer = self.generate_rag_answer(user_input, retrieved_chunks)
        
        # 최종 답변 생성 (입력 타입에 따라 Persona 적용)
        response = self.generate_final_answer(
            user_input=user_input,
            input_type=input_type,
            rag_answer=rag_answer,
            retrieved_chunks=retrieved_chunks
        )
        
        # 대화 기록에 추가
        self.chat_history.append({
            "user": user_input,
            "assistant": response["answer"],
            "type": input_type
        })
        
        return response


# 메인 함수
def main():
    
    print("=" * 70)
    print("Persona 기반 상담 시스템 (칼 로저스 스타일)")
    print("=" * 70)
    
    # 경로 설정
    base_dir = Path(__file__).parent.parent.parent
    vector_db_dir = base_dir / "vector_db"
    
    try:
        # Persona 상담 시스템 초기화
        print("\n시스템 초기화 중...\n")
        persona_system = PersonaTherapySystem(str(vector_db_dir))
        
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
                if persona_system.select_collection(int(db_choice)):
                    break
            else:
                print("[오류] 1 또는 2를 입력해주세요.")
        
        # 상담 시작
        print("\n" + "=" * 70)
        print("상담 시작")
        print("=" * 70)
        print("질문이나 고민을 편하게 말씀해주세요.")
        print("종료하시려면 'exit'를 입력하세요.")
        print("=" * 70)
        
        # 대화 루프
        while True:
            print("\n" + "-" * 70)
            user_input = input("\n[사용자] ").strip()
            
            if not user_input:
                print("[알림] 질문이나 고민을 입력해주세요.")
                continue
            
            # 상담 진행
            response = persona_system.chat(user_input)
            
            # 답변 출력
            print("\n[상담사]")
            print(response['answer'])
            
            # 디버깅 정보 (필요시 주석 해제)
            # print(f"\n[DEBUG] 입력 타입: {response['input_type']}")
            # print(f"[DEBUG] RAG 답변 요약: {response['used_rag_answer']}")
            
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

