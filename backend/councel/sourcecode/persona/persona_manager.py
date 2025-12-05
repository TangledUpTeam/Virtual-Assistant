"""
페르소나 관리 모듈
생성날짜: 2025.12.01
설명: RAG 기반 페르소나 생성 및 관리 기능
시간복잡도: O(p + q*n + m)
"""

import json
import time
from pathlib import Path
from typing import Optional
from threading import Thread
from openai import OpenAI

# 페르소나 생성 및 관리 클래스
class PersonaManager:
    
    # 초기화 함수
    def __init__(self, openai_client: OpenAI, collection, base_dir: Path):

        # OpenAI, 컬렉션, 기본 경로 설정
        self.openai_client = openai_client
        self.collection = collection
        self.base_dir = base_dir
        
        # 캐시 파일 경로 설정
        cache_dir = base_dir / "cache"
        cache_dir.mkdir(exist_ok=True)
        self.persona_cache_path = cache_dir / "adler_persona_cache.json"
        
        # 페르소나 상태 플래그(기본값)
        self._persona_ready = False
        self._rag_persona_ready = False
        self.adler_persona = None
        
        # 캐시된 페르소나 로드 시도
        cached_persona = self._load_cached_persona()
        if cached_persona:
            self.adler_persona = cached_persona
            self._persona_ready = True
            self._rag_persona_ready = True
        else:
            # 기본 페르소나로 빠르게 시작
            self.adler_persona = self._get_default_persona()
            self._persona_ready = True
            self._rag_persona_ready = False
            print("[정보] 기본 페르소나로 시작 (백그라운드에서 RAG 페르소나 생성 중...)")
            # 백그라운드에서 RAG 페르소나 생성
            self._start_background_persona_generation()
    
    # RAG 기반 페르소나 생성(Vector DB + 웹 검색)
    def generate_persona_with_rag(self) -> str:
        return self._generate_persona_from_rag()
    
    # 프롬프트 엔지니어링으로 페르소나 생성(기본 페르소나)
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
    
    # 페르소나 디폴트 값(프롬프트 엔지니어링으로 만든 페르소나)
    def _get_default_persona(self) -> str:
        return self.generate_persona_with_prompt_engineering()
    
    # 저장된 페르소나 캐시 로드(캐시는 24시간 동안 유효)
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
                        print(f"[정보] 캐시가 만료되었습니다")
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

        # 백그라운드에서 실행하는 함수
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
    
    # 페르소나 준비 여부 확인 함수
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
    
    # RAG 사용 -> 페르소나 생성 함수
    def _generate_persona_from_rag(self) -> str:

        # 검색 쿼리 최적화: 6개 → 3개로 축소 (핵심 개념만 선별)
        persona_queries = [
            "Alfred Adler individual psychology core principles",
            "inferiority complex and superiority striving",
            "social interest and community feeling"
        ]
        
        # 1. Vector DB에서 관련 청크 수집
        all_chunks = []
        for query in persona_queries:
            try:
                # 임베딩 생성
                embedding_response = self.openai_client.embeddings.create(
                    model="text-embedding-3-large",
                    input=query
                )
                query_embedding = embedding_response.data[0].embedding
                
                # 검색
                results = self.collection.query(
                    query_embeddings=[query_embedding],
                    n_results=3
                )
                
                # 결과 포맷팅
                if results['ids'] and results['ids'][0]:
                    for i in range(len(results['ids'][0])):
                        chunk = {
                            'id': results['ids'][0][i],
                            'text': results['documents'][0][i],
                            'metadata': results['metadatas'][0][i],
                            'distance': results['distances'][0][i] if 'distances' in results else None
                        }
                        all_chunks.append(chunk)
            except Exception as e:
                print(f"[경고] 페르소나 생성 중 검색 실패 ({query}): {e}")
        
        # 중복 제거 (id 기준)
        seen_ids = set()
        unique_chunks = []
        for chunk in all_chunks:
            if chunk['id'] not in seen_ids:
                seen_ids.add(chunk['id'])
                unique_chunks.append(chunk)
        
        # 상위 5개 청크만 사용 -> 10개에서 5개로 축소 -> 속도 줄이기 위함
        unique_chunks = unique_chunks[:5]
        
        # 2. 웹 검색으로 최신 정보 수집
        web_info = self._search_web_for_adler()
        
        # 3. 검색된 청크가 없으면 기본 페르소나 사용
        if not unique_chunks and not web_info:
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