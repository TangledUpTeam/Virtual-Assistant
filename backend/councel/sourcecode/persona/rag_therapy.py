"""
RAG 기반 상담 시스템
생성날짜: 2025.11.18
수정날짜: 2025.11.28
설명: 사용자의 질문을 받아 관련 상담 데이터 청크를 검색하고, 이를 바탕으로 적절한 답변 또는 상담을 진행
OpenAI API를 사용한 임베딩 및 답변 생성
주요 변경: 
  - RAG 기반 동적 페르소나 생성 (Vector DB + 웹 검색)
  - LLM 기반 답변 품질 자동 평가 (스코어링 시스템)
  - 청크 한국어 요약 기능
  - Re-ranker 적용 (검색 결과 재정렬)
  - 코드 구조 정리: 상담 관련 기능 / 로그 관련 기능 분리
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
        self.counseling_keywords = [
            '힘들어', '상담', '짜증', '우울', '불안', '스트레스',
            '고민', '걱정', '슬프', '외로', '화나', '답답',
            '아들러', 'adler', 'counseling', 'therapy', 'help',
            'depressed', 'anxious', '심리'
        ]
        
        # 대화 히스토리 (단기 기억)
        self.chat_history = []
        
        # 로거 초기화 (스코어링 로그 저장용)
        base_dir = Path(__file__).parent.parent.parent  # backend/councel/
        test_dir = base_dir / "test"  # backend/councel/test/
        log_file_prefix = "scoring_log_v3"  # 로그 파일명 (필요시 변경)
        
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

            당신은 알프레드 아들러(Alfred Adler)의 개인심리학을 따르는 심리학자입니다.

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
            - **반드시 1~2문장 이내로 매우 간결하게 답변**

            말투:
            - 격려적이고 희망적인 표현 사용
            - "~할 수 있습니다", "~의 기회입니다" 등 긍정적 표현
            - 명확하고 실용적인 조언
            - 불필요한 설명은 생략하고 핵심만 전달

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
                        당신은 알프레드 아들러(Alfred Adler)의 개인심리학을 따르는 심리학자입니다.

                        핵심 원칙:
                        1. [원칙 1]
                        2. [원칙 2]
                        3. [원칙 3]
                        4. [원칙 4]
                        5. [원칙 5]

                        답변 방식:
                        - [방식 1]
                        - [방식 2]
                        - [방식 3]
                        - [방식 4]
                        - [방식 5]
                        - **반드시 1~2문장 이내로 매우 간결하게 답변**

                        말투:
                        - [말투 1]
                        - [말투 2]
                        - [말투 3]
                        - [말투 4]

                        **중요 사항:**
                        - 답변은 1~2문장 이내로 매우 간결하게 작성
                        - 열등감을 성장의 기회로 재해석
                        - 사회적 관심과 공동체 감각 강조
                        - 목표 지향적 관점 제시
                        - 격려적이고 희망적인 톤 유지
                        - 상대방의 감정에 공감하고 이해하도록 노력

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
            used_chunks_detailed.append({
                "chunk_id": chunk['id'],
                "source": source,
                "metadata": chunk['metadata'],
                "summary_kr": chunk_summary,
                "distance": chunk.get('distance')
            })
        
        context = "\n\n".join(context_parts)
        
        # 아들러 페르소나 사용
        persona_prompt = self.adler_persona
        user_message = f"""참고 자료:
                            {context}

                            사용자 질문: {user_input}

                            위 자료를 바탕으로 아들러 개인심리학 관점에서 답변해주세요.
                            격려와 용기를 주는 톤으로, 열등감을 성장의 기회로 재해석하고 사회적 관심을 강조해주세요.

                            **중요: 답변은 1~2문장 이내로 매우 간결하게 작성해주세요.**
                        """
        
        # 대화 히스토리 추가 (단기 기억)
        messages = [{"role": "system", "content": persona_prompt}]
        
        # 최근 3개의 대화만 포함 (컨텍스트 길이 관리)
        for history in self.chat_history[-3:]:
            messages.append({"role": "user", "content": history["user"]})
            messages.append({"role": "assistant", "content": history["assistant"]})
        
        messages.append({"role": "user", "content": user_message})
        
        # OpenAI API 호출
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                temperature=0.3,  # 낮은 temperature로 일관된 답변 생성
                max_tokens=80  # 답변 길이 제한 (1000 -> 200 -> 100 -> 80)
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
        
        # 3. 입력 유형에 따른 처리 (모든 모드에서 아들러 페르소나 사용)
        retrieved_chunks = self.retrieve_chunks(english_input, n_results=5)
        
        response = self.generate_response_with_persona(user_input, retrieved_chunks, mode=input_type)
        
        # 4. 로그 저장 (TherapyLogger 사용)
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