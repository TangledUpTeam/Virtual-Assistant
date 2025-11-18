"""
아이디어 생성 도구 (Idea Generator)

전체 플로우:
1. Q1: 목적/도메인 입력 ("어디에 쓸 아이디어가 필요하신가요?")
2. Q2: LLM 기반 워밍업 질문 생성 (2-3개) + "네" 입력 대기
3. Q3: 자유연상 입력 (20초 제한, 10개 미만 시 재입력)
4. 임시 RAG 처리:
   - Q3 임베딩 및 임시 ChromaDB 저장
   - Q1-Q3 유사도 기반 키워드 추출
   - 영구 RAG (SCAMPER, Mind Mapping, Starbursting)와 결합
   - LLM으로 아이디어 2-3개 생성
   - 각 아이디어별 SWOT 또는 How Now Wow 분석
5. 삭제 확인 ("삭제하시겠습니까?") - "네" 입력 시 모든 임시 데이터 삭제
"""

import readline  # 한글 입력 백스페이스 버그 수정
import time
import signal
import sys
from pathlib import Path
from typing import List, Dict, Optional
from openai import OpenAI
from dotenv import load_dotenv
import os

from session_manager import SessionManager
from ephemeral_rag import EphemeralRAG
from domain_hints import get_domain_hint, format_hint_for_prompt

# ChromaDB import
import chromadb
from chromadb.config import Settings as ChromaSettings


class TimeoutException(Exception):
    """시간 초과 예외"""
    pass


def timeout_handler(signum, frame):
    """시간 초과 핸들러"""
    raise TimeoutException()


class IdeaGenerator:
    """
    아이디어 생성 도구 메인 클래스
    
    Q1 → Q2 → Q3 → 아이디어 생성 → 분석 → 삭제의 전체 플로우를 관리합니다.
    """
    
    def __init__(self):
        """초기화"""
        load_dotenv()
        
        # OpenAI 클라이언트
        self.openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.llm_model = os.getenv("LLM_MODEL", "gpt-4o")
        self.embedding_model = os.getenv("EMBEDDING_MODEL", "text-embedding-3-large")
        
        # 세션 매니저
        self.session_manager = SessionManager()
        
        # 영구 RAG (SCAMPER, Mind Mapping, Starbursting) ChromaDB 초기화
        current_file = Path(__file__).resolve()
        module_dir = current_file.parent
        persist_directory = str(module_dir / "data" / "chroma")
        
        self.chroma_client = chromadb.PersistentClient(
            path=persist_directory,
            settings=ChromaSettings(anonymized_telemetry=False)
        )
        
        try:
            self.permanent_collection = self.chroma_client.get_collection(
                name="brainstorming_techniques"
            )
            print("✅ 영구 RAG 컬렉션 로드 완료")
        except Exception as e:
            print(f"⚠️  영구 RAG 컬렉션 로드 실패: {e}")
            print("   chroma_loader.py를 먼저 실행해주세요.")
            self.permanent_collection = None
        
        # 현재 세션 정보
        self.current_session_id = None
        self.ephemeral_rag = None
        
        print("✅ 아이디어 생성 도구 초기화 완료")
    
    def start_new_session(self) -> str:
        """
        새로운 세션 시작
        
        Returns:
            str: 세션 ID
        """
        self.current_session_id = self.session_manager.create_session()
        session = self.session_manager.get_session(self.current_session_id)
        
        # Ephemeral RAG 초기화 (ChromaDB 클라이언트 재사용)
        self.ephemeral_rag = EphemeralRAG(
            session_id=self.current_session_id,
            collection_name=session['chroma_collection'],
            chroma_client=self.chroma_client  # 기존 클라이언트 재사용
        )
        
        print(f"\n{'='*60}")
        print(f"🎨 새로운 아이디어 생성 세션 시작")
        print(f"   세션 ID: {self.current_session_id}")
        print(f"{'='*60}\n")
        
        return self.current_session_id
    
    def q1_ask_purpose(self) -> str:
        """
        Q1: 목적/도메인 입력
        
        Returns:
            str: 사용자가 입력한 목적
        """
        print("📋 Q1: 어디에 쓸 아이디어가 필요하신가요?")
        print("    (예: 모바일 앱, 마케팅 캠페인, 신제품 기획 등)")
        
        purpose = input("\n💭 입력: ").strip()
        
        # 세션에 저장
        self.session_manager.update_session(self.current_session_id, {
            'q1_purpose': purpose
        })
        
        print(f"\n✅ 목적이 설정되었습니다: {purpose}\n")
        return purpose
    
    def q2_generate_warmup(self, purpose: str) -> List[str]:
        """
        Q2: LLM 기반 워밍업 질문 생성
        
        Args:
            purpose: Q1에서 입력한 목적
            
        Returns:
            List[str]: 생성된 워밍업 질문 리스트 (2-3개)
        """
        print("🤔 Q2: 브레인스토밍 워밍업")
        print("    LLM이 워밍업 질문을 생성하고 있습니다...\n")
        
        prompt = f"""사용자가 "{purpose}"에 대한 아이디어를 생성하려고 합니다.

**목표**: 사용자의 직군/상황에 맞는 구체적인 워밍업 질문 2-3개 생성

1. 먼저 목적을 보고 직군을 추론하세요 (유튜버, 회사원, 소상공인, 개발자, 학생 등)
2. 해당 직군이 고민할 법한 구체적 질문을 만드세요

**직군별 질문 예시:**

유튜버:
- "썸네일에 들어갈 메인 비주얼은 어떤 장면인가요?"
- "영상 첫 3초에 시청자를 사로잡을 Hook은 무엇인가요?"

소상공인:
- "이 아이디어로 한 달에 몇 명의 신규 고객을 유치하고 싶나요?"
- "경쟁 가게와 비교했을 때 차별화 포인트는 무엇인가요?"

회사원:
- "이 프로젝트의 KPI는 무엇이고, 어떻게 측정하나요?"
- "상사에게 3분 안에 설명한다면 핵심 메시지는 무엇인가요?"

개발자/학생:
- "사용자가 앱을 열었을 때 첫 화면에 뭐가 보여야 하나요?"
- "이 기능을 구현하는 데 가장 어려운 부분은 무엇일까요?"

각 질문은 번호를 붙여 한 줄로 작성해주세요."""

        try:
            response = self.openai_client.chat.completions.create(
                model=self.llm_model,
                messages=[
                    {"role": "system", "content": "당신은 유능한 기획자입니다. 사용자의 직군에 맞는 구체적이고 실용적인 질문을 던집니다."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.8,
                max_tokens=400
            )
            
            warmup_text = response.choices[0].message.content.strip()
            
            # 질문 파싱 (번호 기반)
            warmup_questions = []
            for line in warmup_text.split('\n'):
                line = line.strip()
                if line and (line[0].isdigit() or line.startswith('-') or line.startswith('•')):
                    # 번호나 불릿 제거
                    cleaned = line.lstrip('0123456789.-•) ').strip()
                    if cleaned:
                        warmup_questions.append(cleaned)
            
            # 세션에 저장
            self.session_manager.update_session(self.current_session_id, {
                'q2_warmup': warmup_questions
            })
            
            # 질문 표시
            print("💡 워밍업 질문:\n")
            for i, question in enumerate(warmup_questions, 1):
                print(f"   {i}. {question}")
            
            return warmup_questions
            
        except Exception as e:
            print(f"❌ 워밍업 질문 생성 실패: {e}")
            return []
    
    def q2_wait_for_confirmation(self) -> bool:
        """
        Q2: "네" 입력 대기
        
        Returns:
            bool: 사용자가 "네"를 입력했는지 여부
        """
        # 입력 버퍼 정리 (워밍업 질문 생성 중 입력된 값 제거)
        import time as time_module
        time_module.sleep(0.1)
        try:
            import termios
            termios.tcflush(sys.stdin, termios.TCIFLUSH)
        except:
            pass
        
        print("\n")
        response = input("준비가 되셨다면 '네'를 입력해주세요: ").strip()
        
        if response == "네":
            print("✅ Q3로 넘어갑니다!\n")
            return True
        else:
            print("⚠️  '네'를 입력해야 다음 단계로 진행됩니다.")
            return False
    
    def q3_free_association(self, time_limit: int = 30, min_items: int = 10, max_items: int = 20) -> List[str]:
        """
        Q3: 자유연상 입력
        
        30초 동안 떠오르는 것을 자유롭게 입력받습니다.
        10개 미만이면 재입력을 요청합니다. 20개 도달 시 자동 종료됩니다.
        
        Args:
            time_limit: 시간 제한 (초)
            min_items: 최소 항목 개수
            max_items: 최대 항목 개수
            
        Returns:
            List[str]: 자유연상 단어/문구 리스트
        """
        print("🚀 Q3: 자유연상")
        print(f"    지금부터 {time_limit}초 동안 떠오르는 무엇이든 자유롭게 많이 적어주세요.")
        print(f"    각 항목은 엔터로 구분하세요. (최소 {min_items}개, 최대 {max_items}개)")
        print(f"\n⏱️  입력 시작!\n")
        
        associations = []
        start_time = time.time()
        
        try:
            # 시그널 설정 (Unix 계열 시스템에서만 작동)
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(time_limit)
            
            while len(associations) < max_items:
                try:
                    elapsed = int(time.time() - start_time)
                    remaining = time_limit - elapsed
                    
                    if remaining <= 0:
                        break
                    
                    item = input(f"[{remaining}초 남음, {len(associations)}/{max_items}개] 💭 ").strip()
                    if item:
                        associations.append(item)
                        # 최대 개수 도달 시 자동 종료
                        if len(associations) >= max_items:
                            print(f"\n✅ 최대 {max_items}개 입력 완료! 자동 종료됩니다.")
                            break
                        
                except TimeoutException:
                    print("\n⏰ 시간 종료!")
                    break
                except EOFError:
                    break
            
            # 알람 해제
            signal.alarm(0)
            
        except Exception as e:
            print(f"\n⚠️  입력 중 오류 발생: {e}")
            signal.alarm(0)  # 오류 발생 시에도 알람 해제
        
        # 입력 버퍼 정리 (더 확실하게)
        import time as time_module
        time_module.sleep(0.1)  # 잠시 대기
        try:
            import termios
            termios.tcflush(sys.stdin, termios.TCIFLUSH)
        except:
            pass
        
        print(f"\n✅ {len(associations)}개 항목 입력 완료!")
        
        # 최소 개수 체크
        if len(associations) < min_items:
            print(f"\n⚠️  최소 {min_items}개 이상 입력해주세요! (현재: {len(associations)}개)")
            print(f"    {min_items - len(associations)}개 더 필요합니다.\n")
            
            # 재입력
            remaining_needed = min_items - len(associations)
            remaining_allowed = max_items - len(associations)
            print(f"🔄 다시 {time_limit}초 동안 추가 입력해주세요! (최소 {remaining_needed}개 더, 최대 {remaining_allowed}개까지)\n")
            additional = self.q3_free_association_retry(time_limit, remaining_needed, remaining_allowed)
            associations.extend(additional)
        
        # 세션에 저장
        self.session_manager.update_session(self.current_session_id, {
            'q3_associations': associations
        })
        
        # Ephemeral RAG에 추가
        self.ephemeral_rag.add_associations(associations)
        
        print(f"\n✅ 총 {len(associations)}개 항목이 저장되었습니다.\n")
        return associations
    
    def q3_free_association_retry(self, time_limit: int, needed: int, max_allowed: int) -> List[str]:
        """
        Q3 재입력 (최소 개수 미달 시)
        
        Args:
            time_limit: 시간 제한 (초)
            needed: 필요한 최소 추가 항목 개수
            max_allowed: 최대 허용 추가 항목 개수
            
        Returns:
            List[str]: 추가 자유연상 리스트
        """
        associations = []
        start_time = time.time()
        
        try:
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(time_limit)
            
            while len(associations) < max_allowed:
                try:
                    elapsed = int(time.time() - start_time)
                    remaining = time_limit - elapsed
                    
                    if remaining <= 0:
                        break
                    
                    # 최소값 도달 여부에 따라 메시지 변경
                    if len(associations) < needed:
                        status = f"{needed - len(associations)}개 더 필요"
                    else:
                        status = f"충분함, 최대 {max_allowed - len(associations)}개 더 가능"
                    
                    item = input(f"[{remaining}초 남음, {status}] 💭 ").strip()
                    if item:
                        associations.append(item)
                        # 최대 개수 도달 시 자동 종료
                        if len(associations) >= max_allowed:
                            print(f"\n✅ 최대 개수 도달! 자동 종료됩니다.")
                            break
                        
                except TimeoutException:
                    print("\n⏰ 시간 종료!")
                    break
                except EOFError:
                    break
            
            signal.alarm(0)
            
        except Exception as e:
            print(f"\n⚠️  입력 중 오류 발생: {e}")
            signal.alarm(0)
        
        # 입력 버퍼 정리 (더 확실하게)
        import time as time_module
        time_module.sleep(0.1)  # 잠시 대기
        try:
            import termios
            termios.tcflush(sys.stdin, termios.TCIFLUSH)
        except:
            pass
        
        return associations
    
    def _search_permanent_rag(self, query: str, n_results: int = 5) -> List[Dict]:
        """
        영구 RAG에서 브레인스토밍 기법 검색
        
        Args:
            query: 검색 쿼리
            n_results: 반환할 결과 개수
            
        Returns:
            List[Dict]: 검색 결과 리스트
        """
        if not self.permanent_collection:
            return []
        
        try:
            # 쿼리 임베딩
            query_embedding = self.ephemeral_rag.embed_text(query)
            
            # ChromaDB 검색
            results = self.permanent_collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results
            )
            
            # 결과 파싱
            techniques = []
            if results['documents'] and len(results['documents'][0]) > 0:
                for i in range(len(results['documents'][0])):
                    techniques.append({
                        'title': results['metadatas'][0][i].get('title', 'N/A'),
                        'content': results['documents'][0][i],
                        'chunk_id': results['metadatas'][0][i].get('chunk_id', 'N/A'),
                        'similarity': 1 - results['distances'][0][i] if results['distances'] else 0
                    })
            
            return techniques
            
        except Exception as e:
            print(f"⚠️  영구 RAG 검색 실패: {e}")
            return []
    
    def generate_ideas(self, purpose: str, keywords: List[Dict], top_k_techniques: int = 3) -> List[Dict]:
        """
        아이디어 생성
        
        Q1 목적, Q3 키워드, 영구 RAG (SCAMPER 등)를 결합하여 아이디어를 생성합니다.
        
        Args:
            purpose: Q1 목적
            keywords: Q3에서 추출한 키워드 리스트
            top_k_techniques: 사용할 상위 기법 개수
            
        Returns:
            List[Dict]: 생성된 아이디어 리스트
        """
        print("🎨 아이디어 생성 중...\n")
        
        # 1. 영구 RAG에서 관련 기법 검색 (SCAMPER, Mind Mapping, Starbursting)
        techniques_results = self._search_permanent_rag(
            query=purpose,
            n_results=top_k_techniques
        )
        
        # 2. 키워드 문자열 생성
        keyword_str = ", ".join([kw['keyword'] for kw in keywords[:7]])
        
        # 3. 기법 내용 문자열 생성
        techniques_str = "\n\n".join([
            f"[기법 {i+1}] {t['title']}\n{t['content'][:500]}..."
            for i, t in enumerate(techniques_results)
        ])
        
        # 4. 직군별 힌트 가져오기 (Add-on 모듈, 일회성)
        domain_hint = get_domain_hint(purpose)
        formatted_hint = format_hint_for_prompt(domain_hint)
        
        # 5. LLM 프롬프트 생성
        prompt = f"""사용자가 "{purpose}"에 대한 아이디어를 원합니다.

【자유연상 키워드】
{keyword_str}

【적용 가능한 브레인스토밍 기법】
{techniques_str}
{formatted_hint}
---

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

위 규칙을 엄격히 지키며 2-3개의 **빠르게 실행 가능한** 아이디어를 생성하세요:

---
아이디어 제목: [간단한 제목]
설명: [구체적 행동 위주. 허구 통계/비용 절대 금지. 빠르게 실행 가능한 것만]
적용된 기법: [브레인스토밍 기법명]
---"""

        try:
            response = self.openai_client.chat.completions.create(
                model=self.llm_model,
                messages=[
                    {"role": "system", "content": "당신은 현실적인 기획자입니다. 허구의 통계나 비용을 절대 지어내지 않으며, 사용자가 가진 자원과 역량으로 빠르게 시작 가능한 아이디어를 제안합니다. 거창한 전략이 아닌, 구체적으로 실행 가능한 행동 위주로 설명합니다."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=2000
            )
            
            ideas_text = response.choices[0].message.content.strip()
            
            # 아이디어 파싱
            ideas = self._parse_ideas(ideas_text)
            
            # 세션에 저장
            self.session_manager.update_session(self.current_session_id, {
                'ideas': ideas
            })
            
            # 아이디어 출력
            print(f"✅ {len(ideas)}개의 아이디어가 생성되었습니다!\n")
            for i, idea in enumerate(ideas, 1):
                print(f"{'='*60}")
                print(f"💡 아이디어 {i}: {idea.get('title', '제목 없음')}")
                print(f"{'='*60}")
                print(f"{idea.get('description', '설명 없음')}")
                print(f"\n🔧 적용 기법: {idea.get('technique', '기법 없음')}\n")
            
            return ideas
            
        except Exception as e:
            print(f"❌ 아이디어 생성 실패: {e}")
            return []
    
    def _parse_ideas(self, ideas_text: str) -> List[Dict]:
        """
        LLM 응답에서 아이디어 파싱
        
        Args:
            ideas_text: LLM이 생성한 아이디어 텍스트
            
        Returns:
            List[Dict]: 파싱된 아이디어 리스트
        """
        ideas = []
        current_idea = {}
        
        for line in ideas_text.split('\n'):
            line = line.strip()
            
            if line.startswith('---'):
                if current_idea:
                    ideas.append(current_idea)
                    current_idea = {}
            elif line.startswith('아이디어 제목:') or line.startswith('제목:'):
                current_idea['title'] = line.split(':', 1)[1].strip()
            elif line.startswith('설명:'):
                current_idea['description'] = line.split(':', 1)[1].strip()
            elif line.startswith('적용된 기법:') or line.startswith('기법:'):
                current_idea['technique'] = line.split(':', 1)[1].strip()
            elif current_idea and 'description' in current_idea and line:
                # 설명 이어붙이기
                current_idea['description'] += ' ' + line
        
        # 마지막 아이디어 추가
        if current_idea:
            ideas.append(current_idea)
        
        return ideas
    
    def analyze_ideas(self, ideas: List[Dict]) -> List[Dict]:
        """
        아이디어 분석 (SWOT 또는 How Now Wow)
        
        각 아이디어에 대해 적절한 분석 기법을 선택하여 분석합니다.
        
        Args:
            ideas: 생성된 아이디어 리스트
            
        Returns:
            List[Dict]: 분석이 추가된 아이디어 리스트
        """
        print("\n📊 아이디어 분석 중...\n")
        
        for i, idea in enumerate(ideas, 1):
            print(f"{'='*60}")
            print(f"📈 아이디어 {i} 분석: {idea.get('title', '제목 없음')}")
            print(f"{'='*60}\n")
            
            # 분석 기법 선택 (여기서는 SWOT를 기본으로 사용)
            analysis = self._perform_swot_analysis(idea)
            idea['analysis'] = analysis
            idea['analysis_type'] = 'SWOT'
            
            # 분석 결과 출력
            print(f"강점 (Strengths):\n{analysis.get('strengths', 'N/A')}\n")
            print(f"약점 (Weaknesses):\n{analysis.get('weaknesses', 'N/A')}\n")
            print(f"기회 (Opportunities):\n{analysis.get('opportunities', 'N/A')}\n")
            print(f"위협 (Threats):\n{analysis.get('threats', 'N/A')}\n")
        
        # 세션 업데이트
        self.session_manager.update_session(self.current_session_id, {
            'ideas': ideas
        })
        
        print(f"{'='*60}\n")
        print("✅ 모든 아이디어 분석 완료!\n")
        
        return ideas
    
    def _perform_swot_analysis(self, idea: Dict) -> Dict:
        """
        SWOT 분석 수행
        
        Args:
            idea: 분석할 아이디어
            
        Returns:
            Dict: SWOT 분석 결과
        """
        prompt = f"""다음 아이디어에 대해 SWOT 분석을 수행해주세요:

아이디어 제목: {idea.get('title', '제목 없음')}
설명: {idea.get('description', '설명 없음')}

**🚨 작성 규칙**

1. **허구 데이터 금지**: 통계, 비용, 경쟁사를 지어내지 마세요
2. **짧고 핵심만**: 각 항목당 1-2줄로 간결하게
3. **구체적으로**: "시장 경쟁력" 같은 추상어 대신 "비슷한 앱이 없음" 처럼 구체적으로

**필수 형식** (반드시 4가지 모두 작성):

강점 (Strengths):
- [핵심 장점 1줄]
- [핵심 장점 1줄]

약점 (Weaknesses):
- [솔직한 단점 1줄]
- [솔직한 단점 1줄]

기회 (Opportunities):
- [현실적 기회 1줄]
- [현실적 기회 1줄]

위협 (Threats):
- [구체적 위협 1줄]
- [구체적 위협 1줄]

**예시**:
강점: SNS 홍보는 무료로 시작 가능. 학원 강사가 직접 진행하니 비용 추가 없음.
약점: 영상 편집 처음이면 배우는데 시간 걸림. 참가자 모집 안 될 수도 있음.
기회: 요즘 쇼츠 영상이 인기. 국비지원 찾는 사람 많음.
위협: 다른 학원도 비슷한 이벤트 많이 함. 플랫폼 알고리즘 바뀌면 노출 줄어들 수 있음."""

        try:
            response = self.openai_client.chat.completions.create(
                model=self.llm_model,
                messages=[
                    {"role": "system", "content": "당신은 현실적인 기획자입니다. SWOT 분석은 짧고 간결하게, 각 항목당 1-2줄로 핵심만 작성합니다. 강점/약점/기회/위협 4가지를 반드시 모두 작성해야 합니다."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.6,
                max_tokens=500
            )
            
            analysis_text = response.choices[0].message.content.strip()
            
            # SWOT 파싱 (개선)
            swot = {
                'strengths': '',
                'weaknesses': '',
                'opportunities': '',
                'threats': ''
            }
            
            current_section = None
            for line in analysis_text.split('\n'):
                line = line.strip()
                
                # 섹션 헤더 감지 (개선된 로직)
                if '강점' in line or 'Strengths' in line.lower():
                    current_section = 'strengths'
                    # 헤더에 바로 내용이 있는 경우 (예: "강점: 무료로 시작 가능")
                    if ':' in line:
                        content = line.split(':', 1)[1].strip()
                        if content:
                            swot['strengths'] = content
                elif '약점' in line or 'Weaknesses' in line.lower():
                    current_section = 'weaknesses'
                    if ':' in line:
                        content = line.split(':', 1)[1].strip()
                        if content:
                            swot['weaknesses'] = content
                elif '기회' in line or 'Opportunities' in line.lower():
                    current_section = 'opportunities'
                    if ':' in line:
                        content = line.split(':', 1)[1].strip()
                        if content:
                            swot['opportunities'] = content
                elif '위협' in line or 'Threats' in line.lower():
                    current_section = 'threats'
                    if ':' in line:
                        content = line.split(':', 1)[1].strip()
                        if content:
                            swot['threats'] = content
                # 일반 라인 (불릿 포인트 등)
                elif current_section and line and line not in ['', '-', '•', '*']:
                    # 불릿 제거
                    cleaned_line = line.lstrip('-•*').strip()
                    if cleaned_line:
                        if swot[current_section]:
                            swot[current_section] += ' ' + cleaned_line
                        else:
                            swot[current_section] = cleaned_line
            
            # 빈 항목 기본값 설정
            if not swot['strengths']:
                swot['strengths'] = '(분석 데이터 없음)'
            if not swot['weaknesses']:
                swot['weaknesses'] = '(분석 데이터 없음)'
            if not swot['opportunities']:
                swot['opportunities'] = '(분석 데이터 없음)'
            if not swot['threats']:
                swot['threats'] = '(분석 데이터 없음)'
            
            return swot
            
        except Exception as e:
            print(f"⚠️  SWOT 분석 실패: {e}")
            return {
                'strengths': 'N/A',
                'weaknesses': 'N/A',
                'opportunities': 'N/A',
                'threats': 'N/A'
            }
    
    def confirm_deletion(self) -> bool:
        """
        삭제 확인
        
        Returns:
            bool: 삭제 여부
        """
        # 입력 버퍼 정리 (이전 입력이 남아있을 수 있음)
        import time as time_module
        time_module.sleep(0.2)  # 충분히 대기
        try:
            import termios
            termios.tcflush(sys.stdin, termios.TCIFLUSH)
        except:
            pass
        
        print("\n" + "="*60)
        print("🗑️  데이터 삭제")
        print("="*60)
        print("\n이번 세션의 모든 데이터를 삭제하시겠습니까?")
        print("(Q1 목적, Q2 워밍업, Q3 연상, 생성된 아이디어, 임시 벡터 DB)\n")
        
        response = input("삭제하려면 '네'를 입력해주세요: ").strip()
        
        return response == "네"
    
    def delete_session_data(self):
        """
        세션 데이터 삭제
        
        임시 ChromaDB 컬렉션, 세션 디렉토리, 메모리 데이터를 모두 삭제합니다.
        """
        if not self.current_session_id:
            print("⚠️  삭제할 세션이 없습니다.")
            return
        
        print("\n🗑️  데이터 삭제 중...")
        
        # 1. Ephemeral ChromaDB 컬렉션 삭제
        if self.ephemeral_rag:
            self.ephemeral_rag.delete_collection()
        
        # 2. 세션 삭제 (디렉토리 + 메모리)
        self.session_manager.delete_session(self.current_session_id)
        
        print("✅ 모든 데이터가 삭제되었습니다.")
        print("   아이디어 오염 및 유출이 방지되었습니다.\n")
        
        # 초기화
        self.current_session_id = None
        self.ephemeral_rag = None
    
    def run(self):
        """
        전체 플로우 실행
        
        Q1 → Q2 → Q3 → 아이디어 생성 → 분석 → 삭제 확인
        """
        try:
            # 세션 시작
            self.start_new_session()
            
            # Q1: 목적 입력
            purpose = self.q1_ask_purpose()
            
            # Q2: 워밍업 질문 생성 + "네" 대기
            warmup_questions = self.q2_generate_warmup(purpose)
            
            while not self.q2_wait_for_confirmation():
                pass  # "네" 입력할 때까지 대기
            
            # Q3: 자유연상 입력 (1페이즈 30초, 최소 10개, 최대 20개)
            associations = self.q3_free_association(time_limit=30, min_items=10, max_items=20)
            
            # Q1-Q3 유사도 기반 키워드 추출
            print("\n🔍 Q1과 Q3 간 유사도 기반 키워드 추출 중...\n")
            keywords = self.ephemeral_rag.extract_keywords_by_similarity(purpose, top_k=7)
            
            # 아이디어 생성
            ideas = self.generate_ideas(purpose, keywords, top_k_techniques=3)
            
            if not ideas:
                print("⚠️  아이디어 생성에 실패했습니다.")
                return
            
            # 아이디어 분석
            ideas = self.analyze_ideas(ideas)
            
            # 삭제 확인
            if self.confirm_deletion():
                self.delete_session_data()
            else:
                print("\n✅ 데이터가 유지됩니다.")
                print(f"   세션 ID: {self.current_session_id}")
                print("   나중에 /delete 명령으로 삭제할 수 있습니다.\n")
            
            print("\n" + "="*60)
            print("🎉 아이디어 생성 완료!")
            print("="*60)
            
        except KeyboardInterrupt:
            print("\n\n⚠️  사용자가 중단했습니다.")
            
            # 중단 시에도 삭제 확인
            if self.confirm_deletion():
                self.delete_session_data()
        
        except Exception as e:
            print(f"\n❌ 오류 발생: {e}")
            import traceback
            traceback.print_exc()


# 메인 실행
if __name__ == "__main__":
    generator = IdeaGenerator()
    generator.run()

