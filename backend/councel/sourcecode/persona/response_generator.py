"""
답변 생성 모듈
생성날짜: 2025.12.01
설명: LLM 기반 답변 생성 기능
"""

from typing import List, Dict, Any
from openai import OpenAI


class ResponseGenerator:
    """답변 생성 클래스"""
    
    def __init__(self, openai_client: OpenAI, counseling_keywords: List[str]):
        """
        초기화
        
        Args:
            openai_client: OpenAI 클라이언트
            counseling_keywords: 상담 키워드 리스트
        """
        self.openai_client = openai_client
        self.counseling_keywords = counseling_keywords
    
    def classify_input(self, user_input: str) -> str:
        """사용자의 입력 분류(아들러, 감정/상담, 일반)"""
        user_input_lower = user_input.lower()
        
        # 아들러 키워드 체크
        if "아들러" in user_input or "adler" in user_input_lower:
            return "adler"
        
        # 감정/상담 키워드 체크
        for keyword in self.counseling_keywords:
            if keyword in user_input_lower:
                return "counseling"
        
        return "general"
    
    def is_therapy_related(self, user_input: str) -> bool:
        """입력된 질문이 심리 상담 관련인지 확인"""
        input_type = self.classify_input(user_input)
        return input_type in ["adler", "counseling"]
    
    def _generate_llm_only_response(self, user_input: str, adler_persona: str, chat_history: List[Dict[str, str]], counseling_keywords: List[str]) -> Dict[str, Any]:
        """
        RAG 없이 LLM 단독으로 답변 생성 (유사도가 높을 때)
        
        Args:
            user_input: 사용자 질문
            adler_persona: 아들러 페르소나 프롬프트
            chat_history: 대화 히스토리
            counseling_keywords: 상담 키워드 리스트
            
        Returns:
            답변 딕셔너리
        """
        try:
            # 아들러 페르소나 사용
            persona_prompt = adler_persona
            
            # 대화 히스토리에서 감정 맥락 파악
            emotion_context = ""
            if chat_history:
                recent_emotions = []
                for history in chat_history[-2:]:
                    # 최근 대화에서 감정 키워드 추출
                    for keyword in counseling_keywords[:20]:  # 주요 감정 키워드만
                        if keyword in history["user"].lower():
                            recent_emotions.append(keyword)
                
                if recent_emotions:
                    emotion_context = f"\n[이전 대화 맥락: 사용자가 '{', '.join(set(recent_emotions[:3]))}' 관련 감정을 표현했습니다. 이를 고려하여 답변하세요.]"
            
            # 대화 히스토리 추가
            messages = [{"role": "system", "content": persona_prompt + emotion_context}]
            
            # 최근 3개의 대화만 포함
            for history in chat_history[-3:]:
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
    
    def generate_response_with_persona(self, user_input: str, retrieved_chunks: List[Dict[str, Any]], adler_persona: str, chat_history: List[Dict[str, str]], mode: str = "adler", distance_to_similarity_func=None, summarize_chunk_func=None) -> Dict[str, Any]:
        """
        페르소나 기반 답변 생성
        
        Args:
            user_input: 사용자 질문
            retrieved_chunks: 검색된 청크 리스트
            adler_persona: 아들러 페르소나 프롬프트
            chat_history: 대화 히스토리
            mode: 모드 (adler, counseling, general)
            distance_to_similarity_func: distance를 similarity로 변환하는 함수
            summarize_chunk_func: 청크를 요약하는 함수
            
        Returns:
            답변 딕셔너리
        """
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
            
            # 상세 청크 정보 (로깅용)
            if summarize_chunk_func:
                chunk_summary = summarize_chunk_func(chunk_text)
            else:
                chunk_summary = chunk_text[:100] + "..."
            
            chunk_distance = chunk.get('distance')
            if distance_to_similarity_func and chunk_distance is not None:
                chunk_similarity = distance_to_similarity_func(chunk_distance)
            else:
                chunk_similarity = None
            
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
        persona_prompt = adler_persona
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
        for history in chat_history[-10:]:
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

