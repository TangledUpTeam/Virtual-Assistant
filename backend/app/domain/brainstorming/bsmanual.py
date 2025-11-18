"""
브레인스토밍 매뉴얼 (RAG 테스트용)

RAG 시스템이 브레인스토밍 기법 데이터를 잘 검색하고 활용하는지 테스트하는 파일입니다.
나중에 이 RAG를 기반으로 아이디어 산출기를 구현할 예정입니다.
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from datetime import datetime

# 한글 입력 버그 수정을 위한 readline import
try:
    import readline
except ImportError:
    pass  # Windows에서는 readline이 없을 수 있음

# .env 파일 로드
env_path = Path(__file__).parent.parent.parent.parent / '.env'
load_dotenv(env_path)

# 환경변수 체크
if not os.getenv('OPENAI_API_KEY'):
    print("❌ OPENAI_API_KEY가 설정되지 않았습니다!")
    sys.exit(1)

# 서비스 임포트
import chromadb
from chromadb.config import Settings
from openai import OpenAI
from typing import List, Dict, Optional


class BrainstormingManual:
    """브레인스토밍 매뉴얼 (RAG 테스트)"""
    
    def __init__(self):
        # OpenAI 클라이언트
        self.openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        self.embedding_model = os.getenv('EMBEDDING_MODEL', 'text-embedding-3-large')
        self.llm_model = os.getenv('LLM_MODEL', 'gpt-4o')
        
        # ChromaDB 설정
        base_dir = Path(__file__).parent
        data_dir = base_dir / "data"
        self.persist_directory = str(data_dir / "chroma")
        
        # ChromaDB 클라이언트
        self.chroma_client = chromadb.PersistentClient(
            path=self.persist_directory,
            settings=Settings(anonymized_telemetry=False)
        )
        
        # 컬렉션
        self.collection_name = "brainstorming_techniques"
        self.collection = self.chroma_client.get_collection(name=self.collection_name)
        
        # 대화 히스토리
        self.conversation_history = []
        
    def _embed_query(self, query: str) -> List[float]:
        """질문을 임베딩"""
        response = self.openai_client.embeddings.create(
            model=self.embedding_model,
            input=query,
            encoding_format="float"
        )
        return response.data[0].embedding
    
    def search_techniques(self, query: str, n_results: int = 3) -> List[Dict]:
        """브레인스토밍 기법 검색"""
        query_embedding = self._embed_query(query)
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results
        )
        
        formatted_results = []
        for idx in range(len(results['ids'][0])):
            distance = results['distances'][0][idx]
            similarity = 1 - distance
            
            metadata = results['metadatas'][0][idx]
            document = results['documents'][0][idx]
            
            formatted_results.append({
                "chunk_id": metadata['chunk_id'],
                "title": metadata['title'],
                "content": document,
                "similarity": round(similarity, 4)
            })
        
        return formatted_results
    
    def chat(self, user_message: str) -> str:
        """
        사용자 메시지를 받아 응답 생성
        
        Args:
            user_message: 사용자의 질문/메시지
            
        Returns:
            챗봇의 응답
        """
        # 1. 관련 브레인스토밍 기법 검색
        relevant_techniques = self.search_techniques(user_message, n_results=3)
        
        # 2. 컨텍스트 구성
        if relevant_techniques:
            context = "\n\n".join([
                f"[{tech['title']}]\n{tech['content'][:300]}..."
                for tech in relevant_techniques
            ])
        else:
            context = "관련된 브레인스토밍 기법을 찾을 수 없습니다."
        
        # 3. 대화 히스토리에 추가
        self.conversation_history.append({
            "role": "user",
            "content": user_message
        })
        
        # 4. GPT에게 질문 (대화 히스토리 포함)
        system_prompt = f"""당신은 브레인스토밍 전문가 AI 어시스턴트입니다.

사용자의 질문에 대해 다음 브레인스토밍 기법 자료를 참고하여 답변하세요:

{context}

답변 가이드:
- 친근하고 대화하듯이 답변하세요
- 사용자의 상황에 맞는 구체적인 조언을 제공하세요
- 필요시 실행 방법과 주의사항을 알려주세요
- 참고한 기법의 이름을 자연스럽게 언급하세요
- 간결하지만 유용한 정보를 제공하세요"""

        messages = [{"role": "system", "content": system_prompt}]
        
        # 최근 5개 대화만 포함 (컨텍스트 길이 제한)
        messages.extend(self.conversation_history[-5:])
        
        response = self.openai_client.chat.completions.create(
            model=self.llm_model,
            messages=messages,
            temperature=0.7,
            max_tokens=800
        )
        
        assistant_message = response.choices[0].message.content
        
        # 5. 응답을 히스토리에 추가
        self.conversation_history.append({
            "role": "assistant",
            "content": assistant_message
        })
        
        return assistant_message
    
    def get_conversation_stats(self):
        """대화 통계"""
        return {
            "total_messages": len(self.conversation_history),
            "user_messages": len([m for m in self.conversation_history if m['role'] == 'user']),
            "assistant_messages": len([m for m in self.conversation_history if m['role'] == 'assistant'])
        }


def print_separator(char="─", length=60):
    """구분선"""
    print(char * length)


def print_message(role: str, content: str):
    """메시지 출력"""
    if role == "user":
        print(f"\n👤 You: {content}")
    else:
        print(f"\n🤖 Assistant:")
        print(content)
    print_separator()


def main():
    """메인 함수"""
    print("""
╔═══════════════════════════════════════════════════════╗
║   📚 브레인스토밍 매뉴얼 (RAG 테스트)                 ║
╚═══════════════════════════════════════════════════════╝

브레인스토밍 기법 RAG 시스템을 테스트합니다. 💡

💬 자유롭게 질문해주세요:
   - "팀 협업에 좋은 방법이 뭐가 있을까?"
   - "빠르게 아이디어를 내고 싶어"
   - "SWOT 분석이 뭐야?"

📝 명령어:
   /help    - 도움말
   /stats   - 대화 통계
   /clear   - 대화 초기화
   /quit    - 종료
""")
    
    # RAG 시스템 초기화
    try:
        print("⏳ RAG 시스템 초기화 중...")
        manual = BrainstormingManual()
        print(f"✅ 준비 완료! ({manual.collection.count()}개 기법 로드됨)\n")
        print_separator()
    except Exception as e:
        print(f"❌ 초기화 실패: {e}")
        print("\n💡 해결 방법:")
        print("   python chroma_loader.py 를 먼저 실행하세요")
        sys.exit(1)
    
    # 대화 루프
    while True:
        try:
            # 사용자 입력 (한글 입력 시 백스페이스 문제 해결)
            try:
                user_input = input("\n💬 You: ").strip()
            except EOFError:
                print("\n\n👋 대화를 종료합니다.")
                break
            
            if not user_input:
                continue
            
            # 명령어 처리
            if user_input.startswith('/'):
                cmd = user_input.lower()
                
                if cmd == '/quit':
                    print("\n👋 대화를 종료합니다. 좋은 하루 되세요!")
                    break
                
                elif cmd == '/help':
                    print("""
📚 사용 가이드:

1️⃣ 자유로운 질문
   - "팀 회의에서 쓸 수 있는 기법은?"
   - "혼자 아이디어 정리하는 방법"
   - "문제 해결 브레인스토밍"

2️⃣ 구체적인 상황 설명
   - "5명 팀으로 신제품 회의를 1시간 해야해요"
   - "온라인으로 브레인스토밍하려는데 추천해줘"

3️⃣ 특정 기법 질문
   - "마인드맵이 뭐야?"
   - "SWOT 분석 방법 알려줘"

💡 자연스럽게 대화하듯이 물어보세요!
""")
                    continue
                
                elif cmd == '/stats':
                    stats = manual.get_conversation_stats()
                    print(f"""
📊 대화 통계:
   - 총 메시지: {stats['total_messages']}개
   - 내 질문: {stats['user_messages']}개
   - AI 응답: {stats['assistant_messages']}개
""")
                    continue
                
                elif cmd == '/clear':
                    manual.conversation_history = []
                    print("✅ 대화 히스토리가 초기화되었습니다.")
                    continue
                
                else:
                    print("❌ 알 수 없는 명령어입니다. /help를 입력해보세요.")
                    continue
            
            # 일반 메시지 처리
            print_separator()
            print("🤖 RAG 검색 중...")
            
            # AI 응답 생성
            response = manual.chat(user_input)
            
            # 응답 출력
            print(f"\n🤖 Assistant:\n{response}")
            print_separator()
            
        except KeyboardInterrupt:
            print("\n\n👋 대화를 종료합니다.")
            break
        except Exception as e:
            print(f"\n❌ 오류: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    main()

