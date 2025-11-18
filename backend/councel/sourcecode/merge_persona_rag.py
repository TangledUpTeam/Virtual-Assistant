"""
통합 RAG + Persona 상담 시스템
생성날짜: 2025.11.18
설명: RAG 기반 검색과 Persona(칼 로저스) 스타일을 통합한 상담 시스템
      사용자 입력 유형을 자동 판단하여 질문/상담에 맞는 답변 제공
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


# 통합 RAG + Persona 상담 시스템
class MergedTherapySystem:
    
    def __init__(self, vector_db_path: str, model_name: str = "BAAI/bge-m3"):
        """
        통합 상담 시스템 초기화
        - RAG 엔진: Vector DB 검색 및 임베딩
        - Persona: 칼 로저스 스타일 상담
        """
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
        print("임베딩 모델 로딩 중...")
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModel.from_pretrained(model_name)
        self.model.to(self.device)
        self.model.eval()
        print(f"✓ 모델 로딩 완료 (디바이스: {self.device})")
        
        # 현재 선택된 컬렉션 및 DB 번호
        self.current_collection = None
        self.current_db_choice = None
        
        # 대화 기록 저장
        self.chat_history = []
        
        # Persona 지침
        self.persona_instructions = PERSONA_INSTRUCTIONS
    
    # ========== RAG 엔진 관련 함수 ==========
    
    def mean_pooling(self, model_output, attention_mask):
        """평균 풀링 함수"""
        token_embeddings = model_output[0]
        input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
        return torch.sum(token_embeddings * input_mask_expanded, 1) / torch.clamp(input_mask_expanded.sum(1), min=1e-9)
    
    def create_query_embedding(self, query_text: str) -> List[float]:
        """사용자 질문을 임베딩 벡터로 변환"""
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
    
    def select_collection(self, db_choice: int) -> bool:
        """Vector DB 컬렉션 선택 (Rule 1)"""
        # 잘못된 값 입력 시 예외처리
        if db_choice not in self.collection_map:
            print(f"[오류] 잘못된 DB 선택입니다. 1 또는 2를 입력해주세요.")
            return False
        
        # 선택한 DB 이름을 변수에 저장
        collection_name = self.collection_map[db_choice]
        
        try:
            self.current_collection = self.client.get_collection(name=collection_name)
            self.current_db_choice = db_choice
            collection_type = "문단 기반" if db_choice == 1 else "의미 기반"
            print(f"\n✓ '{collection_type}' Vector DB 선택 완료 (컬렉션: {collection_name})")
            return True
        except Exception as e:
            print(f"[오류] 컬렉션을 찾을 수 없습니다: {collection_name}")
            print(f"상세: {e}")
            return False
    
    def retrieve_chunks(self, user_input: str, n_results: int = 5) -> List[Dict[str, Any]]:
        """사용자 질문과 관련된 데이터를 상담 청크로부터 검색 (Rule 1)"""
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
    
    def generate_rag_answer(self, user_input: str, retrieved_chunks: List[Dict[str, Any]]) -> str:
        """RAG 엔진에서 검색된 청크를 기반으로 기본 답변 생성"""
        if not retrieved_chunks:
            return "관련된 정보를 찾을 수 없습니다."
        
        # 상위 3개 청크를 사용하여 답변 구성
        rag_answer_parts = []
        for i, chunk in enumerate(retrieved_chunks[:3], 1):
            chunk_text = chunk['text']
            rag_answer_parts.append(chunk_text)
        
        return "\n\n".join(rag_answer_parts)
    
    # ========== Persona 관련 함수 ==========
    
    def classify_input_type_auto(self, user_input: str) -> str:
        """
        사용자 입력이 질문인지 상담인지 자동으로 판단 (Rule 2)
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
            if len(user_input) > 30 and any(char in user_input for char in ['..', '...']):
                return "counseling"
            elif '?' in user_input or len(user_input) < 30:
                return "question"
            else:
                # 기본값은 상담으로 간주 (안전한 선택)
                return "counseling"
    
    def _extract_emotion(self, user_input: str) -> str:
        """사용자 입력에서 감정을 추출하여 reflective listening에 활용 (Rule 3)"""
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
    
    def _add_history_context(self, answer: str) -> str:
        """이전 대화 기록을 참고하여 답변에 맥락을 추가 (Rule 4)"""
        # 이전 대화가 있으면 연결 표현 추가
        if len(self.chat_history) > 0:
            last_exchange = self.chat_history[-1]
            # 필요시 이전 대화 내용을 참고하여 답변 수정
            # 현재는 단순히 연결성 유지
            pass
        
        return answer
    
    def _apply_persona_layer(self, chunk_text: str) -> str:
        """
        RAG 청크를 칼 로저스 상담사 시점으로 재작성 (Persona Layer)
        - 이론적 내용을 상담사의 부드러운 말투로 변환
        - "~입니다" → "~인 것 같아요", "~하시는 것 같네요"
        - 객관적 설명 → 공감적 제안
        """
        # 청크가 비어있으면 그대로 반환
        if not chunk_text.strip():
            return chunk_text
        
        # 상담사 시점 변환 패턴
        # 1. 강한 단정 표현을 부드럽게
        text = re.sub(r'입니다\.', '인 것 같아요.', chunk_text)
        text = re.sub(r'합니다\.', '할 수 있을 것 같아요.', text)
        text = re.sub(r'됩니다\.', '될 수 있을 것 같아요.', text)
        text = re.sub(r'있습니다\.', '있는 것 같아요.', text)
        
        # 2. "해야 한다" 같은 지시적 표현을 비지시적으로
        text = re.sub(r'해야 합니다', '해보시는 것도 도움이 될 수 있을 것 같아요', text)
        text = re.sub(r'해야 한다', '해보시는 것이 좋을 것 같아요', text)
        text = re.sub(r'필요합니다', '필요하실 수 있을 것 같아요', text)
        
        # 3. "중요하다" 같은 강조 표현을 부드럽게
        text = re.sub(r'중요합니다', '중요하게 느껴질 수 있을 것 같아요', text)
        text = re.sub(r'중요하다', '중요할 수 있을 것 같아요', text)
        
        # 4. 이론적 용어를 일상적 표현으로
        text = re.sub(r'공감적 이해', '상대방의 마음을 이해하려는 노력', text)
        text = re.sub(r'무조건적 긍정적 존중', '있는 그대로를 받아들이는 것', text)
        
        return text
    
    def _transform_chunk_to_counseling(self, chunk_text: str) -> str:
        """
        RAG 청크를 상담사 관점에서 자연스럽게 재구성
        - 단순 정보 나열이 아닌, 상담사가 이해하고 공감하며 전달하는 형식
        """
        # Persona Layer 적용
        transformed = self._apply_persona_layer(chunk_text)
        
        # 문장이 너무 길면 요약하거나 핵심만 추출
        sentences = transformed.split('.')
        
        # 핵심 문장만 선택 (너무 기술적이거나 형식적인 문장 제외)
        meaningful_sentences = []
        for sentence in sentences:
            sentence = sentence.strip()
            if sentence and len(sentence) > 10:
                # 너무 학술적이거나 형식적인 표현 필터링
                if not any(word in sentence for word in ['참고문헌', '출처:', '저자:', '논문', '연구']):
                    meaningful_sentences.append(sentence)
        
        # 최대 2-3개 문장만 사용 (간결하게)
        if len(meaningful_sentences) > 3:
            meaningful_sentences = meaningful_sentences[:3]
        
        # 재조합
        result = '. '.join(meaningful_sentences)
        if result and not result.endswith('.'):
            result += '.'
        
        return result
    
    # ========== 통합 답변 생성 함수 ==========
    
    def generate_final_answer(
        self,
        user_input: str,
        input_type: str,
        rag_answer: str,
        retrieved_chunks: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        입력 타입에 따라 최종 답변 생성 (Rule 2)
        - question: RAG 답변을 그대로 활용하여 정확하고 간결하게 답변
        - counseling: RAG 답변을 Persona 스타일로 변환하여 공감적 상담 진행
        """
        
        # Rule 2: 질문인 경우 - 정확하고 간결하게 답변 (Rule 5, 6)
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
        
        # Rule 2: 상담인 경우 - Persona 스타일 적용 (Rule 3: 공감, reflective listening)
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
                
                # 3. RAG 기반 상담 내용 제공 (Persona Layer로 재작성)
                answer_parts.append("\n\n제가 이해한 바로는, 이런 관점도 도움이 될 수 있을 것 같습니다:\n")
                
                # 청크 내용을 상담사 시점으로 재작성 (Persona Layer 적용)
                counseling_chunks = []
                for i, chunk in enumerate(retrieved_chunks[:2], 1):  # 상위 2개만 사용 (간결하게)
                    chunk_text = chunk['text']
                    # ★ Persona Layer: 청크를 상담사 시점으로 변환
                    transformed_text = self._transform_chunk_to_counseling(chunk_text)
                    
                    if transformed_text.strip():
                        counseling_chunks.append(transformed_text)
                
                # 재작성된 청크들을 자연스럽게 연결
                if counseling_chunks:
                    # 첫 번째 청크
                    answer_parts.append(f"\n{counseling_chunks[0]}")
                    
                    # 두 번째 청크가 있으면 연결어와 함께 추가
                    if len(counseling_chunks) > 1:
                        answer_parts.append(f"\n\n또한, {counseling_chunks[1]}")
                
                # 4. 마무리: 비지시적 접근 (조언보다는 탐색 유도)
                answer_parts.append("\n\n이런 이야기들이 지금의 상황에서 어떻게 느껴지시나요? 더 나누고 싶으신 이야기가 있으시면 편하게 말씀해주세요.")
                
                answer = "".join(answer_parts)
        
        # Rule 4: chat_history를 참고하여 일관성 유지
        if self.chat_history:
            answer = self._add_history_context(answer)
        
        return {
            "input_type": input_type,
            "answer": answer,
            "used_rag_answer": rag_answer[:100] + "..." if len(rag_answer) > 100 else rag_answer,
            "db_used": self.current_db_choice,
            "continue_conversation": True
        }
    
    # ========== 메인 상담 함수 ==========
    
    def chat(self, user_input: str) -> Dict[str, Any]:
        """
        사용자 입력을 받아 전체 상담 프로세스 진행
        1. 입력 타입 자동 판단 (question / counseling)
        2. 선택된 Vector DB에서 관련 청크 검색
        3. RAG 기본 답변 생성
        4. 입력 타입에 따라 최종 답변 생성 (Persona 적용)
        5. 대화 기록 저장 및 연속성 유지
        """
        
        # Rule 7: exit 입력 확인
        if user_input.strip().lower() == "exit":
            return {
                "input_type": "exit",
                "answer": "상담을 마무리하겠습니다. 오늘 함께 시간을 보내주셔서 감사합니다. 언제든 다시 찾아주세요.",
                "used_rag_answer": "",
                "db_used": self.current_db_choice,
                "continue_conversation": False
            }
        
        # Step 1: 입력 타입 자동 판단 (Rule 2)
        input_type = self.classify_input_type_auto(user_input)
        print(f"\n🔍 입력 분석: {'상담' if input_type == 'counseling' else '질문'} 모드")
        
        # Step 2: 선택된 Vector DB에서 관련 청크 검색 (Rule 1)
        print("🔍 관련 자료 검색 중...")
        retrieved_chunks = self.retrieve_chunks(user_input, n_results=5)
        print(f"✓ {len(retrieved_chunks)}개의 관련 자료를 찾았습니다.\n")
        
        # Step 3: RAG 기본 답변 생성
        rag_answer = self.generate_rag_answer(user_input, retrieved_chunks)
        
        # Step 4: 최종 답변 생성 (입력 타입에 따라 Persona 적용)
        response = self.generate_final_answer(
            user_input=user_input,
            input_type=input_type,
            rag_answer=rag_answer,
            retrieved_chunks=retrieved_chunks
        )
        
        # Step 5: 대화 기록에 추가 (Rule 4: 연속성 유지)
        self.chat_history.append({
            "user": user_input,
            "assistant": response["answer"],
            "type": input_type,
            "db_used": self.current_db_choice
        })
        
        return response


# ========== 메인 함수 ==========

def main():
    """
    통합 상담 시스템 메인 함수
    - DB 선택 안내 (Rule 1)
    - 반복 대화 유지 (Rule 7)
    """
    
    print("=" * 70)
    print("통합 RAG + Persona 상담 시스템 (칼 로저스 스타일)")
    print("=" * 70)
    
    # 경로 설정
    base_dir = Path(__file__).parent.parent
    vector_db_dir = base_dir / "vector_db"
    
    try:
        # 시스템 초기화
        print("\n시스템 초기화 중...\n")
        therapy_system = MergedTherapySystem(str(vector_db_dir))
        
        # Rule 1: DB 선택 안내
        print("\n" + "=" * 70)
        print("Vector DB 선택")
        print("=" * 70)
        print("1. 문단 기반 (paragraph_vec)")
        print("2. 의미 기반 (semantic_vec)")
        print("=" * 70)
        
        while True:
            db_choice = input("\nDB 번호를 선택하세요 (1 또는 2): ").strip()
            
            if db_choice in ['1', '2']:
                if therapy_system.select_collection(int(db_choice)):
                    break
            else:
                print("[오류] 1 또는 2를 입력해주세요.")
        
        # 상담 시작
        print("\n" + "=" * 70)
        print("상담 시작")
        print("=" * 70)
        print("질문이나 고민을 편하게 말씀해주세요.")
        print("- 일반 질문: 정보 기반 답변 제공")
        print("- 상담/고민: 칼 로저스 스타일 공감적 상담 진행")
        print("종료하시려면 'exit'를 입력하세요.")
        print("=" * 70)
        
        # Rule 7: 대화 루프 (반복 대화 유지)
        while True:
            print("\n" + "-" * 70)
            user_input = input("\n[사용자] ").strip()
            
            if not user_input:
                print("[알림] 질문이나 고민을 입력해주세요.")
                continue
            
            # 상담 진행
            response = therapy_system.chat(user_input)
            
            # 답변 출력
            print("\n[상담사]")
            print(response['answer'])
            
            # 디버깅 정보 (필요시 주석 해제)
            # print(f"\n[DEBUG] 입력 타입: {response['input_type']}")
            # print(f"[DEBUG] 사용된 DB: {response['db_used']}")
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

