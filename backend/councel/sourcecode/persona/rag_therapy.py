"""
RAG 기반 상담 시스템
생성날짜: 2025.11.18
수정날짜: 2025.12.01
설명: 사용자의 질문을 받아 관련 상담 데이터 청크를 검색하고, 이를 바탕으로 적절한 답변 또는 상담을 진행
OpenAI API를 사용한 임베딩 및 답변 생성
시간복잡도: O(i * q * n + k + n + h)
주요 변경: 
  - RAG 기반 동적 페르소나 생성 (Vector DB + 웹 검색)
  - LLM 기반 답변 품질 자동 평가 (스코어링 시스템)
  - 청크 한국어 요약 기능
  - Re-ranker 적용 (검색 결과 재정렬)
  - 코드 구조 정리: 상담 관련 기능 / 로그 관련 기능 분리
  - Threshold 기반 RAG + Self-learning 시스템 (2025.12.01)
    * 유사도 0.75 기준 분기: 높으면 LLM 단독, 낮으면 RAG + Self-learning
    * Self-learning: 유사도 낮을 때 Q&A를 Vector DB에 자동 저장
  - 파일 분리: persona_manager, search_engine, response_generator로 분리 (2025.12.01)
로그와 관련된 코드 위치
  - 21줄
  - 206줄
  - 376줄
  - 401줄
  - 456줄
"""

# ============================================================
# 스코어링 관련 코드 (주석처리됨 - 필요시 주석 해제)
# ============================================================
# TherapyLogger 임포트 (직접 실행 시와 모듈 import 시 모두 지원)
# try:
#     from .therapy_logger import TherapyLogger
# except ImportError:
#     # 직접 실행 시 상대 import가 실패하면 절대 import 시도
#     import sys
#     from pathlib import Path
#     # 현재 파일의 디렉토리를 sys.path에 추가
#     current_dir = Path(__file__).parent
#     if str(current_dir) not in sys.path:
#         sys.path.insert(0, str(current_dir))
#     from therapy_logger import TherapyLogger
# ============================================================

import os
import json
import chromadb
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from openai import OpenAI
from dotenv import load_dotenv

# 분리된 모듈 임포트
from .persona_manager import PersonaManager
from .search_engine import SearchEngine
from .response_generator import ResponseGenerator

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
        except Exception as e:
            raise ValueError(f"컬렉션 '{self.collection_name}'을 찾을 수 없습니다: {e}")
        
        # 감정/상담 키워드 목록
        # 나중에 Multi-agent 구현 시 삭제 예정
        self.counseling_keywords = [
            # 기본 감정 키워드
            '힘들어', '상담', '짜증', '우울', '불안', '스트레스',
            '고민', '걱정', '슬프', '외로', '화나', '답답',
            '아들러', 'adler', 'counseling', 'therapy', 'help',
            'depressed', 'anxious', '심리',
            
            # 부정적 감정 키워드
            '절망', '포기', '무기력', '자책', '후회', '미안',
            '두려움', '공포', '불안감', '초조', '조마조마',
            '분노', '화남', '짜증나', '성가심', '불쾌',
            '슬픔', '비참', '절망적', '우울함', '침체',
            '외로움', '고독', '쓸쓸', '허전', '외톨이',
            '답답함', '막막', '막힘', '난처', '곤란',
            '피곤', '지침', '무력감', '무기력', '의욕없음',
            '수치', '수치스럽', '수치심',
            '열받', '열받아', '화낼', '미치', '미쳐',
            '억울', '억울해', '억울함',
            '멍하', '멍하게', '로봇',
            
            # 관계/대인관계 관련
            '갈등', '싸움', '다툼', '오해', '불화',
            '이별', '헤어짐', '이혼', '결별',
            '배신', '상처', '아픔', '서운',
            '소외', '왕따', '따돌림', '무시',

            # 관계/대인관계 관련 섹션 (103번 줄 근처)에 추가:
            '배제', '배제하는', '멀리하는', '따로 노는', '겉돌고', 
            '혼자', '남겨지는', '불편', '팀', '회사',
            
            # 직장/학업 스트레스
            '직장', '업무', '과로', '번아웃', 'burnout',
            '시험', '공부', '학업', '성적', '압박',
            '실패', '좌절', '낙담', '실망',
            '상사', '팀장', '부장', '동기', '동료',
            '욕', '쌍욕', '폭언', '인격모독', '인격 모독',
            '소리지르', '소리 지르', '화풀이',
            '그만두', '퇴사', '사직',
            
            # 자기존중감/자신감 관련
            '자존감', '자신감', '열등감', '비교', '열등',
            '자책', '자기비하', '자기혐오', '부족함',
            '능력부족', '무능력', '쓸모없음',
            
            # 트라우마/과거 상처
            '트라우마', 'trauma', '상처', '과거', '기억',
            '악몽', '플래시백', 'ptsd',
            
            # 신체 반응/증상
            '심장', '떨려', '떨림', '손떨림',
            '잠이 안 와', '불면', '수면장애', '수면',
            
            # 감정 조절/대처
            '감정조절', '감정 조절', '퍼붓', '퍼붓다',
            '대처', '현명', '해결',
            
            # 자살 사고
            '죽고 싶', '자살', '자살사고', 'suicide',
            
            # 영어 감정 키워드
            'sad', 'angry', 'lonely', 'frustrated', 'stressed',
            'worried', 'scared', 'afraid', 'fear', 'panic',
            'hopeless', 'helpless', 'worthless', 'empty',
            'guilt', 'shame', 'regret', 'remorse',
            'jealous', 'envy', 'resentment', 'bitter',
            'tired', 'exhausted', 'burnout', 'overwhelmed',
            'confused', 'lost', 'directionless', 'purposeless',
            
            # 상담/치료 관련 용어
            '심리상담', '정신건강', '치료', '치유', '회복',
            '마음', '감정', '기분', '상태', '조언',
            '도움', '지원', '위로', '격려', '공감',
            'psychology', 'mental health', 'counselor', 'therapist',
            'support', 'comfort', 'encouragement', 'empathy',
            
            # 일상적 표현
            '안좋아', '안좋음', '나쁨', '최악', '끔찍',
            '괴로워', '괴롭', '아파', '아픔', '고통',
            '힘듦', '어려움', '난감', '막막함',

            # 직장/학업 스트레스 섹션 (109-116번 줄)에 추가 권장:
            '적응', '적응하는', '적응이', '분위기', '문화', '익숙', '익숙해지지', 
            '익숙하지', '부담', '부담스럽고', '어울리', '어울리지', '소통', 
            '환경', '출근', '노력', '긴장', '긴장되고', '긴장돼요',

            # 직장/학업 스트레스 섹션에 추가 (162번 줄 다음):
            '낯설', '낯설어서', '대화', '규칙', '절차', '복잡', 
            '시스템', '도구', '효율', '회의', '의견', '표현',
            '출퇴근', '루틴', '리듬', '변화', '부담감', '프로젝트',

            # 통제/주도권 관련 (Case 1 - Jim)
            '통제', '주도권', '주도', '독단적', '경직', '경직된',
            'inflexible', 'overbearing', 'control',

            # 알코올/학대 관련 (Case 1 - Jim)  
            '알코올', '술', '음주', '취함', 'alcoholic', 'drunk',
            '학대', '폭력', '구타', 'abusive', 'violence',

            # 신뢰/불신 관련 (Case 4 - Jen)
            '불신', '신뢰', '믿음', '믿을', 'trust', 'mistrust', 'trustworthy',

            # 가족 관계 관련
            '아버지', '어머니', '부모', '가족', 'father', 'mother', 'parent', 'family',

            # 완벽주의 관련 (Case 3 - Margarita)
            '완벽', '완벽주의', '완벽해', 'perfect', 'perfectionism',

            # 불안정 관련
            '불안정', '불안정한', 'insecure', 'instability',

        ]
        
        # 대화 히스토리 (단기 기억)
        self.chat_history = []
        
        # ========================================
        # 스코어링 관련 코드 (주석처리됨 - 필요시 주석 해제)
        # ========================================
        # 로거 초기화 (스코어링 로그 저장용)
        # base_dir = Path(__file__).parent.parent.parent  # backend/councel/
        # test_dir = base_dir / "test"  # backend/councel/test/
        # log_file_prefix = "scoring_log_v7"  # 로그 파일명 (필요시 변경)
        # 
        # self.therapy_logger = TherapyLogger(
        #     openai_client=self.openai_client,
        #     log_dir=str(test_dir),
        #     log_file_prefix=log_file_prefix
        # )
        # ========================================
        
        # 기본 디렉토리 경로
        base_dir = Path(__file__).parent.parent.parent  # backend/councel/
        
        # 분리된 모듈 초기화
        self.persona_manager = PersonaManager(
            openai_client=self.openai_client,
            collection=self.collection,
            base_dir=base_dir
        )
        self.adler_persona = self.persona_manager.adler_persona
        
        self.search_engine = SearchEngine(
            openai_client=self.openai_client,
            collection=self.collection,
            counseling_keywords=self.counseling_keywords
        )
        
        self.response_generator = ResponseGenerator(
            openai_client=self.openai_client,
            counseling_keywords=self.counseling_keywords
        )
        
        # ========================================
    
    # ============================================================
    # 상담 관련 기능
    # ============================================================
    
    # Self-learning: Q&A를 Vector DB에 저장
    # 자가학습 RAG
    def _save_qa_to_vectordb(self, user_query: str, llm_response: str):

        try:
            import uuid
            from datetime import datetime
            
            # Q&A 문서 생성
            qa_document = {
                "user_query": user_query,
                "llm_response": llm_response,
                "timestamp": datetime.now().isoformat()
            }
            
            # JSON 문자열로 변환
            qa_text = json.dumps(qa_document, ensure_ascii=False, indent=2)
            
            # 임베딩 생성
            embedding = self.search_engine.create_query_embedding(user_query)
            
            # 고유 ID 생성
            doc_id = f"self_learning_{uuid.uuid4().hex[:12]}"
            
            # Vector DB에 저장
            self.collection.add(
                ids=[doc_id],
                embeddings=[embedding],
                documents=[qa_text],
                metadatas=[{
                    "source": "self_learning",
                    "type": "qa_pair",
                    "timestamp": qa_document["timestamp"]
                }]
            )
            
            print(f"[정보] Self-learning: Q&A가 Vector DB에 저장되었습니다 (ID: {doc_id})")
            
        except Exception as e:
            print(f"[경고] Self-learning 저장 실패: {e}")
            # 저장 실패해도 답변은 계속 진행
    
    # 상담 함수(사용자 입력 -> 답변 생성)
    def chat(self, user_input: str) -> Dict[str, Any]:

        # 종료 키워드 확인 (exit, 고마워, 끝)
        user_input_lower = user_input.strip().lower()
        exit_keywords = ["exit", "고마워", "끝"]
        if any(keyword in user_input_lower for keyword in exit_keywords):
            return {
                "answer": "상담을 마무리하겠습니다. 오늘 함께 시간을 보내주셔서 감사합니다. 언제든 다시 찾아주세요.",
                "used_chunks": [],
                "used_chunks_detailed": [],
                "mode": "exit",
                "continue_conversation": False
            }
        
        # 1. 입력 분류
        input_type = self.response_generator.classify_input(user_input)
        
        # 2. 영어로 번역 (Vector DB 검색용)
        english_input = self.search_engine.translate_to_english(user_input)
        
        # 3. Threshold 고정 (0.7)
        threshold = 0.7
        print(f"[정보] Threshold 설정: {threshold}")
        
        # 4. Multi-step 반복 검색 시스템 사용 (쿼리 확장 1회로 제한)
        search_result = self.search_engine._iterative_search_with_query_expansion(english_input, max_iterations=2, n_results=5)
        retrieved_chunks = search_result['chunks']
        quality_info = search_result['quality_info']
        iterations_used = search_result['iterations_used']
        
        print(f"[정보] 검색 완료: {iterations_used}회 반복, 품질 점수 {quality_info['quality_score']:.4f}")
        
        # 5. 최고 유사도 계산 (감정 가중치 적용된 값 사용)
        max_similarity = 0.0
        for chunk in retrieved_chunks:
            # 하이브리드 검색에서 계산된 final_similarity 사용
            if 'final_similarity' in chunk:
                max_similarity = max(max_similarity, chunk['final_similarity'])
            elif 'distance' in chunk and chunk['distance'] is not None:
                similarity = self.search_engine.get_distance_to_similarity(chunk['distance'])
                max_similarity = max(max_similarity, similarity)
        
        print(f"[정보] 최고 유사도: {max_similarity:.4f} (Threshold: {threshold})")
        
        # 6. Threshold 분기
        if max_similarity >= threshold:
            # Case A: 유사도 ≥ threshold -> RAG 없이 LLM 단독 답변
            print(f"[정보] Threshold 분기: LLM 단독 모드 (유사도 {max_similarity:.4f} ≥ {threshold})")
            response = self.response_generator._generate_llm_only_response(
                user_input, 
                self.adler_persona, 
                self.chat_history,
                self.counseling_keywords
            )
            response['similarity_score'] = max_similarity
            response['search_iterations'] = iterations_used
        else:
            # Case B: 유사도 < threshold -> RAG + Self-learning
            print(f"[정보] Threshold 분기: RAG + Self-learning 모드 (유사도 {max_similarity:.4f} < {threshold})")
            
            # 6-1. RAG 기반 답변 생성
            response = self.response_generator.generate_response_with_persona(
                user_input, 
                retrieved_chunks, 
                self.adler_persona,
                self.chat_history,
                mode=input_type,
                distance_to_similarity_func=self.search_engine.get_distance_to_similarity,
                summarize_chunk_func=self.summarize_chunk if hasattr(self, 'summarize_chunk') else None
            )
            response['similarity_score'] = max_similarity
            response['search_iterations'] = iterations_used
            response['search_quality'] = quality_info['quality_score']
            
            # 6-2. Self-learning: Multi-step으로 개선된 후에도 threshold를 넘지 못하면 저장
            if max_similarity < 0.7:
                self._save_qa_to_vectordb(user_input, response["answer"])
        
        # ========================================
        # 스코어링 관련 코드 (주석처리됨 - 필요시 주석 해제)
        # ========================================
        # 7. 로그 저장 (TherapyLogger 사용)
        # response = self.therapy_logger.log_conversation(
        #     user_input=user_input,
        #     response=response,
        #     retrieved_chunks=retrieved_chunks,
        #     enable_scoring=enable_scoring
        # )
        # ========================================
        
        # 대화 히스토리에 추가 (단기 기억)
        self.chat_history.append({
            "user": user_input,
            "assistant": response["answer"]
        })
        
        # 히스토리가 너무 길어지면 오래된 것 제거 (최대 10개 유지)
        if len(self.chat_history) > 10:
            self.chat_history = self.chat_history[-10:]
        
        return response
    
    # ============================================================
    # 로그 관련 기능 (주석처리됨 - 필요시 주석 해제)
    # ============================================================
    # 청크를 한국어로 요약(로그에 저장하기 위함)
    # def summarize_chunk(self, chunk_text: str) -> str:
    #     try:
    #         response = self.openai_client.chat.completions.create(
    #             model="gpt-4o-mini",
    #             messages=[
    #                 {
    #                     "role": "system",
    #                     "content": "당신은 텍스트를 간결하게 요약하는 전문가입니다. 주어진 텍스트를 한국어로 1-2줄로 요약해주세요."
    #                 },
    #                 {
    #                     "role": "user",
    #                     "content": f"다음 텍스트를 한국어로 1-2줄로 요약해주세요:\n\n{chunk_text[:500]}"
    #                 }
    #             ],
    #             temperature=0.3,
    #             max_tokens=100
    #         )
    #         return response.choices[0].message.content.strip()
    #     except Exception as e:
    #         print(f"[경고] 청크 요약 실패: {e}")
    #         return chunk_text[:100] + "..."
    
    # summarize_chunk는 response_generator에서 사용하므로 간단한 버전 제공
    def summarize_chunk(self, chunk_text: str) -> str:
        """청크를 간단히 요약 (스코어링 비활성화 시 사용)"""
        return chunk_text[:100] + "..."

# ============================================================
# 메인 함수 (테스트용)
# ============================================================

def main():

    # 경로 설정 (sourcecode/rag 기준)
    base_dir = Path(__file__).parent.parent.parent
    vector_db_dir = base_dir / "vector_db"
    
    try:
        # RAG 상담 시스템 초기화
        rag_system = RAGTherapySystem(str(vector_db_dir))
        
        # 대화 루프
        while True:
            print("\n" + "-" * 70)
            user_input = input("\n[사용자] ").strip()
            
            if not user_input:
                continue
            
            # 상담 진행
            # response = rag_system.chat(user_input, enable_scoring=True)  # 스코어링 주석처리됨
            response = rag_system.chat(user_input)
            
            # 종료 확인
            if not response['continue_conversation']:
                break
    
    except KeyboardInterrupt:
        print("\n\n프로그램이 사용자에 의해 중단되었습니다.")
    
    except Exception as e:
        print(f"\n[오류] 예상치 못한 오류 발생: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()