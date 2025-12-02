"""
RAG evaluation runner
"""
import json
import os
import time
import re
from typing import List, Dict, Any, Optional
from tqdm import tqdm

from ..core.config import config
from ..core.models import Query
from ..services.rag_pipeline import RAGPipeline
from ..infrastructure.embeddings.openai import OpenAIEmbeddingProvider
from ..infrastructure.llm.openai import OpenAILLMProvider
from .metrics import RetrievalMetrics, GenerationMetrics, EndToEndMetrics


class RAGEvaluator:
    """RAG 시스템 평가 실행기"""
    
    def __init__(
        self,
        pipeline: Optional[RAGPipeline] = None,
        qa_file_path: Optional[str] = None
    ):
        """
        평가기 초기화
        
        Args:
            pipeline: RAG 파이프라인
            qa_file_path: QA 데이터셋 파일 경로
        """
        self.pipeline = pipeline or RAGPipeline()
        self.qa_file_path = qa_file_path or config.eval_qa_file
        self.embedding_provider = OpenAIEmbeddingProvider()
        self.llm_provider = OpenAILLMProvider()
    
    def load_qa_dataset(self) -> List[Dict[str, Any]]:
        """QA 데이터셋 로드"""
        abs_path = os.path.abspath(self.qa_file_path)
        
        if not os.path.exists(abs_path):
            raise FileNotFoundError(f"QA file not found: {abs_path}")
        
        with open(abs_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print(f"[OK] QA 데이터 로드: {len(data)}개 항목")
        return data
    
    def evaluate(
        self,
        top_k: int = 5,
        similarity_threshold: float = 0.75
    ) -> Dict[str, Any]:
        """
        전체 평가 실행
        
        Args:
            top_k: 검색할 문서 개수
            similarity_threshold: 유사도 임계값
            
        Returns:
            평가 결과
        """
        print("\n" + "="*80)
        print("RAG 성능 평가 시작")
        print("="*80 + "\n")
        
        qa_data = self.load_qa_dataset()
        results = []
        
        for idx, qa_item in enumerate(tqdm(qa_data, desc="평가 진행 중")):
            result = self._evaluate_single(
                qa_item=qa_item,
                index=idx,
                top_k=top_k,
                similarity_threshold=similarity_threshold
            )
            results.append(result)
        
        # 요약 통계 계산
        summary = EndToEndMetrics.summarize_results(results)
        
        return {
            'summary': summary,
            'detailed_results': results,
            'config': {
                'top_k': top_k,
                'similarity_threshold': similarity_threshold,
                'qa_file': self.qa_file_path
            }
        }
    
    def _evaluate_single(
        self,
        qa_item: Dict[str, Any],
        index: int,
        top_k: int,
        similarity_threshold: float
    ) -> Dict[str, Any]:
        """단일 QA 평가"""
        question = qa_item['question']
        ground_truth = qa_item['answer']
        
        # 1. RAG 실행
        try:
            generation_result = self.pipeline.run(question=question, top_k=top_k)
            generated_answer = generation_result.answer
            retrieved_chunks = [doc.content for doc in generation_result.source_documents]
        except Exception as e:
            return {
                'index': index,
                'question': question,
                'error': str(e),
                'retrieval_hit': False,
                'semantic_similarity': 0.0,
                'similarity_hit': False,
                'judge_score': 0,
                'keyword_hit': False
            }
        
        # 2. Retrieval Hit Rate
        retrieval_hit, hit_chunk_indices = RetrievalMetrics.calculate_hit_rate(
            retrieved_chunks=retrieved_chunks,
            ground_truth=ground_truth
        )
        
        # 3. Semantic Similarity
        gt_embedding = self.embedding_provider.embed_text(ground_truth)
        gen_embedding = self.embedding_provider.embed_text(generated_answer)
        similarity = GenerationMetrics.calculate_semantic_similarity(gt_embedding, gen_embedding)
        similarity_hit = similarity >= similarity_threshold
        
        # 4. LLM-as-a-judge
        judge_score, judge_reason = self._judge_semantic_match(ground_truth, generated_answer)
        
        # 5. Keyword Hit
        keyword_hit, keyword_count, matched_keywords = GenerationMetrics.calculate_keyword_hit(
            ground_truth=ground_truth,
            generated_answer=generated_answer
        )
        
        return {
            'index': index,
            'question': question,
            'ground_truth': ground_truth,
            'generated_answer': generated_answer,
            'retrieval_hit': bool(retrieval_hit),
            'hit_chunk_indices': hit_chunk_indices,
            'num_retrieved_chunks': len(retrieved_chunks),
            'semantic_similarity': float(similarity),
            'similarity_hit': bool(similarity_hit),
            'judge_score': int(judge_score),
            'judge_reason': judge_reason,
            'keyword_hit': bool(keyword_hit),
            'keyword_count': int(keyword_count),
            'matched_keywords': matched_keywords,
            'section': qa_item.get('section', ''),
            'source': qa_item.get('source', '')
        }
    
    def _judge_semantic_match(self, ground_truth: str, generated_answer: str) -> tuple[int, str]:
        """LLM을 사용한 의미적 일치도 평가"""
        judge_prompt = f"""다음 두 문장이 의미적으로 동일한지 평가하세요.

[정답]
{ground_truth}

[생성된 답변]
{generated_answer}

평가 기준:
- 0점: 의미가 다름
- 1점: 일부 핵심은 맞지만 불완전함
- 2점: 의미적으로 충분히 동일함

출력 형식:
점수: [0, 1, 또는 2]
이유: [간단한 설명]"""
        
        try:
            result = self.llm_provider.generate(
                prompt=judge_prompt,
                temperature=0.0
            )
            
            # 점수 추출
            score_match = re.search(r'점수[:\s]*(\d)', result)
            score = int(score_match.group(1)) if score_match else 0
            score = max(0, min(2, score))
            
            return score, result
            
        except Exception as e:
            return 0, f"Judge evaluation failed: {str(e)}"
    
    def save_results(
        self,
        evaluation_data: Dict[str, Any],
        output_file: str = "evaluation_results.json"
    ):
        """평가 결과 저장"""
        output_path = os.path.join(config.eval_output_full_path, output_file)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(evaluation_data, f, ensure_ascii=False, indent=2)
        
        print(f"\n[OK] 평가 결과 저장: {output_path}")
    
    def print_summary(self, summary: Dict[str, Any]):
        """요약 결과 출력"""
        print("\n" + "="*80)
        print("평가 결과 요약")
        print("="*80)
        print(f"총 질문 수: {summary['total_questions']}")
        print(f"\n[1] Retrieval Hit Rate (가장 중요)")
        print(f"  - Hit: {summary['retrieval_hit_count']}/{summary['total_questions']} "
              f"({summary['retrieval_hit_rate']*100:.1f}%)")
        print(f"\n[2] Semantic Similarity")
        print(f"  - 평균 유사도: {summary['semantic_similarity_avg']:.3f}")
        print(f"  - Threshold 이상: {summary['similarity_hit_count']}/{summary['total_questions']} "
              f"({summary['similarity_hit_rate']*100:.1f}%)")
        print(f"\n[3] LLM-as-a-judge")
        print(f"  - 평균 점수: {summary['judge_score_avg']:.2f}/2.0")
        print(f"\n[4] Keyword Hit")
        print(f"  - Hit: {summary['keyword_hit_count']}/{summary['total_questions']} "
              f"({summary['keyword_hit_rate']*100:.1f}%)")
        print(f"\n[실패 사례]")
        print(f"  - 실패 건수: {summary['failure_count']}")
        print("\n" + "="*80)
