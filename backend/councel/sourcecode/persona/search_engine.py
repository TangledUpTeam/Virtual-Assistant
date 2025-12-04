"""
검색 엔진 모듈
생성날짜: 2025.12.01
설명: Vector DB 검색 및 유사도 계산 기능
시간복잡도: O(i*q*n + k(m+n) + n*m)
"""

import re
import asyncio
from typing import List, Dict, Any
from openai import OpenAI
from openai import AsyncOpenAI


class SearchEngine:
    """검색 및 유사도 계산 클래스"""
    
    def __init__(self, openai_client: OpenAI, collection, counseling_keywords: List[str], async_openai_client: AsyncOpenAI = None):
        """
        초기화
        
        Args:
            openai_client: OpenAI 클라이언트
            collection: ChromaDB 컬렉션
            counseling_keywords: 상담 키워드 리스트
            async_openai_client: AsyncOpenAI 클라이언트 (병렬 처리용)
        """
        self.openai_client = openai_client
        self.async_openai_client = async_openai_client
        self.collection = collection
        self.counseling_keywords = counseling_keywords
    
    def translate_to_english(self, text: str) -> str:
        """사용자의 입력값을 영어로 번역하는 함수"""
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
    
    async def translate_to_english_async(self, text: str) -> str:
        """사용자의 입력값을 영어로 번역하는 비동기 함수"""
        if not self.async_openai_client:
            # AsyncOpenAI 클라이언트가 없으면 동기 메서드 사용
            return self.translate_to_english(text)
        
        try:
            response = await self.async_openai_client.chat.completions.create(
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
    
    def create_query_embedding(self, query_text: str) -> List[float]:
        """사용자의 질문을 임베딩 벡터로 변환"""
        try:
            response = self.openai_client.embeddings.create(
                model="text-embedding-3-large",
                input=query_text
            )
            return response.data[0].embedding
        except Exception as e:
            print(f"[오류] 임베딩 생성 실패: {e}")
            raise
    
    async def create_query_embedding_async(self, query_text: str) -> List[float]:
        """사용자의 질문을 임베딩 벡터로 변환하는 비동기 함수"""
        if not self.async_openai_client:
            # AsyncOpenAI 클라이언트가 없으면 동기 메서드 사용
            return self.create_query_embedding(query_text)
        
        try:
            response = await self.async_openai_client.embeddings.create(
                model="text-embedding-3-large",
                input=query_text
            )
            return response.data[0].embedding
        except Exception as e:
            print(f"[오류] 임베딩 생성 실패: {e}")
            raise
    
    async def retrieve_chunks_async(self, user_input: str, n_results: int = 5, use_reranker: bool = True) -> List[Dict[str, Any]]:
        """
        Vector DB에서 관련 청크 검색 (비동기 버전)
        """
        # 질문을 임베딩으로 변환 (비동기)
        query_embedding = await self.create_query_embedding_async(user_input)
        
        # 유사도 검색 (ChromaDB는 동기식이므로 동기 호출)
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
        
        # 조건부 Re-ranker: 최고 유사도가 0.6 이상이면 생략
        if use_reranker and retrieved_chunks:
            max_similarity = self._get_max_similarity(retrieved_chunks)
            if max_similarity < 0.6:
                retrieved_chunks = self.rerank_chunks(user_input, retrieved_chunks)
        
        return retrieved_chunks
    
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
    
    def rerank_chunks(self, user_input: str, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Re-ranker 사용 -> 검색된 청크들을 관련성 기준으로 재정렬 (LLM 사용)"""
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
            # 조기 종료 조건 강화: 품질 점수가 0.7 이상이면 조기 종료
            if quality_info['quality_score'] >= 0.7:
                print(f"[정보] 조기 종료: 품질 점수 {quality_info['quality_score']:.4f} ≥ 0.7 (반복 {iteration+1}회)")
                break
            
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
        
        # 조건부 Re-ranker: 최고 유사도가 0.6 이상이면 생략
        max_similarity = self._get_max_similarity(all_chunks)
        if all_chunks and max_similarity < 0.6:
            print(f"[정보] Re-ranker 적용 (최고 유사도: {max_similarity:.4f} < 0.6)")
            all_chunks = self.rerank_chunks(user_input, all_chunks)
        else:
            print(f"[정보] Re-ranker 생략 (최고 유사도: {max_similarity:.4f} ≥ 0.6)")
        
        # 상위 n_results개만 반환
        final_chunks = all_chunks[:n_results]
        
        return {
            "chunks": final_chunks,
            "quality_info": quality_info,
            "iterations_used": iteration + 1,
            "total_chunks_found": len(all_chunks)
        }
    
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
    
    def retrieve_chunks(self, user_input: str, n_results: int = 5, use_reranker: bool = True) -> List[Dict[str, Any]]:
        """
        Vector DB에서 관련 청크 검색
        top_n -> 5개 청크 검색(n_results)
        reranker -> true
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
        
        # 조건부 Re-ranker: 최고 유사도가 0.6 이상이면 생략
        if use_reranker and retrieved_chunks:
            max_similarity = self._get_max_similarity(retrieved_chunks)
            if max_similarity < 0.6:
                retrieved_chunks = self.rerank_chunks(user_input, retrieved_chunks)
        
        return retrieved_chunks
    
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
    
    def get_distance_to_similarity(self, distance: float) -> float:
        """외부에서 사용할 수 있도록 public 메서드로 제공"""
        return self._distance_to_similarity(distance)

