"""
RAG 기반 상담 시스템
생성날짜: 2025.11.18
수정날짜: 2025.12.01
설명: 사용자의 질문을 받아 관련 상담 데이터 청크를 검색하고, 이를 바탕으로 적절한 답변 또는 상담을 진행
OpenAI API를 사용한 임베딩 및 답변 생성
주요 변경: 
  - RAG 기반 동적 페르소나 생성 (Vector DB + 웹 검색)
  - LLM 기반 답변 품질 자동 평가 (스코어링 시스템)
  - 청크 한국어 요약 기능
  - Re-ranker 적용 (검색 결과 재정렬)
  - 코드 구조 정리: 상담 관련 기능 / 로그 관련 기능 분리
  - Threshold 기반 RAG + Self-learning 시스템 (2025.12.01)
    * 유사도 0.75 기준 분기: 높으면 LLM 단독, 낮으면 RAG + Self-learning
    * Self-learning: 유사도 낮을 때 Q&A를 Vector DB에 자동 저장
"""

import os
import json
import chromadb
import sys
import re
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
from threading import Thread
from openai import OpenAI
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

# TherapyLogger 임포트 (직접 실행 시와 모듈 import 시 모두 지원)
try:
    from .therapy_logger import TherapyLogger
except ImportError:
    # 직접 실행 시 상대 import가 실패하면 절대 import 시도
    import sys
    from pathlib import Path
    # 현재 파일의 디렉토리를 sys.path에 추가
    current_dir = Path(__file__).parent
    if str(current_dir) not in sys.path:
        sys.path.insert(0, str(current_dir))
    from therapy_logger import TherapyLogger

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
        
        # 로거 초기화 (스코어링 로그 저장용)
        base_dir = Path(__file__).parent.parent.parent  # backend/councel/
        test_dir = base_dir / "test"  # backend/councel/test/
        log_file_prefix = "scoring_log_v7"  # 로그 파일명 (필요시 변경)
        
        self.therapy_logger = TherapyLogger(
            openai_client=self.openai_client,
            log_dir=str(test_dir),
            log_file_prefix=log_file_prefix
        )
        
        # ========================================
        # 페르소나 초기화 (Lazy Loading + Background Task + Caching)
        # ========================================
        
        # 캐시 파일 경로 설정
        cache_dir = base_dir / "cache"
        cache_dir.mkdir(exist_ok=True)
        self.persona_cache_path = cache_dir / "adler_persona_cache.json"
        
        # 페르소나 상태 플래그
        self._persona_ready = False
        self._rag_persona_ready = False
        
        # 캐시된 페르소나 로드 시도
        cached_persona = self._load_cached_persona()
        if cached_persona:
            self.adler_persona = cached_persona
            self._persona_ready = True
            self._rag_persona_ready = True
            print("[정보] 캐시된 RAG 페르소나 로드 완료")
        else:
            # 기본 페르소나로 빠르게 시작
            self.adler_persona = self._get_default_persona()
            self._persona_ready = True
            self._rag_persona_ready = False
            print("[정보] 기본 페르소나로 시작 (백그라운드에서 RAG 페르소나 생성 중...)")
            # 백그라운드에서 RAG 페르소나 생성
            self._start_background_persona_generation()
        
        # ========================================
    
    # ============================================================
    # 상담 관련 기능
    # ============================================================
    
    # 페르소나 생성 함수
    # RAG 기반 페르소나 생성(Vector DB + 웹 검색)
    def generate_persona_with_rag(self) -> str:
        return self._generate_persona_from_rag()
    
    # 프롬프트 엔지니어링으로만 페르소나 생성 
    def generate_persona_with_prompt_engineering(self) -> str:

        return """

            당신은 알프레드 아들러(Alfred Adler)의 개인심리학을 따르는 공감적인 심리학자입니다.

            핵심 원칙:
            1. 열등감과 보상: 모든 인간은 열등감을 느끼며, 이를 극복하려는 우월성 추구가 성장의 동력입니다.
            2. 사회적 관심: 인간은 본질적으로 사회적 존재이며, 공동체 감각이 중요합니다.
            3. 생활양식: 개인의 독특한 생활양식이 행동과 사고를 결정합니다.
            4. 목적론적 관점: 과거보다는 미래의 목표가 현재 행동을 결정합니다.
            5. 격려: 용기를 북돋우는 것이 치료의 핵심입니다.

            답변 방식 (3단계 구조 필수):
            1단계 - 감정 인정: 먼저 상대방의 감정을 있는 그대로 인정하고 공감합니다.
               - "~하셨군요", "~느끼시는군요", "~한 마음이 드셨겠어요"
               - 감정을 판단하지 않고 있는 그대로 받아들입니다.
            
            2단계 - 아들러 관점 재해석: 그 감정과 상황을 성장의 기회로 재해석합니다.
               - 열등감을 성장 동력으로 재구성
               - 사회적 관심과 공동체 감각 연결
               - 목표 지향적 관점 제시
            
            3단계 - 격려 및 실천 방안 제시: 상대방의 내적 힘과 가능성을 믿으며 격려하고 실천 가능한 방향을 제시합니다.
               - "~할 수 있습니다", "~의 기회입니다"
               - 구체적이고 실천 가능한 방향 제시

            말투:
            - 따뜻하고 수용적인 톤 유지
            - 경청하고 있음을 느끼게 하는 표현 사용
            - "~하셨군요", "~느끼시는군요" 등 반영적 경청 기법 활용
            - 판단하지 않고 이해하려는 자세
            - 2~3문장으로 간결하되 공감이 느껴지도록 작성

            중요사항:
            - 반드시 감정 인정 → 재해석 → 격려 순서로 답변
            - 상대방의 감정을 최소화하거나 무시하지 않기
            - "하지만", "그래도" 등 감정을 부정하는 표현 자제
            - 상대방이 자신의 감정을 충분히 표현했다고 느끼게 하기

        """
    
    # 페로스나 디폴트 값(프롬프트 엔지니어링 사용한 페르소나)
    def _get_default_persona(self) -> str:
        return self.generate_persona_with_prompt_engineering()
    
    # 캐시된 페르소나 로드(캐시는 24시간 유효)
    def _load_cached_persona(self) -> Optional[str]:

        try:
            if self.persona_cache_path.exists():
                with open(self.persona_cache_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # 캐시 유효성 검사 (24시간 이내)
                    cache_timestamp = data.get('timestamp', 0)
                    current_time = time.time()
                    if current_time - cache_timestamp < 86400:  # 24시간 = 86400초
                        return data.get('persona')
                    else:
                        print(f"[정보] 캐시가 만료되었습니다 (생성 시각: {time.ctime(cache_timestamp)})")
        except Exception as e:
            print(f"[경고] 캐시 로드 실패: {e}")
        return None
    
    # 페르소나를 캐시에 저장
    def _save_persona_cache(self, persona: str):

        try:
            data = {
                'persona': persona,
                'timestamp': time.time()
            }
            with open(self.persona_cache_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[경고] 캐시 저장 실패: {e}")
    
    # 백그라운드에서 RAG 페르소나 생성 및 캐싱
    def _start_background_persona_generation(self):

        def generate_in_background():
            try:
                rag_persona = self._generate_persona_from_rag()
                self.adler_persona = rag_persona
                self._rag_persona_ready = True
                self._save_persona_cache(rag_persona)
                print("[정보] RAG 페르소나 로딩 완료!")
            except Exception as e:
                print(f"[경고] 백그라운드 페르소나 생성 실패: {e}")
                print("[정보] 기본 페르소나를 계속 사용합니다.")
                import traceback
                traceback.print_exc()
        
        # 백그라운드 스레드 시작 (daemon=True로 서버 종료 시 자동 정리)
        thread = Thread(target=generate_in_background, daemon=True)
        thread.start()
    
    # RAG 페르소나 생성 완료 여부 확인
    def is_rag_persona_ready(self) -> bool:
        return self._rag_persona_ready
    
    # 웹 검색 -> 아들러 정보 수집(페르소나 생성 용도)
    def _search_web_for_adler(self) -> str:

        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert on Alfred Adler's individual psychology. Provide a comprehensive summary of Adler's core principles and therapeutic approaches."
                    },
                    {
                        "role": "user",
                        "content": """Provide a detailed summary of Alfred Adler's individual psychology including:
1. Core principles (inferiority complex, superiority striving, social interest, etc.)
2. Lifestyle and life patterns
3. Therapeutic techniques and encouragement methods
4. Teleological perspective and goal orientation
5. Key concepts for counseling practice

Keep it concise but comprehensive."""
                    }
                ],
                temperature=0.3,
                max_tokens=800
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"[경고] 웹 검색 실패: {e}")
            return ""
    
    # RAG 기반 페르소나 생성(Vector DB + 웹 검색)
    def _generate_persona_from_rag(self) -> str:

        # 아들러 핵심 개념 검색 쿼리들
        persona_queries = [
            "Alfred Adler individual psychology core principles",
            "inferiority complex and superiority striving",
            "social interest and community feeling",
            "lifestyle and life style pattern",
            "encouragement therapy techniques",
            "teleological perspective goal orientation"
        ]
        
        # 1. Vector DB에서 관련 청크 수집
        all_chunks = []
        for query in persona_queries:
            try:
                chunks = self.retrieve_chunks(query, n_results=3)
                all_chunks.extend(chunks)
            except Exception as e:
                print(f"[경고] 페르소나 생성 중 검색 실패 ({query}): {e}")
        
        # 중복 제거 (id 기준)
        seen_ids = set()
        unique_chunks = []
        for chunk in all_chunks:
            if chunk['id'] not in seen_ids:
                seen_ids.add(chunk['id'])
                unique_chunks.append(chunk)
        
        # 상위 10개 청크만 사용
        unique_chunks = unique_chunks[:10]
        
        # 2. 웹 검색으로 최신 정보 수집
        web_info = self._search_web_for_adler()
        
        # 3. 검색된 청크가 없으면 기본 페르소나 사용
        if not unique_chunks and not web_info:
            print("[경고] 페르소나 생성용 자료를 찾을 수 없어 기본 페르소나를 사용합니다.")
            return self._get_default_persona()
        
        # 4. Vector DB 청크 텍스트 추출
        context_parts = []
        if unique_chunks:
            context_parts.append("=== Vector DB 자료 ===")
            for i, chunk in enumerate(unique_chunks, 1):
                context_parts.append(f"[자료 {i}] {chunk['text'][:500]}")  # 각 청크 최대 500자
        
        # 5. 웹 검색 정보 추가
        if web_info:
            context_parts.append("\n=== 웹 검색 정보 ===")
            context_parts.append(web_info)
        
        context = "\n\n".join(context_parts)
        
        # 6. LLM을 사용하여 페르소나 프롬프트 생성
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system", 
                        "content": "You are a prompt engineering expert. Create a persona prompt for a therapist based on Adler's individual psychology."
                    },
                    {
                        "role": "user",
                        "content": f"""다음은 알프레드 아들러의 개인심리학에 관한 자료입니다:

                        {context}

                        위 자료를 바탕으로 다음 형식으로 페르소나 프롬프트를 작성해주세요:

                        **형식:**
                        당신은 알프레드 아들러(Alfred Adler)의 개인심리학을 따르는 공감적인 심리학자입니다.

                        핵심 원칙:
                        1. [원칙 1]
                        2. [원칙 2]
                        3. [원칙 3]
                        4. [원칙 4]
                        5. [원칙 5]

                        답변 방식 (3단계 구조 필수):
                        1단계 - 감정 인정: [감정 인정 방법 설명]
                        2단계 - 아들러 관점 재해석: [재해석 방법 설명]
                        3단계 - 격려: [격려 방법 설명]

                        말투:
                        - 따뜻하고 수용적인 톤
                        - 반영적 경청 기법 ("~하셨군요", "~느끼시는군요")
                        - 판단하지 않고 이해하려는 자세
                        - [추가 말투 특징]

                        **중요 사항:**
                        - 반드시 감정 인정 → 재해석 → 격려 순서로 답변
                        - 상대방의 감정을 최소화하거나 무시하지 않기
                        - "하지만", "그래도" 등 감정을 부정하는 표현 자제
                        - 열등감을 성장의 기회로 재해석
                        - 사회적 관심과 공동체 감각 강조
                        - 목표 지향적 관점 제시
                        - 2~3문장으로 간결하되 공감이 느껴지도록 작성
                        - 공감적 경청을 최우선으로 하되 아들러 이론 통합

                        페르소나 프롬프트만 출력해주세요. 다른 설명은 불필요합니다."""
                    }
                ],
                temperature=0.3,
                max_tokens=500
            )
            
            generated_persona = response.choices[0].message.content.strip()
            return generated_persona
            
        except Exception as e:
            print(f"[경고] 페르소나 생성 실패, 기본 페르소나 사용: {e}")
            return self._get_default_persona()
    
    # 사용자의 입력값을 영어로 변역하는 함수
    def translate_to_english(self, text: str) -> str:

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
    
    # 사용자의 질문을 임베딩 벡터로 변환
    def create_query_embedding(self, query_text: str) -> List[float]:

        try:
            response = self.openai_client.embeddings.create(
                model="text-embedding-3-large",
                input=query_text
            )
            return response.data[0].embedding
        except Exception as e:
            print(f"[오류] 임베딩 생성 실패: {e}")
            raise
    
    # ChromaDB의 distance 값을 코사인 유사도로 변환
    def _distance_to_similarity(self, distance: float) -> float:
        """
        ChromaDB의 L2 distance를 유사도 점수로 변환
        
        Args:
            distance: ChromaDB에서 반환된 L2 distance 값
            
        Returns:
            0~1 사이의 유사도 점수 (1에 가까울수록 유사)
        """
        # L2 distance를 유사도로 변환: 1 / (1 + distance)
        # distance가 0이면 similarity는 1 (완전 일치)
        # distance가 클수록 similarity는 0에 가까워짐
        return 1.0 / (1.0 + distance)
    
    # Self-learning: Q&A를 Vector DB에 저장
    def _save_qa_to_vectordb(self, user_query: str, llm_response: str):
        """
        사용자 질문과 LLM 답변을 Vector DB에 저장 (Self-learning)
        
        Args:
            user_query: 사용자 질문
            llm_response: LLM 답변
        """
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
            embedding = self.create_query_embedding(user_query)
            
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
    
    # 사용자의 입력 분류(아들러, 감정/상담, 일반)
    def classify_input(self, user_input: str) -> str:

        user_input_lower = user_input.lower()
        
        # 아들러 키워드 체크
        if "아들러" in user_input or "adler" in user_input_lower:
            return "adler"
        
        # 감정/상담 키워드 체크
        for keyword in self.counseling_keywords:
            if keyword in user_input_lower:
                return "counseling"
        
        return "general"
    
    # 입력된 질문이 심리 상담 관련인지 확인
    def is_therapy_related(self, user_input: str) -> bool:

        input_type = self.classify_input(user_input)
        return input_type in ["adler", "counseling"]
    
    # Re-ranker 사용 -> 검색된 청크들을 관련성 기준으로 재정렬
    # LLM 사용
    def rerank_chunks(self, user_input: str, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:

        if not chunks or len(chunks) <= 1:
            return chunks
        
        try:
            # 각 청크의 관련성 평가를 위한 프롬프트 구성
            chunks_text = "\n\n".join([
                f"[청크 {i+1}]\n{chunk['text'][:300]}..." 
                for i, chunk in enumerate(chunks)
            ])
            
            evaluation_prompt = f"""다음은 사용자 질문과 검색된 청크들입니다.

                사용자 질문: {user_input}

                검색된 청크들:
                {chunks_text}

                위 청크들을 사용자 질문과의 관련성 순서대로 번호만 나열해주세요.
                예: 3, 1, 2, 5, 4 (가장 관련성 높은 것부터)

                번호만 출력해주세요. 다른 설명은 불필요합니다."""
            
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert at evaluating document relevance. Rank documents by their relevance to the user's question."
                    },
                    {
                        "role": "user",
                        "content": evaluation_prompt
                    }
                ],
                temperature=0.1,  # 매우 낮은 temperature로 일관된 평가
                max_tokens=50
            )
            
            # 순위 파싱
            ranking_text = response.choices[0].message.content.strip()
            # 숫자만 추출
            ranked_indices = [int(x) - 1 for x in re.findall(r'\d+', ranking_text)]  # 1-based to 0-based
            
            # 유효한 인덱스만 필터링
            valid_indices = [idx for idx in ranked_indices if 0 <= idx < len(chunks)]
            
            # 재정렬
            if valid_indices and len(valid_indices) == len(chunks):
                reranked_chunks = [chunks[idx] for idx in valid_indices]
                # 재정렬된 청크에 rerank_score 추가
                for i, chunk in enumerate(reranked_chunks):
                    chunk['rerank_score'] = len(chunks) - i  # 높은 순위일수록 높은 점수
                return reranked_chunks
            else:
                # 파싱 실패 시 원본 반환
                print(f"[경고] Re-ranker 순위 파싱 실패. 원본 순서 유지.")
                return chunks
                
        except Exception as e:
            print(f"[경고] Re-ranker 실행 실패: {e}")
            return chunks
    
    # 감정 키워드 탐지 및 가중치 계산
    def _calculate_emotion_boost(self, user_input: str, chunk_text: str) -> float:
        """
        사용자 입력과 청크에서 감정 키워드를 탐지하여 유사도 보너스 계산
        
        Args:
            user_input: 사용자 질문
            chunk_text: 청크 텍스트
            
        Returns:
            유사도 보너스 (0.0 ~ 0.2)
        """
        user_input_lower = user_input.lower()
        chunk_text_lower = chunk_text.lower()
        
        # 사용자 입력에서 감정 키워드 추출
        user_emotions = set()
        for keyword in self.counseling_keywords:
            if keyword in user_input_lower:
                user_emotions.add(keyword)
        
        if not user_emotions:
            return 0.0
        
        # 청크에서 매칭되는 감정 키워드 개수 계산
        matching_emotions = 0
        for emotion in user_emotions:
            if emotion in chunk_text_lower:
                matching_emotions += 1
        
        # 매칭 비율에 따라 보너스 계산 (최대 0.2)
        if matching_emotions > 0:
            boost = min(0.2, matching_emotions * 0.05)
            return boost
        
        return 0.0
    
    # 검색 결과 품질 평가
    def _evaluate_search_quality(self, chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        검색된 청크의 품질을 평가
        
        Args:
            chunks: 검색된 청크 리스트
            
        Returns:
            품질 평가 결과 (avg_similarity, diversity_score, quality_score)
        """
        if not chunks:
            return {
                "avg_similarity": 0.0,
                "diversity_score": 0.0,
                "quality_score": 0.0,
                "needs_improvement": True
            }
        
        # 평균 유사도 계산
        similarities = []
        for chunk in chunks:
            distance = chunk.get('distance')
            if distance is not None:
                similarity = self._distance_to_similarity(distance)
                similarities.append(similarity)
        
        avg_similarity = sum(similarities) / len(similarities) if similarities else 0.0
        
        # 다양성 점수 계산 (서로 다른 소스의 비율)
        sources = set()
        for chunk in chunks:
            source = chunk.get('metadata', {}).get('source', 'unknown')
            sources.add(source)
        
        diversity_score = len(sources) / len(chunks) if chunks else 0.0
        
        # 종합 품질 점수 (평균 유사도 70% + 다양성 30%)
        quality_score = avg_similarity * 0.7 + diversity_score * 0.3
        
        # 품질 개선 필요 여부 (0.6 미만이면 재검색 필요)
        needs_improvement = quality_score < 0.6
        
        return {
            "avg_similarity": avg_similarity,
            "diversity_score": diversity_score,
            "quality_score": quality_score,
            "needs_improvement": needs_improvement
        }
    
    # LLM 기반 쿼리 확장
    def _expand_query_with_llm(self, user_input: str) -> List[str]:
        """
        사용자 질문을 LLM으로 확장하여 관련 검색어 생성
        
        Args:
            user_input: 사용자 질문
            
        Returns:
            확장된 검색어 리스트
        """
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert at expanding search queries for Adlerian psychology counseling. Generate related search terms."
                    },
                    {
                        "role": "user",
                        "content": f"""다음 질문과 관련된 검색어를 생성해주세요:

질문: {user_input}

다음 관점에서 3-5개의 관련 검색어를 생성하세요:
1. 핵심 감정이나 심리 상태
2. 아들러 심리학 관련 개념 (열등감, 사회적 관심, 생활양식 등)
3. 유사한 상황이나 문제

검색어만 쉼표로 구분하여 출력하세요. 예: inferiority complex, social interest, lifestyle pattern"""
                    }
                ],
                temperature=0.3,
                max_tokens=150
            )
            
            # 응답에서 검색어 추출
            expanded_terms = response.choices[0].message.content.strip()
            # 쉼표로 분리하고 정리
            terms = [term.strip() for term in expanded_terms.split(',')]
            
            return terms[:5]  # 최대 5개
            
        except Exception as e:
            print(f"[경고] 쿼리 확장 실패: {e}")
            return []
    
    # Multi-step 반복 검색 시스템
    def _iterative_search_with_query_expansion(self, user_input: str, max_iterations: int = 2, n_results: int = 5) -> Dict[str, Any]:
        """
        반복적 검색 개선 시스템 (Multi-step Self-learning)
        
        Step 1: 초기 검색
        Step 2: 결과 품질 평가
        Step 3: 품질이 낮으면 쿼리 확장
        Step 4: 재검색 및 결과 병합
        Step 5: 최대 2회 반복 (초기 검색 1회 + 쿼리 확장 검색 1회)
        
        Args:
            user_input: 사용자 질문
            max_iterations: 최대 반복 횟수
            n_results: 검색할 청크 개수
            
        Returns:
            검색 결과 딕셔너리 (chunks, quality_info, iterations_used)
        """
        all_chunks = []
        seen_ids = set()
        iteration = 0
        
        # Step 1: 초기 검색
        print(f"[정보] Multi-step 검색 시작 (최대 {max_iterations}회)")
        initial_chunks = self.retrieve_chunks(user_input, n_results=n_results, use_reranker=False)
        
        for chunk in initial_chunks:
            if chunk['id'] not in seen_ids:
                all_chunks.append(chunk)
                seen_ids.add(chunk['id'])
        
        # Step 2: 품질 평가
        quality_info = self._evaluate_search_quality(all_chunks)
        print(f"[정보] 초기 검색 품질: {quality_info['quality_score']:.4f} (평균 유사도: {quality_info['avg_similarity']:.4f})")
        
        # Step 3-5: 품질이 낮으면 반복 검색
        while quality_info['needs_improvement'] and iteration < max_iterations - 1:
            iteration += 1
            print(f"[정보] 검색 품질 개선 시도 {iteration}/{max_iterations-1}")
            
            # 쿼리 확장
            expanded_queries = self._expand_query_with_llm(user_input)
            
            if not expanded_queries:
                print(f"[경고] 쿼리 확장 실패, 반복 검색 중단")
                break
            
            print(f"[정보] 확장된 검색어: {', '.join(expanded_queries)}")
            
            # 확장된 쿼리로 재검색
            for query in expanded_queries:
                new_chunks = self.retrieve_chunks(query, n_results=3, use_reranker=False)
                for chunk in new_chunks:
                    if chunk['id'] not in seen_ids:
                        all_chunks.append(chunk)
                        seen_ids.add(chunk['id'])
            
            # 재평가
            quality_info = self._evaluate_search_quality(all_chunks)
            print(f"[정보] 개선 후 품질: {quality_info['quality_score']:.4f}")
            
            # 품질이 충분히 개선되었으면 중단
            if not quality_info['needs_improvement']:
                print(f"[정보] 검색 품질 목표 달성 (반복 {iteration+1}회)")
                break
        
        # Re-ranker 적용 (최종 결과에만)
        if all_chunks:
            all_chunks = self.rerank_chunks(user_input, all_chunks)
        
        # 상위 n_results개만 반환
        final_chunks = all_chunks[:n_results]
        
        return {
            "chunks": final_chunks,
            "quality_info": quality_info,
            "iterations_used": iteration + 1,
            "total_chunks_found": len(all_chunks)
        }
    
    # 하이브리드 검색 (벡터 + 키워드)
    def _hybrid_search(self, user_input: str, n_results: int = 5) -> List[Dict[str, Any]]:
        """
        벡터 검색과 키워드 검색을 결합한 하이브리드 검색
        
        Args:
            user_input: 사용자 질문
            n_results: 검색할 청크 개수
            
        Returns:
            검색된 청크 리스트 (감정 가중치 적용됨)
        """
        # 벡터 검색
        query_embedding = self.create_query_embedding(user_input)
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results * 2  # 더 많이 검색 후 필터링
        )
        
        # 결과 포맷팅 및 감정 가중치 적용
        retrieved_chunks = []
        if results['ids'] and results['ids'][0]:
            for i in range(len(results['ids'][0])):
                chunk = {
                    'id': results['ids'][0][i],
                    'text': results['documents'][0][i],
                    'metadata': results['metadatas'][0][i],
                    'distance': results['distances'][0][i] if 'distances' in results else None
                }
                
                # 기본 유사도 계산
                base_similarity = self._distance_to_similarity(chunk['distance']) if chunk['distance'] is not None else 0.0
                
                # 감정 가중치 계산
                emotion_boost = self._calculate_emotion_boost(user_input, chunk['text'])
                
                # 최종 유사도 (가중치 적용)
                final_similarity = min(1.0, base_similarity + emotion_boost)
                
                chunk['base_similarity'] = base_similarity
                chunk['emotion_boost'] = emotion_boost
                chunk['final_similarity'] = final_similarity
                
                retrieved_chunks.append(chunk)
        
        # 최종 유사도 기준으로 정렬
        retrieved_chunks.sort(key=lambda x: x['final_similarity'], reverse=True)
        
        # 상위 n_results개만 반환
        return retrieved_chunks[:n_results]
    
    # Vector DB에서 관련 청크 검색
    # top_n -> 5개 청크 검색(n_results)
    # reranker -> true
    def retrieve_chunks(self, user_input: str, n_results: int = 5, use_reranker: bool = True) -> List[Dict[str, Any]]:

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
        
        # Re-ranker 적용
        if use_reranker and retrieved_chunks:
            retrieved_chunks = self.rerank_chunks(user_input, retrieved_chunks)
        
        return retrieved_chunks
    
    # 검색된 청크 중 최고 유사도 반환
    def _get_max_similarity(self, retrieved_chunks: List[Dict[str, Any]]) -> float:
        """
        검색된 청크들 중 가장 높은 유사도 점수 반환
        
        Args:
            retrieved_chunks: 검색된 청크 리스트
            
        Returns:
            최고 유사도 점수 (0~1)
        """
        if not retrieved_chunks:
            return 0.0
        
        max_similarity = 0.0
        for chunk in retrieved_chunks:
            distance = chunk.get('distance')
            if distance is not None:
                similarity = self._distance_to_similarity(distance)
                max_similarity = max(max_similarity, similarity)
        
        return max_similarity
    
    # RAG 없이 LLM 단독으로 답변 생성
    def _generate_llm_only_response(self, user_input: str) -> Dict[str, Any]:
        """
        RAG 없이 LLM 단독으로 답변 생성 (유사도가 높을 때)
        
        Args:
            user_input: 사용자 질문
            
        Returns:
            답변 딕셔너리
        """
        try:
            # 아들러 페르소나 사용
            persona_prompt = self.adler_persona
            
            # 대화 히스토리에서 감정 맥락 파악
            emotion_context = ""
            if self.chat_history:
                recent_emotions = []
                for history in self.chat_history[-2:]:
                    # 최근 대화에서 감정 키워드 추출
                    for keyword in self.counseling_keywords[:20]:  # 주요 감정 키워드만
                        if keyword in history["user"].lower():
                            recent_emotions.append(keyword)
                
                if recent_emotions:
                    emotion_context = f"\n[이전 대화 맥락: 사용자가 '{', '.join(set(recent_emotions[:3]))}' 관련 감정을 표현했습니다. 이를 고려하여 답변하세요.]"
            
            # 대화 히스토리 추가
            messages = [{"role": "system", "content": persona_prompt + emotion_context}]
            
            # 최근 3개의 대화만 포함
            for history in self.chat_history[-3:]:
                messages.append({"role": "user", "content": history["user"]})
                messages.append({"role": "assistant", "content": history["assistant"]})
            
            # 공감적 답변 유도 프롬프트
            enhanced_input = f"""{user_input}

[중요: 반드시 3단계 구조로 답변하세요]
1. 먼저 사용자의 감정을 인정하고 공감
2. 아들러 관점에서 재해석
3. 격려와 희망 제시"""
            
            messages.append({"role": "user", "content": enhanced_input})
            
            # OpenAI API 호출
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                temperature=0.3,
                max_tokens=200  # 공감 표현을 위해 약간 늘림
            )
            
            answer = response.choices[0].message.content.strip()
            
            return {
                "answer": answer,
                "used_chunks": [],
                "used_chunks_detailed": [],
                "mode": "llm_only",
                "continue_conversation": True,
                "similarity_score": None  # LLM only 모드에서는 유사도 없음
            }
        
        except Exception as e:
            print(f"[오류] LLM 단독 답변 생성 실패: {e}")
            return {
                "answer": "죄송합니다. 답변 생성 중 오류가 발생했습니다. 다시 시도해주세요.",
                "used_chunks": [],
                "used_chunks_detailed": [],
                "mode": "error",
                "continue_conversation": True
            }
    
    # 페르소나 기반 답변 생성
    def generate_response_with_persona(self, user_input: str, retrieved_chunks: List[Dict[str, Any]], mode: str = "adler") -> Dict[str, Any]:

        # 검색된 청크가 없는 경우
        if not retrieved_chunks:
            return {
                "answer": "죄송합니다. 관련된 자료를 찾을 수 없습니다. 다른 질문을 해주시겠어요?",
                "used_chunks": [],
                "used_chunks_detailed": [],
                "continue_conversation": True
            }
        
        # 컨텍스트 구성
        context_parts = []
        used_chunks = []
        used_chunks_detailed = []
        
        for i, chunk in enumerate(retrieved_chunks[:3], 1):  # 상위 3개 청크 사용
            chunk_text = chunk['text']
            source = chunk['metadata'].get('source', '알 수 없음')
            context_parts.append(f"[자료 {i}]\n{chunk_text}\n(출처: {source})")
            used_chunks.append(f"{source}: {chunk_text[:50]}...")
            
            # 상세 청크 정보 (로깅용 - summarize_chunk는 로그 섹션에 정의)
            chunk_summary = self.summarize_chunk(chunk_text)
            chunk_distance = chunk.get('distance')
            chunk_similarity = self._distance_to_similarity(chunk_distance) if chunk_distance is not None else None
            
            used_chunks_detailed.append({
                "chunk_id": chunk['id'],
                "source": source,
                "metadata": chunk['metadata'],
                "summary_kr": chunk_summary,
                "distance": chunk_distance,
                "similarity": chunk_similarity  # 코사인 유사도 추가
            })
        
        context = "\n\n".join(context_parts)
        
        # 사용자 입력에서 감정 키워드 추출
        detected_emotions = []
        user_input_lower = user_input.lower()
        for keyword in self.counseling_keywords[:30]:  # 주요 감정 키워드
            if keyword in user_input_lower:
                detected_emotions.append(keyword)
        
        emotion_note = ""
        if detected_emotions:
            emotion_note = f"\n[감지된 감정: {', '.join(detected_emotions[:3])} - 이 감정들을 먼저 인정하고 공감해주세요]"
        
        # 아들러 페르소나 사용
        persona_prompt = self.adler_persona
        user_message = f"""참고 자료:
{context}

사용자 질문: {user_input}{emotion_note}

**답변 구조 (반드시 준수):**

1단계 - 감정 인정 (1문장):
   - 사용자의 감정을 있는 그대로 인정하고 공감합니다.
   - 예: "~하셨군요", "~느끼시는 마음이 충분히 이해됩니다"
   - 절대 "하지만", "그래도"로 시작하지 마세요.

2단계 - 아들러 관점 재해석 (1문장):
   - 위 참고 자료를 바탕으로 아들러 개인심리학 관점에서 재해석합니다.
   - 열등감을 성장의 기회로, 어려움을 목표 달성의 과정으로 재구성합니다.

3단계 - 격려 및 실천 방안 제시 (1~2문장):
   - 사용자의 내적 힘과 가능성을 믿으며 구체적으로 격려합니다.
   - 실천 가능한 방향을 제시합니다.

**중요:**
- 반드시 3단계 순서대로 답변 (총 3~4문장)
- 실천 방안을 제시할 때에는 구체적으로 제시하고 실천 가능한 방향을 제시
- 감정을 판단하거나 최소화하지 않기
- 따뜻하고 수용적인 톤 유지"""
        
        # 대화 히스토리 추가 (단기 기억)
        messages = [{"role": "system", "content": persona_prompt}]
        
        # 최근 10개의 대화만 포함 (컨텍스트 길이 관리)
        for history in self.chat_history[-10:]:
            messages.append({"role": "user", "content": history["user"]})
            messages.append({"role": "assistant", "content": history["assistant"]})
        
        messages.append({"role": "user", "content": user_message})
        
        # OpenAI API 호출
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                temperature=0.3,  # 낮은 temperature로 일관된 답변 생성
                max_tokens=250  # 답변 길이 제한 (1000 -> 200 -> 100 -> 80 -> 150 -> 250)
            )
            
            answer = response.choices[0].message.content.strip()
            
            return {
                "answer": answer,
                "used_chunks": used_chunks,
                "used_chunks_detailed": used_chunks_detailed,
                "mode": mode,
                "continue_conversation": True
            }
        
        except Exception as e:
            print(f"[오류] OpenAI 답변 생성 실패: {e}")
            return {
                "answer": "죄송합니다. 답변 생성 중 오류가 발생했습니다. 다시 시도해주세요.",
                "used_chunks": [],
                "used_chunks_detailed": [],
                "mode": mode,
                "continue_conversation": True
            }
    
    # 상담 함수(사용자 입력 -> 답변 생성 + 품질 평가)
    def chat(self, user_input: str, enable_scoring: bool = True) -> Dict[str, Any]:

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
        input_type = self.classify_input(user_input)
        
        # 2. 영어로 번역 (Vector DB 검색용)
        english_input = self.translate_to_english(user_input)
        
        # 3. Threshold 고정 (0.7)
        threshold = 0.7
        print(f"[정보] Threshold 설정: {threshold}")
        
        # 4. Multi-step 반복 검색 시스템 사용 (쿼리 확장 1회로 제한)
        search_result = self._iterative_search_with_query_expansion(english_input, max_iterations=2, n_results=5)
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
                similarity = self._distance_to_similarity(chunk['distance'])
                max_similarity = max(max_similarity, similarity)
        
        print(f"[정보] 최고 유사도: {max_similarity:.4f} (Threshold: {threshold})")
        
        # 6. Threshold 분기
        if max_similarity >= threshold:
            # Case A: 유사도 ≥ threshold -> RAG 없이 LLM 단독 답변
            print(f"[정보] Threshold 분기: LLM 단독 모드 (유사도 {max_similarity:.4f} ≥ {threshold})")
            response = self._generate_llm_only_response(user_input)
            response['similarity_score'] = max_similarity
            response['search_iterations'] = iterations_used
        else:
            # Case B: 유사도 < threshold -> RAG + Self-learning
            print(f"[정보] Threshold 분기: RAG + Self-learning 모드 (유사도 {max_similarity:.4f} < {threshold})")
            
            # 6-1. RAG 기반 답변 생성
            response = self.generate_response_with_persona(user_input, retrieved_chunks, mode=input_type)
            response['similarity_score'] = max_similarity
            response['search_iterations'] = iterations_used
            response['search_quality'] = quality_info['quality_score']
            
            # 6-2. Self-learning: Multi-step으로 개선된 후에도 threshold를 넘지 못하면 저장
            if max_similarity < 0.7:
                self._save_qa_to_vectordb(user_input, response["answer"])
        
        # 7. 로그 저장 (TherapyLogger 사용)
        response = self.therapy_logger.log_conversation(
            user_input=user_input,
            response=response,
            retrieved_chunks=retrieved_chunks,
            enable_scoring=enable_scoring
        )
        
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
    # 로그 관련 기능
    # ============================================================
    
    # 청크를 한국어로 요약(로그에 저장하기 위함)
    def summarize_chunk(self, chunk_text: str) -> str:

        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "당신은 텍스트를 간결하게 요약하는 전문가입니다. 주어진 텍스트를 한국어로 1-2줄로 요약해주세요."
                    },
                    {
                        "role": "user",
                        "content": f"다음 텍스트를 한국어로 1-2줄로 요약해주세요:\n\n{chunk_text[:500]}"
                    }
                ],
                temperature=0.3,
                max_tokens=100
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"[경고] 청크 요약 실패: {e}")
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
            
            # 상담 진행 (스코어링 활성화)
            response = rag_system.chat(user_input, enable_scoring=True)
            
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