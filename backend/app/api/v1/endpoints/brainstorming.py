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
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Optional
import sys
from pathlib import Path

# 브레인스토밍 모듈 경로 추가
brainstorming_path = Path(__file__).resolve().parent.parent.parent.parent / "domain" / "brainstorming"
sys.path.insert(0, str(brainstorming_path))

from session_manager import SessionManager
from ephemeral_rag import EphemeralRAG
from domain_hints import get_domain_hint, format_hint_for_prompt

# ChromaDB import
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

# 영구 RAG ChromaDB 클라이언트
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
    
    Returns:
        SessionResponse: 세션 ID와 메시지
    """
    try:
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
    Q3: 자유연상 입력
    
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
        
        # Ephemeral RAG 초기화 (처음 한 번만)
        if 'ephemeral_rag_initialized' not in session:
            ephemeral_rag = EphemeralRAG(
                session_id=session_id,
                collection_name=session['chroma_collection'],
                chroma_client=chroma_client
            )
            session_manager.update_session(session_id, {
                'ephemeral_rag_initialized': True
            })
        else:
            ephemeral_rag = EphemeralRAG(
                session_id=session_id,
                collection_name=session['chroma_collection'],
                chroma_client=chroma_client
            )
        
        # 임베딩 및 ChromaDB 저장
        ephemeral_rag.add_associations(request.associations)
        
        # 세션에 저장
        session_manager.update_session(session_id, {
            'q3_associations': request.associations
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
        
        # Ephemeral RAG 초기화
        ephemeral_rag = EphemeralRAG(
            session_id=session_id,
            collection_name=session['chroma_collection'],
            chroma_client=chroma_client
        )
        
        # Q3 연상 키워드 추출 (유사도 기반)
        # 🔥 메서드 이름 수정: extract_keywords → extract_keywords_by_similarity
        # 🔥 인자 수정: purpose_embedding → purpose (텍스트)
        keywords_data = ephemeral_rag.extract_keywords_by_similarity(
            purpose=purpose,
            top_k=5
        )
        
        # 키워드만 추출 (keyword 필드에서)
        extracted_keywords = [kw['keyword'] for kw in keywords_data]
        
        # 영구 RAG에서 브레인스토밍 기법 검색
        rag_context = ""
        if permanent_collection:
            purpose_embedding_2 = openai_client.embeddings.create(
                input=purpose,
                model=embedding_model
            ).data[0].embedding
            
            results = permanent_collection.query(
                query_embeddings=[purpose_embedding_2],
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
        prompt = f"""**역할**: 당신은 유능한 기획자입니다.

**목적**: "{purpose}"

**사용자의 연상 키워드**: {', '.join(extracted_keywords)}

**브레인스토밍 기법 (참고자료)**:

다음은 검증된 전문가 브레인스토밍 기법입니다.
아이디어 발상 시 이 기법들을 **적극 활용**하되, 자연스럽게 녹여내세요.

{rag_context}

💡 **활용 팁**: 
- 각 아이디어마다 서로 다른 기법을 시도해보세요
- 기법을 변형하거나 조합해도 좋습니다
- 기법보다 **문제 해결**이 우선이지만, 기법이 더 나은 아이디어를 만들어냅니다

---

{hint_text}

**요구사항**:
1. **직군 추론**: 목적을 보고 사용자의 직군(유튜버, 소상공인, 직장인, 학생, 개발자, 회사원 등)을 파악하세요.

2. **아이디어 2-3개 생성** (2단계 프로세스):
   
   📍 **STEP 1: 창의적 발상 (브레인스토밍 기법 활용)**
   - **위의 브레인스토밍 기법들을 적극 활용하여** 다양한 관점에서 아이디어를 발상하세요
   - 창의적 사고 기법 예시:
     * SCAMPER: 대체/결합/응용/확대/축소/용도 변경/제거
     * Mind Mapping: 중심 아이디어에서 가지 뻗어나가기
     * 역발상: 반대로 생각해보기
     * 연관 단어: 키워드에서 연상되는 것들 조합
   - 여러 방향으로 생각을 확장하고, 다양한 조합을 시도하세요
   - **창의적 사고 과정을 거쳤다면, 결과가 기존에 있는 것이어도 괜찮습니다**
   
   📍 **STEP 2: 실행 가능성 설계** (아이디어가 정해진 후)
   - 위에서 나온 아이디어 각각에 대해:
   - **구체적인 실행 단계**를 차근차근 제시하세요
   - 첫 단계부터 어떻게 시작할지 명확히 설명하세요
   - 필요한 리소스(시간, 비용, 도구)와 예상 기간을 명시하세요
   - 단계적 접근: 작게 시작 → 점진적 확장
   
   ⚠️ **작성 원칙**:
   - 추상적인 표현 금지 (예: "전략 수립", "시스템 구축" 등)
   - 구체적인 행동과 예시 중심 (예: "GPS 기반 주변 맛집 추천", "네이버 API로 쿠폰 노출")

3. **직군별 맞춤**:
   - 유튜버 → 휴대폰 하나로 촬영 가능한 영상 구조
   - 소상공인 → 네이버/인스타로 당장 시작 가능한 홍보
   - 개발자 → 무료 API + 간단한 코드로 빠른 프로토타입
   - 학생 → 발표 자료, 구글 문서, PPT로 바로 작성
   - 회사원 → 팀 리소스 활용 가능한 실행 계획

4. **보고서 스타일 금지, 행동 중심 작성**

5. **창의적 사고 과정 중시, 실행 단계는 상세하게**:
   
   💡 **아이디어 발상 단계 (STEP 1) - 창의적 기법 활용**:
   - 브레인스토밍 기법을 활용해 **다양한 방향으로** 생각하세요:
     * SCAMPER 예시: "인스타 이벤트" → "라이브 + 퀴즈 결합" (Combine)
     * Mind Map 예시: "디저트" → "계절/색상/감정/스토리" 가지 확장
     * 역발상 예시: "손님이 오게 하기" → "손님이 만들게 하기" (DIY 키트)
   - **창의적 사고 과정이 중요**하며, 결과가 기존 아이디어와 유사해도 괜찮습니다
   - 중요한 것은 "어떤 기법으로 어떻게 생각했는가"입니다
   
   📋 **실행 설계 단계 (STEP 2) - 구체성 극대화**:
   - 위에서 나온 아이디어에 대해 **매우 구체적으로** 설명:
     * ✅ "1주차: 인스타 계정 개설 + 3개 샘플 사진 촬영"
     * ✅ "2주차: 매주 목요일 8시 라이브 일정 공지 + 첫 라이브"
     * ✅ "예상 비용: 월 10만원 (광고비), 준비 기간: 2주"
     * ❌ "마케팅 전략 수립" (너무 추상적)
   
   ❌ **절대 금지**: 
   - 허위 데이터(통계, 시장 규모, 비용, 규제, 경쟁사 실적 등) 언급 금지
   - 모르면 "조사 필요"라고 명시
   
   ✅ **실행 가능성 기준 (유연하게)**:
   - 실행 기간: 단기/장기 모두 가능
   - 투자 규모: 작게 시작 후 단계적 확장 가능
   - **창의적으로 생각한 아이디어라면, 첫 단계만 현실적이면 OK**

**출력 형식**:
아이디어 1: [제목]
- 설명: [구체적인 실행 방법]

아이디어 2: [제목]
- 설명: [구체적인 실행 방법]

아이디어 3: [제목] (선택)
- 설명: [구체적인 실행 방법]
"""
        
        idea_response = openai_client.chat.completions.create(
            model=llm_model,
            messages=[
                {"role": "system", "content": "당신은 창의적이고 실용적인 아이디어를 제안하는 브레인스토밍 전문가입니다."},
                {"role": "user", "content": prompt}
            ],
            temperature=1.0,
            max_tokens=1500
        )
        
        ideas_text = idea_response.choices[0].message.content.strip()
        
        # 아이디어 파싱
        ideas = []
        current_idea = None
        
        for line in ideas_text.split('\n'):
            line = line.strip()
            if not line:
                continue
            
            if line.startswith('아이디어'):
                if current_idea:
                    ideas.append(current_idea)
                
                # 제목 추출
                title = line.split(':', 1)[1].strip() if ':' in line else line
                current_idea = {
                    'title': title,
                    'description': '',
                    'analysis': ''
                }
            elif current_idea and line.startswith('-'):
                # 설명 추출
                content = line.lstrip('-').strip()
                if content.startswith('설명:'):
                    content = content[3:].strip()
                current_idea['description'] += content + '\n'
        
        if current_idea:
            ideas.append(current_idea)
        
        # 각 아이디어에 SWOT 분석 추가
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
            
            swot_response = openai_client.chat.completions.create(
                model=llm_model,
                messages=[
                    {"role": "system", "content": "당신은 현실적인 기획자입니다."},
                    {"role": "user", "content": swot_prompt}
                ],
                temperature=0.6,
                max_tokens=500
            )
            
            idea['analysis'] = swot_response.choices[0].message.content.strip()
        
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
        
        # Ephemeral RAG 데이터 삭제
        ephemeral_rag = EphemeralRAG(
            session_id=session_id,
            collection_name=session['chroma_collection'],
            chroma_client=chroma_client
        )
        ephemeral_rag.delete_collection()
        
        # 세션 디렉토리 삭제
        import shutil
        ephemeral_dir = Path(session['ephemeral_dir'])
        if ephemeral_dir.exists():
            shutil.rmtree(ephemeral_dir)
        
        # 세션 매니저에서 삭제
        session_manager.delete_session(session_id)
        
        return DeleteResponse(message="세션이 삭제되었습니다.")
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"세션 삭제 실패: {str(e)}")

