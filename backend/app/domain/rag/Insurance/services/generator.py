"""
Answer generation service
"""
import time
from typing import List, Optional

from .models import Query, InsuranceDocument, GenerationResult
from ..config import insurance_config
from .exceptions import GenerationException
from .providers import SimpleLLMProvider



class Generator:
    """답변 생성 서비스"""
    
    # 시스템 프롬프트
    SYSTEM_PROMPT = """당신은 보험 및 의료급여 전문가입니다. 
제공된 보험 약관, 법규, 의료급여법 문서를 바탕으로 정확하고 명확한 답변을 제공하세요.

**핵심 규칙:**
1. 제공된 컨텍스트에서 관련 정보를 **적극적으로 찾아서** 답변하세요
2. 문서에 개별 조항이나 개념이 설명되어 있다면, 이를 **종합하여** 질문에 답하세요
3. "차이", "비교", "구분" 등을 묻는 질문의 경우:
   - 문서에 각각의 내용이 있다면 이를 비교하여 답변
   - 명시적인 비교가 없어도 각 내용을 설명하면서 차이점을 도출
4. 컨텍스트에 **전혀** 관련 정보가 없는 경우에만 "제공된 문서에서 해당 정보를 확인할 수 없습니다"라고 답변
5. 법률 조항, 숫자, 날짜는 정확히 인용
6. 일반인이 이해하기 쉽게 설명
7. 문서의 정보를 최대한 활용하여 유용한 답변을 제공하세요

**예시:**
- 질문: "A와 B의 차이는?" → 문서에 A 설명, B 설명이 따로 있다면 → 각각을 설명하고 차이점을 정리
- 질문: "조건은 무엇인가?" → 문서에 관련 법 조항이 있다면 → 해당 내용을 바탕으로 조건 설명"""
    
    def __init__(
        self,
        llm_provider: SimpleLLMProvider,
        system_prompt: Optional[str] = None
    ):
        """
        답변 생성기 초기화
        
        Args:
            llm_provider: LLM 제공자
            system_prompt: 커스텀 시스템 프롬프트
        """
        self.llm_provider = llm_provider
        self.system_prompt = system_prompt or self.SYSTEM_PROMPT
    
    def generate(
        self,
        query: Query,
        context_documents: List[InsuranceDocument],
        include_sources: bool = True
    ) -> GenerationResult:
        """
        쿼리와 컨텍스트로 답변 생성
        
        Args:
            query: 쿼리 객체
            context_documents: 컨텍스트 문서 리스트
            include_sources: 출처 포함 여부
            
        Returns:
            생성 결과
        """
        start_time = time.time()
        
        try:
            # 컨텍스트 구성
            context = self._build_context(context_documents)
            
            # 사용자 프롬프트 구성
            user_prompt = self._build_user_prompt(query.question, context)
            
            # LLM 호출
            answer = self.llm_provider.generate(
                prompt=user_prompt,
                system_prompt=self.system_prompt
            )
            
            generation_time = (time.time() - start_time) * 1000  # ms
            
            # 신뢰도 점수 계산 (간단한 휴리스틱)
            confidence_score = self._calculate_confidence(answer, context_documents)
            
            return GenerationResult(
                answer=answer,
                query=query,
                source_documents=context_documents,
                confidence_score=confidence_score,
                generation_time_ms=generation_time,
                metadata={
                    "model": self.llm_provider.get_model_name(),
                    "num_context_docs": len(context_documents),
                    "context_length": len(context)
                }
            )
            
        except Exception as e:
            raise GenerationException(
                f"Failed to generate answer: {str(e)}",
                details={"query": query.question}
            )
    
    def generate_with_context(
        self,
        question: str,
        context: str
    ) -> str:
        """
        질문과 컨텍스트 문자열로 직접 답변 생성
        
        Args:
            question: 질문
            context: 컨텍스트 문자열
            
        Returns:
            답변
        """
        user_prompt = self._build_user_prompt(question, context)
        
        return self.llm_provider.generate(
            prompt=user_prompt,
            system_prompt=self.system_prompt
        )
    
    def validate_answer(
        self,
        question: str,
        context: str,
        generated_answer: str
    ) -> tuple[bool, str]:
        """
        생성된 답변이 컨텍스트에 근거하는지 검증
        
        Args:
            question: 질문
            context: 컨텍스트
            generated_answer: 생성된 답변
            
        Returns:
            (검증 성공 여부, 검증 결과 또는 수정된 답변)
        """
        validation_prompt = f"""다음 답변이 제공된 컨텍스트에 실제로 근거하는지 판단하세요.

**질문:** {question}

**컨텍스트:**
{context}

**생성된 답변:**
{generated_answer}

**판단 기준:**
- 답변 내용이 컨텍스트에 명시되어 있는가?
- 추측이나 일반 상식으로 답변한 부분은 없는가?

근거하지 않으면 "정보 없음"만 출력하세요.
근거한다면 "검증 완료"를 출력하세요."""
        
        result = self.llm_provider.generate(
            prompt=validation_prompt,
            temperature=0.0
        )
        
        if "정보 없음" in result:
            return False, "제공된 문서에서 해당 정보를 찾을 수 없습니다."
        
        return True, generated_answer
    
    def _build_context(self, documents: List[InsuranceDocument]) -> str:
        """컨텍스트 문자열 구성"""
        context_parts = []
        
        for idx, doc in enumerate(documents, 1):
            source = doc.metadata.get('source', '알 수 없음')
            context_parts.append(f"[문서 {idx}] 출처: {source}\n{doc.content}")
        
        return "\n\n".join(context_parts)
    
    def _build_user_prompt(self, question: str, context: str) -> str:
        """사용자 프롬프트 구성"""
        return f"""<컨텍스트>
{context}
</컨텍스트>

<질문>
{question}
</질문>

위 컨텍스트를 바탕으로 질문에 답변하세요. 컨텍스트에 정보가 없다면 "제공된 문서에서 해당 정보를 확인할 수 없습니다"라고 답변하세요.

답변:"""
    
    def _calculate_confidence(
        self,
        answer: str,
        context_documents: List[InsuranceDocument]
    ) -> float:
        """
        답변 신뢰도 점수 계산 (휴리스틱)
        
        Args:
            answer: 생성된 답변
            context_documents: 컨텍스트 문서
            
        Returns:
            신뢰도 점수 (0.0 ~ 1.0)
        """
        # 간단한 휴리스틱: "제공된 문서에서" 같은 표현이 있으면 낮은 신뢰도
        if "제공된 문서에서" in answer and "확인할 수 없" in answer:
            return 0.1
        
        # 답변 길이가 적절한지
        if len(answer) < 20:
            return 0.3
        
        # 컨텍스트 문서 개수에 따른 가중치
        doc_score = min(len(context_documents) / 5.0, 1.0)
        
        return 0.7 + (doc_score * 0.3)  # 0.7 ~ 1.0
