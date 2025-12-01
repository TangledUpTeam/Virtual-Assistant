"""
브레인스토밍 API 엔드포인트

아이디어 생성 워크플로우:
1. POST /session - 세션 시작
2. POST /purpose - Q1 목적 입력
3. GET /warmup/{session_id} - Q2 워밍업 질문 생성
4. POST /confirm/{session_id} - Q2 확인
5. POST /associations/{session_id} - Q3 자유연상 입력
6. GET /ideas/{session_id} - 아이디어 생성 및 분석
7. DELETE /session/{session_id} - 세션 삭제

변경사항 (2024-11-30):
- Ephemeral RAG: ChromaDB → JSON 기반으로 변경
- 영구 RAG: ChromaDB 유지 (data/chroma/)
- 임시 RAG: JSON 파일 (data/ephemeral/{session_id}/associations.json)
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Optional
import sys
from pathlib import Path
import shutil
from datetime import datetime, timedelta

# 브레인스토밍 모듈 경로 추가
brainstorming_path = Path(__file__).resolve().parent.parent.parent.parent / "domain" / "brainstorming"
sys.path.insert(0, str(brainstorming_path))

from session_manager import SessionManager
from ephemeral_rag import EphemeralRAG, cleanup_old_sessions as cleanup_ephemeral_sessions
from domain_hints import get_domain_hint, format_hint_for_prompt

# ChromaDB import (영구 RAG 전용)
import chromadb
from chromadb.config import Settings as ChromaSettings
from openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv()

router = APIRouter()

# 전역 인스턴스
session_manager = SessionManager()
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
llm_model = os.getenv("LLM_MODEL", "gpt-4o")
embedding_model = os.getenv("EMBEDDING_MODEL", "text-embedding-3-large")

# ============================================================
# 영구 RAG ChromaDB 클라이언트 (브레인스토밍 기법만!)
# ============================================================
module_dir = brainstorming_path
persist_directory = str(module_dir / "data" / "chroma")

chroma_client = chromadb.PersistentClient(
    path=persist_directory,
    settings=ChromaSettings(anonymized_telemetry=False)
)

try:
    permanent_collection = chroma_client.get_collection(
        name="brainstorming_techniques"
    )
    print("✅ 영구 RAG 컬렉션 로드 완료 (brainstorming API)")
    print(f"   📁 경로: {persist_directory}")
    print(f"   📊 문서 수: {permanent_collection.count()}개")
except Exception as e:
    print(f"⚠️  영구 RAG 컬렉션 로드 실패: {e}")
    permanent_collection = None


# === Pydantic 모델 ===

class SessionResponse(BaseModel):
    """세션 생성 응답"""
    session_id: str
    message: str


class PurposeRequest(BaseModel):
    """Q1 목적 입력 요청"""
    session_id: str
    purpose: str


class PurposeResponse(BaseModel):
    """Q1 목적 입력 응답"""
    message: str
    purpose: str


class WarmupResponse(BaseModel):
    """Q2 워밍업 질문 응답"""
    questions: List[str]


class ConfirmResponse(BaseModel):
    """Q2 확인 응답"""
    message: str


class AssociationsRequest(BaseModel):
    """Q3 자유연상 입력 요청"""
    session_id: str
    associations: List[str]


class AssociationsResponse(BaseModel):
    """Q3 자유연상 입력 응답"""
    message: str
    count: int


class IdeaResponse(BaseModel):
    """아이디어 생성 응답"""
    ideas: List[Dict[str, str]]  # [{"title": "...", "description": "...", "analysis": "..."}]


class DeleteResponse(BaseModel):
    """세션 삭제 응답"""
    message: str


# === API 엔드포인트 ===

@router.post("/session", response_model=SessionResponse)
async def create_session():
    """
    새로운 브레인스토밍 세션 시작
    
    시작 전에 오래된 Ephemeral RAG 데이터를 자동으로 청소합니다.
    
    Returns:
        SessionResponse: 세션 ID와 메시지
    """
    try:
        # 🧹 1. 오래된 세션 청소 (5분 이상)
        # Ephemeral 데이터는 임시 데이터이므로 빠르게 정리
        cleanup_ephemeral_sessions(max_age_seconds=300)
        
        # 2. 새 세션 생성
        session_id = session_manager.create_session()
        return SessionResponse(
            session_id=session_id,
            message="새로운 브레인스토밍 세션이 시작되었습니다."
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"세션 생성 실패: {str(e)}")


@router.post("/purpose", response_model=PurposeResponse)
async def submit_purpose(request: PurposeRequest):
    """
    Q1: 목적/도메인 입력
    
    Args:
        request: 세션 ID와 목적
        
    Returns:
        PurposeResponse: 확인 메시지
    """
    try:
        # 세션 존재 여부 확인
        session = session_manager.get_session(request.session_id)
        if not session:
            raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다.")
        
        # 세션에 목적 저장
        session_manager.update_session(request.session_id, {
            'q1_purpose': request.purpose
        })
        
        return PurposeResponse(
            message="목적이 설정되었습니다.",
            purpose=request.purpose
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"목적 입력 실패: {str(e)}")


@router.get("/warmup/{session_id}", response_model=WarmupResponse)
async def get_warmup_questions(session_id: str):
    """
    Q2: LLM 기반 워밍업 질문 생성
    
    Args:
        session_id: 세션 ID
        
    Returns:
        WarmupResponse: 워밍업 질문 리스트 (2-3개)
    """
    try:
        # 세션 존재 여부 확인
        session = session_manager.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다.")
        
        purpose = session.get('q1_purpose')
        if not purpose:
            raise HTTPException(status_code=400, detail="Q1 목적이 입력되지 않았습니다.")
        
        # LLM으로 워밍업 질문 생성
        prompt = f"""사용자가 "{purpose}"에 대한 아이디어를 생성하려고 합니다.

**목표**: 사용자의 직군/상황에 맞는 구체적인 워밍업 질문 2-3개 생성

**직군 추론**: 목적을 보고 사용자가 속한 직군(유튜버, 소상공인, 직장인, 학생, 개발자 등)을 파악하세요.

**워밍업 질문 생성 규칙**:
1. 사용자의 직군/상황에 맞는 **구체적인 질문**
2. 예: "누군가에게 자랑하고 싶은 결과물이라면 누구인가요?"
3. 2-3개의 질문만 생성
4. 각 질문은 간결하고 명확하게
5. 질문만 출력 (다른 설명 없이)

**출력 형식**:
- 질문1
- 질문2
- 질문3 (선택)
"""
        
        response = openai_client.chat.completions.create(
            model=llm_model,
            messages=[
                {"role": "system", "content": "당신은 유능한 기획자입니다."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.8,
            max_tokens=300
        )
        
        # 질문 파싱
        content = response.choices[0].message.content.strip()
        questions = [q.strip().lstrip('-').strip() for q in content.split('\n') if q.strip()]
        
        # 세션에 저장
        session_manager.update_session(session_id, {
            'q2_warmup_questions': questions
        })
        
        return WarmupResponse(questions=questions)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"워밍업 질문 생성 실패: {str(e)}")


@router.post("/confirm/{session_id}", response_model=ConfirmResponse)
async def confirm_warmup(session_id: str):
    """
    Q2: 워밍업 확인 (프론트엔드에서 "네" 버튼 클릭 시)
    
    Args:
        session_id: 세션 ID
        
    Returns:
        ConfirmResponse: 확인 메시지
    """
    try:
        # 세션 존재 여부 확인
        session = session_manager.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다.")
        
        return ConfirmResponse(message="워밍업이 확인되었습니다. Q3로 진행하세요.")
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"확인 실패: {str(e)}")


@router.post("/associations/{session_id}", response_model=AssociationsResponse)
async def submit_associations(session_id: str, request: AssociationsRequest):
    """
    Q3: 자유연상 입력 (JSON 기반 Ephemeral RAG)
    
    Args:
        session_id: 세션 ID
        request: 자유연상 키워드 리스트
        
    Returns:
        AssociationsResponse: 확인 메시지 및 입력 개수
    """
    try:
        # 세션 존재 여부 확인
        session = session_manager.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다.")
        
        # Ephemeral RAG 초기화 (JSON 기반)
        ephemeral_rag = EphemeralRAG(session_id=session_id)
        
        # 임베딩 및 JSON 저장
        ephemeral_rag.add_associations(request.associations)
        
        # 세션에 저장
        session_manager.update_session(session_id, {
            'q3_associations': request.associations,
            'ephemeral_rag_initialized': True
        })
        
        return AssociationsResponse(
            message="자유연상 입력이 완료되었습니다.",
            count=len(request.associations)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"자유연상 입력 실패: {str(e)}")


@router.get("/ideas/{session_id}", response_model=IdeaResponse)
async def generate_ideas(session_id: str):
    """
    아이디어 생성 및 SWOT 분석
    
    Args:
        session_id: 세션 ID
        
    Returns:
        IdeaResponse: 아이디어 리스트
    """
    try:
        # 세션 존재 여부 확인
        session = session_manager.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다.")
        
        purpose = session.get('q1_purpose')
        associations = session.get('q3_associations', [])
        
        if not purpose or not associations:
            raise HTTPException(status_code=400, detail="Q1 또는 Q3 데이터가 없습니다.")
        
        # Ephemeral RAG 초기화 (JSON 기반)
        ephemeral_rag = EphemeralRAG(session_id=session_id)
        
        # Q3 연상 키워드 추출 (유사도 기반)
        keywords_data = ephemeral_rag.extract_keywords_by_similarity(
            purpose=purpose,
            top_k=5
        )
        
        # 키워드만 추출 (keyword 필드에서)
        extracted_keywords = [kw['keyword'] for kw in keywords_data]
        
        # 영구 RAG에서 브레인스토밍 기법 검색 (ChromaDB)
        rag_context = ""
        if permanent_collection:
            purpose_embedding = openai_client.embeddings.create(
                input=purpose,
                model=embedding_model
            ).data[0].embedding
            
            results = permanent_collection.query(
                query_embeddings=[purpose_embedding],
                n_results=3
            )
            
            if results and results.get('documents') and results['documents'][0]:
                # RAG 기법 포맷팅: 번호와 구분선 추가
                formatted_techniques = []
                for i, doc in enumerate(results['documents'][0], 1):
                    formatted_techniques.append(f"📌 **기법 {i}**:\n{doc}")
                rag_context = "\n\n---\n\n".join(formatted_techniques)
        
        # 도메인 힌트 가져오기
        domain_hint = get_domain_hint(purpose)
        hint_text = format_hint_for_prompt(domain_hint) if domain_hint else ""
        
        # 아이디어 생성 프롬프트
        prompt = f"""**역할**: 당신은 창의적이면서도 현실적인 기획자입니다.

**목적**: "{purpose}"

**사용자의 연상 키워드**: {', '.join(extracted_keywords)}

**브레인스토밍 기법 (필수 활용)**:

{rag_context}

💡 **기법 활용 방법**: 
- **각 아이디어마다 위의 기법 중 1-2개를 명시적으로 적용하세요**
- 예: "SCAMPER의 결합(Combine) 기법으로 A와 B를 합침" 
- 예: "마인드맵으로 중심 키워드에서 확장한 아이디어"

---

{hint_text}

**🚨 절대 규칙 (위반 시 답변 무효)**

1. **허구 데이터 절대 금지**
   ❌ 통계, 시장규모, 비용, 법규, 경쟁사 실적 등을 **절대 지어내지 마세요**
   ❌ "2023년 40억 명", "월 10만원", "연평균 9.1% 성장" 같은 **허구의 수치 금지**
   ✅ 모르면 언급하지 말고, 알고 있는 범위만 조심스럽게 표현하세요

2. **현실적 실행 가능성** (사용자 상황에 맞게 조절)
   ✅ 빠르게 시작 가능한 것 (며칠~몇 주 내)
   ✅ 초기 투자 부담이 크지 않은 범위
   ✅ 현재 가진 자원/역량으로 시도 가능한 것
   ❌ "일론 머스크와 협업", "대기업 CEO 섭외", "수억 투자 유치" 같은 **극단적으로 비현실적 제안 금지**

3. **직군별 맞춤**
   - 유튜버 → 휴대폰 하나로 촬영 가능한 영상 구조
   - 소상공인 → 네이버/인스타로 당장 시작 가능한 홍보
   - 개발자 → 무료 API + 간단한 코드로 빠른 프로토타입
   - 학생 → 발표 자료, 구글 문서, PPT로 바로 작성
   - 회사원 → 팀 리소스 활용 가능한 실행 계획
   - 1인 사업자 → 최소 비용, 최대 효과

4. **보고서 스타일 금지, 행동 중심 작성**
   ❌ "효율적인 마케팅 전략 수립을 통해..." (거창한 전략)
   ✅ "네이버 블로그 만들고, 첫 글 3개 올린다. 제목에 '지역명+업종' 넣는다." (구체적 행동)

5. **나쁜 예 (절대 금지)**
   - "글로벌 시장 진출 전략..."
   - "대형 투자사 IR..."
   - "유명인 섭외..."
   - "특허 출원 후..."
   - "개발 비용 2000만원..."

6. **좋은 예 (이렇게 작성)**
   - "카카오톡 오픈채팅방 만들어서 주변 친구 10명 초대"
   - "인스타그램에 휴대폰으로 찍은 사진 3장 올리고, 해시태그 5개 달기"
   - "구글 스프레드시트로 일주일 매출 기록표 만들기"

---

**핵심 요구사항**:

1. **직군 파악**: 목적을 보고 사용자의 직군/상황을 정확히 파악하세요
   - 예: "1인 웹 개발자" → 시간/리소스 제약, 차별화 필요

2. **문제 중심 접근**:
   - 💡 핵심 문제: 사용자가 **실제로 겪고 있는 구체적 불편함**을 먼저 정의
   - 예: "소상공인은 쿠폰을 수기로 관리하다 단골 이탈률이 높음"
   - ❌ 나쁜 예: "시장 경쟁이 치열함" (너무 추상적)

3. **브레인스토밍 기법으로 아이디어 발상**:
   - **위 RAG 기법을 반드시 1개 이상 명시적으로 사용**
   - SCAMPER: 대체/결합/응용/확대/축소/변경/제거
   - Mind Map: 키워드에서 가지 확장
   - 역발상: 반대로 생각
   - 연관어 조합: 키워드 2-3개 결합

4. **개선 방안 (기대 효과)**:
   - 이 아이디어가 문제를 **어떻게** 해결하는지
   - **구체적인 효과**를 제시 (매출 증가, 시간 절약, 고객 만족도 등)
   - 예: "통합 플랫폼으로 고객 재방문율 30% 향상 기대"

5. **분석 결과** (각 항목 1-2줄, 간결하게):
   - 강점: 이 아이디어만의 차별점, 구체적으로
   - 약점: 현실적인 리스크, 솔직하게
   - 기회: 시장 트렌드와의 연결
   - 위협: 경쟁 상황, 구체적으로

**금지 사항**:
❌ 마크다운 볼드체(**) 사용 금지, 이모지와 일반 텍스트만
❌ "1주차", "2주차" 같은 로드맵 제외
❌ 기술 스택 상세 나열 (Firebase, OAuth 등)

**출력 형식**:

아이디어 1: [구체적인 제목]

💡 핵심 문제:
[사용자가 실제로 겪는 구체적 불편함, 2-3줄]

✨ 개선 방안:
[이 아이디어가 문제를 어떻게 해결하는지, 2-3줄]

🎯 기대 효과:
[이 아이디어로 얻을 수 있는 구체적인 효과, 2-3줄]
예: "고객 재방문율 30% 향상 예상", "업무 시간 하루 2시간 절약"

🎨 발상 기법:
[이 아이디어를 떠올릴 때 사용한 브레인스토밍 기법과 사고 과정]

**좋은 예시**:
- "SCAMPER의 '결합(Combine)' 기법으로 발상했습니다. 음성 녹음과 텍스트 메모 기능을 결합하면 어떨까?라는 질문에서 시작했습니다."
- "마인드맵 기법을 활용했습니다. '취업 준비'를 중심에 두고 정보 수집 → 정리 → 알림으로 가지를 확장했습니다."
- "역발상 기법으로 접근했습니다. '손님이 오게 하기'가 아니라 '손님이 직접 만들게 하기(DIY 키트)'로 발상을 전환했습니다."

**나쁜 예시** (❌ 절대 금지):
- "SCAMPER를 적용해 계산기를 만들었습니다" (기법을 제품에 적용하는 것처럼 오해)
- "마인드맵으로 앱을 개발했습니다" (기법이 개발 방법인 것처럼 오해)

📊 분석 결과:
• 강점: [2개, 각 1줄, 구체적으로]
• 약점: [2개, 각 1줄, 솔직하게]
• 기회: [2개, 각 1줄, 현실적으로]
• 위협: [2개, 각 1줄, 구체적으로]

---

아이디어 2: [구체적인 제목]

💡 핵심 문제:
[...]

✨ 개선 방안:
[...]

🎯 기대 효과:
[...]

🎨 발상 기법:
[...]

📊 분석 결과:
• 강점: [...]
• 약점: [...]
• 기회: [...]
• 위협: [...]

---

아이디어 3: [구체적인 제목] (선택)
(동일한 형식)

**마지막 체크**:
✅ 순서: 핵심 문제 → 개선 방안 → 기대 효과 → 발상 기법 → 분석 결과
✅ 브레인스토밍 기법을 명시적으로 활용했나요?
✅ 기대 효과가 구체적이고 측정 가능한가요?
✅ 🎨 발상 기법 섹션에서 "어떤 사고 과정"을 거쳤는지 명확히 설명했나요?
✅ 기법을 제품/서비스에 적용하는 것처럼 오해되지 않게 작성했나요?
✅ 핵심 문제가 구체적인가요?
✅ 허구 데이터 없나요?
✅ 구체적인 행동 예시가 있나요?
"""
        
        idea_response = openai_client.chat.completions.create(
            model=llm_model,
            messages=[
                {"role": "system", "content": "당신은 현실적인 기획자입니다. 허구의 통계나 비용을 절대 지어내지 않으며, 사용자가 가진 자원과 역량으로 빠르게 시작 가능한 아이디어를 제안합니다. 거창한 전략이 아닌, 구체적으로 실행 가능한 행동 위주로 설명합니다. **반드시 2-3개의 완전한 아이디어를 생성해야 합니다.**"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=2000
        )
        
        ideas_text = idea_response.choices[0].message.content.strip()
        
        # 🔥 새로운 파싱 로직 (순서: 핵심 문제 → 개선 방안 → 기대 효과 → 발상 기법 → 분석 결과)
        ideas = []
        current_idea = None
        current_section = None  # 'problem', 'solution', 'effect', 'technique', 'analysis'
        
        import re
        
        for line in ideas_text.split('\n'):
            line = line.strip()
            if not line or line == '---':
                continue
            
            # 아이디어 시작 (정규식으로 정확히 매칭)
            # "아이디어 1:", "아이디어 2:", "아이디어 3:" 형식만 인식
            if re.match(r'^아이디어\s+\d+:', line):
                if current_idea:
                    ideas.append(current_idea)
                
                # 제목 추출
                title = line.split(':', 1)[1].strip() if ':' in line else line
                current_idea = {
                    'title': title,
                    'description': '',
                    'analysis': ''
                }
                current_section = None
            
            # 섹션 구분 (순서대로)
            elif current_idea:
                if '💡 핵심 문제' in line or '핵심 문제:' in line:
                    current_section = 'problem'
                    current_idea['description'] += '\n💡 핵심 문제:\n'
                elif '✨ 개선 방안' in line or '개선 방안:' in line:
                    current_section = 'solution'
                    current_idea['description'] += '\n\n✨ 개선 방안:\n'
                elif '🎯 기대 효과' in line or '기대 효과:' in line:
                    current_section = 'effect'
                    current_idea['description'] += '\n\n🎯 기대 효과:\n'
                elif '🎨 발상 기법' in line or '발상 기법:' in line:
                    current_section = 'technique'
                    current_idea['description'] += '\n\n🎨 발상 기법:\n'
                elif '📊 분석 결과' in line or '분석 결과:' in line or '📊 SWOT 분석' in line or 'SWOT 분석:' in line:
                    current_section = 'analysis'
                    # 🔥 "분석 결과"로 통일
                    if '📊 분석 결과' not in current_idea['description']:
                        current_idea['description'] += '\n\n📊 분석 결과:\n'
                
                # 내용 추가
                elif current_section == 'problem':
                    current_idea['description'] += line + '\n'
                elif current_section == 'solution':
                    current_idea['description'] += line + '\n'
                elif current_section == 'effect':
                    current_idea['description'] += line + '\n'
                elif current_section == 'technique':
                    current_idea['description'] += line + '\n'
                elif current_section == 'analysis':
                    current_idea['description'] += line + '\n'
        
        if current_idea:
            ideas.append(current_idea)
        
        # 🔥 아이디어 검증
        if not ideas:
            raise HTTPException(
                status_code=500,
                detail="아이디어 생성에 실패했습니다. LLM 응답을 파싱할 수 없습니다."
            )
        
        # 각 아이디어의 필수 섹션 검증
        valid_ideas = []
        for idea in ideas:
            # 제목이 있고, description이 비어있지 않으면 유효
            if idea.get('title') and idea.get('description'):
                valid_ideas.append(idea)
            else:
                print(f"⚠️ 유효하지 않은 아이디어 발견: {idea.get('title', 'N/A')}")
        
        if not valid_ideas:
            raise HTTPException(
                status_code=500,
                detail="생성된 아이디어가 없습니다. 다시 시도해주세요."
            )
        
        ideas = valid_ideas
        
        # 🔥 description과 analysis 분리
        # "📊 분석 결과:" 또는 "📊 SWOT 분석:"으로 분리
        for idea in ideas:
            full_text = idea['description']
            
            # 분석 결과 부분 분리
            if '📊 분석 결과:' in full_text:
                parts = full_text.split('📊 분석 결과:')
                idea['description'] = parts[0].strip()
                idea['analysis'] = '📊 분석 결과:\n' + parts[1].strip()
            elif '📊 SWOT 분석:' in full_text:
                # 혹시 SWOT으로 나오면 분석 결과로 변환
                parts = full_text.split('📊 SWOT 분석:')
                idea['description'] = parts[0].strip()
                idea['analysis'] = '📊 분석 결과:\n' + parts[1].strip()
            else:
                # 분석이 없으면 빈 문자열
                idea['analysis'] = ''
        
        # 세션에 저장
        session_manager.update_session(session_id, {
            'generated_ideas': ideas
        })
        
        return IdeaResponse(ideas=ideas)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"아이디어 생성 실패: {str(e)}")


@router.delete("/session/{session_id}", response_model=DeleteResponse)
async def delete_session(session_id: str):
    """
    세션 삭제 (임시 데이터 모두 삭제)
    
    Args:
        session_id: 세션 ID
        
    Returns:
        DeleteResponse: 확인 메시지
    """
    try:
        # 세션 존재 여부 확인
        session = session_manager.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다.")
        
        # Ephemeral RAG 데이터 삭제 (JSON 폴더)
        ephemeral_rag = EphemeralRAG(session_id=session_id)
        ephemeral_rag.delete_session_data()
        
        # 세션 매니저에서 삭제
        session_manager.delete_session(session_id)
        
        return DeleteResponse(message="세션이 삭제되었습니다.")
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"세션 삭제 실패: {str(e)}")
