"""
평가 자동 실행 스크립트

Usage:
    # 모든 테스트 케이스 실행
    python -m backend.app.domain.brainstorming.evaluation.runner
    
    # 특정 테스트 케이스만 실행
    python -m backend.app.domain.brainstorming.evaluation.runner --case-id tc001
"""

import sys
import json
import argparse
from pathlib import Path
from datetime import datetime
from typing import List
import statistics

# 경로 설정
current_file = Path(__file__).resolve()
module_dir = current_file.parent
project_root = module_dir.parents[4]
sys.path.insert(0, str(project_root))

# 브레인스토밍 모듈 import
from backend.app.domain.brainstorming.session_manager import SessionManager
from backend.app.domain.brainstorming.ephemeral_rag import EphemeralRAG

# ChromaDB 및 OpenAI import
import chromadb
from chromadb.config import Settings as ChromaSettings
from openai import OpenAI
from dotenv import load_dotenv
import os

# 평가 모듈 import
from .judge import BrainstormingJudge
from .models import SingleRunResult, TestCaseResult, EvaluationSummary, TestCaseInput
from .criteria import WEIGHTS
from .test_cases import ALL_TEST_CASES, get_test_case_by_id

load_dotenv()


class EvaluationRunner:
    """평가 실행기"""
    
    def __init__(self):
        """초기화"""
        self.session_manager = SessionManager()
        self.judge = BrainstormingJudge(model="gpt-5", temperature=1.0)
        
        self.openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.llm_model = os.getenv("LLM_MODEL", "gpt-4o")
        self.embedding_model = os.getenv("EMBEDDING_MODEL", "text-embedding-3-large")
        
        # Permanent RAG ChromaDB
        brainstorming_path = module_dir.parent
        persist_directory = str(brainstorming_path / "data" / "chroma")
        
        self.chroma_client = chromadb.PersistentClient(
            path=persist_directory,
            settings=ChromaSettings(anonymized_telemetry=False)
        )
        
        try:
            self.permanent_collection = self.chroma_client.get_collection(
                name="brainstorming_techniques"
            )
            print("✅ Permanent RAG 컬렉션 로드 완료")
        except Exception as e:
            print(f"⚠️  Permanent RAG 컬렉션 로드 실패: {e}")
            self.permanent_collection = None
        
        # 결과 저장 디렉토리
        self.results_dir = module_dir / "results"
        self.results_dir.mkdir(exist_ok=True)
    
    def run_single_test(self, test_case: dict, run_number: int) -> SingleRunResult:
        """
        단일 테스트 실행 (1회)
        
        Args:
            test_case: 테스트 케이스
            run_number: 실행 번호 (1, 2, 3)
        
        Returns:
            SingleRunResult: 실행 결과
        """
        print(f"\n{'='*60}")
        print(f"🔄 실행 {run_number}/3: {test_case['name']}")
        print(f"{'='*60}")
        
        # 1. 세션 생성
        session_id = self.session_manager.create_session()
        print(f"✅ 세션 생성: {session_id}")
        
        session = self.session_manager.get_session(session_id)
        
        try:
            # 2. Q1 목적 입력
            purpose = test_case["q1_purpose"]
            self.session_manager.update_session(session_id, {
                'q1_purpose': purpose
            })
            print(f"✅ Q1 목적 입력 완료")
            
            # 3. Q3 자유연상 입력 + Ephemeral RAG 생성
            associations = test_case["q3_associations"]
            
            ephemeral_rag = EphemeralRAG(
                session_id=session_id,
                collection_name=session['chroma_collection'],
                chroma_client=self.chroma_client
            )
            
            ephemeral_rag.add_associations(associations)
            
            self.session_manager.update_session(session_id, {
                'q3_associations': associations,
                'ephemeral_rag_initialized': True
            })
            print(f"✅ Q3 자유연상 입력 + Ephemeral RAG 생성 완료")
            
            # 4. Ephemeral RAG 키워드 추출
            keywords_data = ephemeral_rag.extract_keywords_by_similarity(
                purpose=purpose,
                top_k=5
            )
            extracted_keywords = [kw['keyword'] for kw in keywords_data]
            print(f"✅ Ephemeral RAG 키워드 추출: {extracted_keywords}")
            
            # 5. Permanent RAG 검색
            rag_docs = []
            if self.permanent_collection:
                purpose_embedding = self.openai_client.embeddings.create(
                    input=purpose,
                    model=self.embedding_model
                ).data[0].embedding
                
                results = self.permanent_collection.query(
                    query_embeddings=[purpose_embedding],
                    n_results=3
                )
                
                if results and results.get('documents') and results['documents'][0]:
                    rag_docs = results['documents'][0]
                    print(f"✅ Permanent RAG 검색 완료: {len(rag_docs)}개 문서")
            
            # 6. 아이디어 생성 (실제 API 로직 복제)
            rag_context = "\n\n".join(rag_docs) if rag_docs else ""
            
            # 도메인 힌트는 생략 (평가에 영향 최소화)
            
            prompt = f"""**역할**: 당신은 유능한 기획자입니다.

**목적**: "{purpose}"

**사용자의 연상 키워드**: {', '.join(extracted_keywords)}

**브레인스토밍 기법 참고**:
{rag_context}

**요구사항**:
1. **직군 추론**: 목적을 보고 사용자의 직군(유튜버, 소상공인, 직장인, 학생, 개발자, 회사원 등)을 파악하세요.

2. **아이디어 2-3개 생성**:
   - 각 아이디어는 **즉시 실행 가능**하고 **구체적**이어야 합니다.
   - 추상적인 표현 금지 (예: "전략 수립", "시스템 구축" 등)
   - 구체적인 행동과 예시 중심 (예: "GPS 기반 주변 맛집 추천", "네이버 API로 쿠폰 노출")

3. **직군별 맞춤**:
   - 유튜버 → 휴대폰 하나로 촬영 가능한 영상 구조
   - 소상공인 → 네이버/인스타로 당장 시작 가능한 홍보
   - 개발자 → 무료 API + 간단한 코드로 빠른 프로토타입
   - 학생 → 발표 자료, 구글 문서, PPT로 바로 작성
   - 회사원 → 팀 리소스 활용 가능한 실행 계획

4. **보고서 스타일 금지, 행동 중심 작성**

5. **현실성 제약 (유연)**:
   ❌ **절대 금지**: 허위 데이터(통계, 시장 규모, 비용, 규제, 경쟁사 실적 등) 언급 금지. 모르면 "조사 필요"라고 명시.
   ✅ **현실적 실행 가능성**: 빠르게 실행 가능(며칠~몇 주), 낮은 초기 투자 부담, 기존 리소스/역량으로 가능(개인/소규모 팀/회사 상황에 따라 유연하게).
   ✅ **행동 중심**: 구체적인 행동과 예시 중심, 거창한 전략이나 보고서 스타일 금지.

**출력 형식**:
아이디어 1: [제목]
- 설명: [구체적인 실행 방법]

아이디어 2: [제목]
- 설명: [구체적인 실행 방법]

아이디어 3: [제목] (선택)
- 설명: [구체적인 실행 방법]
"""
            
            idea_response = self.openai_client.chat.completions.create(
                model=self.llm_model,
                messages=[
                    {"role": "system", "content": "당신은 유능한 기획자입니다."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=1500
            )
            
            ideas_text = idea_response.choices[0].message.content.strip()
            print(f"✅ 아이디어 생성 완료")
            
            # 7. 아이디어 파싱 (간단하게)
            ideas = []
            current_idea = None
            
            for line in ideas_text.split('\n'):
                line = line.strip()
                if not line:
                    continue
                
                if line.startswith('아이디어'):
                    if current_idea:
                        ideas.append(current_idea)
                    
                    title = line.split(':', 1)[1].strip() if ':' in line else line
                    current_idea = {
                        'title': title,
                        'description': '',
                        'analysis': ''
                    }
                elif current_idea and line.startswith('-'):
                    content = line.lstrip('-').strip()
                    if content.startswith('설명:'):
                        content = content[3:].strip()
                    current_idea['description'] += content + '\n'
            
            if current_idea:
                ideas.append(current_idea)
            
            # 8. SWOT 분석 추가
            for idea in ideas:
                swot_prompt = f"""**역할**: 현실적인 기획자

**아이디어**: {idea['title']}
{idea['description']}

**요구사항**:
1. 이 아이디어에 대한 **SWOT 분석** 수행
2. **현실적 관점**에서 분석 (사용자의 상황: 개인/소규모 팀/회사)
3. 각 항목을 **1-2줄**로 간결하게 작성
4. **허위 데이터 절대 금지** (모르면 "조사 필요")

**출력 형식**:
Strengths (강점):
- [강점 1]
- [강점 2]

Weaknesses (약점):
- [약점 1]
- [약점 2]

Opportunities (기회):
- [기회 1]
- [기회 2]

Threats (위협):
- [위협 1]
- [위협 2]
"""
                
                swot_response = self.openai_client.chat.completions.create(
                    model=self.llm_model,
                    messages=[
                        {"role": "system", "content": "당신은 현실적인 기획자입니다."},
                        {"role": "user", "content": swot_prompt}
                    ],
                    temperature=0.6,
                    max_tokens=500
                )
                
                idea['analysis'] = swot_response.choices[0].message.content.strip()
            
            print(f"✅ SWOT 분석 완료: {len(ideas)}개 아이디어")
            
            # 9. 최종 텍스트 포맷
            final_ideas_text = ""
            for i, idea in enumerate(ideas, 1):
                final_ideas_text += f"📌 아이디어 {i}: {idea['title']}\n\n"
                final_ideas_text += f"{idea['description']}\n"
                final_ideas_text += f"📊 SWOT 분석:\n\n{idea['analysis']}\n\n"
            
            # 10. Judge 평가
            print(f"🔍 Judge 평가 중... (GPT-5)")
            scores = self.judge.evaluate(
                question=purpose,
                answer=final_ideas_text,
                permanent_rag_docs=rag_docs,
                ephemeral_keywords=extracted_keywords
            )
            
            weighted_total = scores.weighted_average(WEIGHTS)
            
            print(f"✅ 평가 완료:")
            print(f"   - rag_utilization (RAG 활용도): {scores.rag_utilization}/10")
            print(f"   - completeness (답변 완성도): {scores.completeness}/10")
            print(f"   - relevance (질문-답변 연관도): {scores.relevance}/10")
            print(f"   - creativity (창의성): {scores.creativity}/10")
            print(f"   - practicality (실용성): {scores.practicality}/10")
            print(f"   - weighted_total (가중 평균): {weighted_total}/10")
            
            # 11. 결과 생성
            result = SingleRunResult(
                run_number=run_number,
                session_id=session_id,
                ideas_text=final_ideas_text,
                ideas_count=len(ideas),
                permanent_rag_docs=rag_docs,
                ephemeral_keywords=extracted_keywords,
                scores=scores,
                weighted_total=weighted_total
            )
            
            return result
            
        finally:
            # 12. 세션 정리
            self.session_manager.delete_session(session_id)
            print(f"✅ 세션 정리 완료")
    
    def run_test_case(self, test_case: dict) -> TestCaseResult:
        """
        테스트 케이스 실행 (3회 반복)
        
        Args:
            test_case: 테스트 케이스
        
        Returns:
            TestCaseResult: 테스트 케이스 전체 결과
        """
        print(f"\n{'#'*60}")
        print(f"🚀 테스트 케이스 시작: {test_case['name']} ({test_case['id']})")
        print(f"{'#'*60}")
        
        runs = []
        
        # 3회 실행
        for i in range(1, 4):
            run_result = self.run_single_test(test_case, i)
            runs.append(run_result)
        
        # 평균 계산
        avg_rag = sum(r.scores.rag_utilization for r in runs) / 3
        avg_comp = sum(r.scores.completeness for r in runs) / 3
        avg_rel = sum(r.scores.relevance for r in runs) / 3
        avg_cre = sum(r.scores.creativity for r in runs) / 3
        avg_prac = sum(r.scores.practicality for r in runs) / 3
        avg_weighted = sum(r.weighted_total for r in runs) / 3
        
        average_scores = {
            "rag_utilization": round(avg_rag, 2),
            "completeness": round(avg_comp, 2),
            "relevance": round(avg_rel, 2),
            "creativity": round(avg_cre, 2),
            "practicality": round(avg_prac, 2),
        }
        
        # 표준편차 계산
        weighted_scores = [r.weighted_total for r in runs]
        std_dev = round(statistics.stdev(weighted_scores) if len(weighted_scores) > 1 else 0.0, 2)
        
        result = TestCaseResult(
            test_case_id=test_case["id"],
            test_case_name=test_case["name"],
            runs=runs,
            average_scores=average_scores,
            average_weighted_total=round(avg_weighted, 2),
            std_deviation=std_dev
        )
        
        # 한글 레이블 매핑
        label_map = {
            "rag_utilization": "RAG 활용도",
            "completeness": "답변 완성도",
            "relevance": "질문-답변 연관도",
            "creativity": "창의성",
            "practicality": "실용성"
        }
        
        print(f"\n{'='*60}")
        print(f"📊 테스트 케이스 완료: {test_case['name']}")
        print(f"{'='*60}")
        print(f"평균 점수:")
        for key, value in average_scores.items():
            korean_label = label_map.get(key, key)
            print(f"  - {key} ({korean_label}): {value}/10")
        print(f"weighted_total (가중 평균): {result.average_weighted_total}/10")
        print(f"std_deviation (표준편차): {std_dev} (낮을수록 일관성 높음)")
        
        return result
    
    def save_result(self, result: TestCaseResult):
        """결과 JSON 저장"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{result.test_case_id}_result.json"
        filepath = self.results_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(result.model_dump(), f, ensure_ascii=False, indent=2)
        
        print(f"✅ 결과 저장: {filepath}")
    
    def run_all(self):
        """모든 테스트 케이스 실행"""
        print(f"\n{'#'*60}")
        print(f"🎯 전체 평가 시작")
        print(f"{'#'*60}")
        print(f"테스트 케이스: {len(ALL_TEST_CASES)}개")
        
        all_results = []
        
        for test_case in ALL_TEST_CASES:
            result = self.run_test_case(test_case)
            self.save_result(result)
            all_results.append(result)
        
        # 전체 요약
        overall_avg = sum(r.average_weighted_total for r in all_results) / len(all_results)
        
        summary = EvaluationSummary(
            test_cases=all_results,
            overall_average=round(overall_avg, 2),
            model_info={
                "worker_model": self.llm_model,
                "judge_model": self.judge.model,
                "embedding_model": self.embedding_model
            }
        )
        
        # 요약 저장
        summary_filename = f"summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        summary_filepath = self.results_dir / summary_filename
        
        with open(summary_filepath, 'w', encoding='utf-8') as f:
            json.dump(summary.model_dump(), f, ensure_ascii=False, indent=2)
        
        print(f"\n{'#'*60}")
        print(f"✅ 전체 평가 완료!")
        print(f"{'#'*60}")
        print(f"overall_average (전체 평균 점수): {overall_avg}/10")
        print(f"summary_file (요약 파일): {summary_filepath}")


def main():
    """메인 실행 함수"""
    parser = argparse.ArgumentParser(description="브레인스토밍 평가 자동 실행")
    parser.add_argument(
        "--case-id",
        type=str,
        help="특정 테스트 케이스 ID (예: tc001). 생략 시 전체 실행"
    )
    
    args = parser.parse_args()
    
    runner = EvaluationRunner()
    
    if args.case_id:
        # 특정 케이스만 실행
        test_case = get_test_case_by_id(args.case_id)
        result = runner.run_test_case(test_case)
        runner.save_result(result)
    else:
        # 전체 실행
        runner.run_all()


if __name__ == "__main__":
    main()

