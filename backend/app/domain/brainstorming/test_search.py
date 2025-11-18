"""
브레인스토밍 RAG 검색 테스트 스크립트

콘솔에서 대화형으로 검색을 테스트할 수 있습니다.
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# .env 파일 로드
env_path = Path(__file__).parent.parent.parent.parent / '.env'
load_dotenv(env_path)

# 환경변수 체크
if not os.getenv('OPENAI_API_KEY'):
    print("❌ OPENAI_API_KEY가 설정되지 않았습니다!")
    sys.exit(1)

# 독립 실행을 위한 서비스 임포트
import chromadb
from chromadb.config import Settings
from openai import OpenAI
from typing import List, Dict, Optional


class BrainstormingService:
    """브레인스토밍 RAG 검색 서비스 (테스트용 독립 버전)"""
    
    def __init__(self):
        # OpenAI 클라이언트 초기화
        self.openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        self.embedding_model = os.getenv('EMBEDDING_MODEL', 'text-embedding-3-large')
        self.llm_model = os.getenv('LLM_MODEL', 'gpt-4o')
        self.llm_temperature = float(os.getenv('LLM_TEMPERATURE', '0.7'))
        self.llm_max_tokens = int(os.getenv('LLM_MAX_TOKENS', '2000'))
        
        # ChromaDB 경로 설정 - 브레인스토밍 모듈 전용
        base_dir = Path(__file__).parent
        data_dir = base_dir / "data"
        self.persist_directory = str(data_dir / "chroma")
        
        # ChromaDB 클라이언트 초기화
        self.chroma_client = chromadb.PersistentClient(
            path=self.persist_directory,
            settings=Settings(anonymized_telemetry=False)
        )
        
        # 브레인스토밍 컬렉션 가져오기
        self.collection_name = "brainstorming_techniques"
        self.collection = self.chroma_client.get_collection(name=self.collection_name)
    
    def _embed_query(self, query: str) -> List[float]:
        """질문을 임베딩 벡터로 변환"""
        response = self.openai_client.embeddings.create(
            model=self.embedding_model,
            input=query,
            encoding_format="float"
        )
        return response.data[0].embedding
    
    def search_techniques(self, query: str, n_results: int = 5, min_similarity: float = 0.0) -> List[Dict]:
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
            
            if similarity < min_similarity:
                continue
            
            metadata = results['metadatas'][0][idx]
            document = results['documents'][0][idx]
            
            formatted_results.append({
                "chunk_id": metadata['chunk_id'],
                "title": metadata['title'],
                "content": document,
                "similarity": round(similarity, 4),
                "metadata": {
                    "word_count": metadata.get('word_count', 0),
                    "char_count": metadata.get('char_count', 0),
                    "source_file": metadata.get('source_file', ''),
                    "embedding_model": metadata.get('embedding_model', '')
                }
            })
        
        return formatted_results
    
    def generate_suggestions(self, query: str, context_count: int = 3) -> Dict:
        """RAG를 사용하여 브레인스토밍 제안 생성"""
        relevant_chunks = self.search_techniques(
            query=query,
            n_results=context_count,
            min_similarity=0.3
        )
        
        if not relevant_chunks:
            return {
                "query": query,
                "suggestions": "관련된 브레인스토밍 기법을 찾을 수 없습니다.",
                "sources": []
            }
        
        context_text = "\n\n".join([
            f"[{chunk['title']}]\n{chunk['content']}"
            for chunk in relevant_chunks
        ])
        
        prompt = f"""당신은 브레인스토밍 전문가입니다. 
아래의 브레인스토밍 기법들을 참고하여 사용자의 상황에 가장 적합한 방법을 추천해주세요.

<참고 자료>
{context_text}

<사용자 질문>
{query}

위 자료를 바탕으로:
1. 이 상황에 가장 적합한 브레인스토밍 기법 2-3가지를 추천하고
2. 각 기법을 어떻게 적용하면 좋을지 구체적으로 설명해주세요.
3. 실행 시 주의사항도 함께 알려주세요.

친근하고 실용적인 톤으로 답변해주세요."""

        response = self.openai_client.chat.completions.create(
            model=self.llm_model,
            messages=[
                {"role": "system", "content": "당신은 브레인스토밍과 창의적 사고 전문가입니다."},
                {"role": "user", "content": prompt}
            ],
            temperature=self.llm_temperature,
            max_tokens=self.llm_max_tokens
        )
        
        suggestions = response.choices[0].message.content
        
        return {
            "query": query,
            "suggestions": suggestions,
            "sources": [
                {
                    "title": chunk['title'],
                    "chunk_id": chunk['chunk_id'],
                    "similarity": chunk['similarity']
                }
                for chunk in relevant_chunks
            ]
        }
    
    def get_technique_by_id(self, chunk_id: str) -> Optional[Dict]:
        """특정 청크 ID로 브레인스토밍 기법 조회"""
        try:
            result = self.collection.get(
                ids=[f"chunk_{chunk_id}"],
                include=["documents", "metadatas"]
            )
            
            if not result['ids']:
                return None
            
            metadata = result['metadatas'][0]
            document = result['documents'][0]
            
            return {
                "chunk_id": metadata['chunk_id'],
                "title": metadata['title'],
                "content": document,
                "metadata": {
                    "word_count": metadata.get('word_count', 0),
                    "char_count": metadata.get('char_count', 0),
                    "source_file": metadata.get('source_file', ''),
                    "embedding_model": metadata.get('embedding_model', '')
                }
            }
        except:
            return None
    
    def list_all_techniques(self) -> List[Dict]:
        """모든 브레인스토밍 기법 목록 조회"""
        result = self.collection.get(include=["metadatas"])
        
        techniques = []
        for idx, chunk_id in enumerate(result['ids']):
            metadata = result['metadatas'][idx]
            techniques.append({
                "chunk_id": metadata['chunk_id'],
                "title": metadata['title'],
                "word_count": metadata.get('word_count', 0)
            })
        
        techniques.sort(key=lambda x: x['chunk_id'])
        return techniques


def print_separator(char="=", length=60):
    """구분선 출력"""
    print(char * length)


def print_results(results, show_content=False):
    """검색 결과 출력"""
    if not results:
        print("❌ 검색 결과가 없습니다.")
        return
    
    print(f"\n📋 {len(results)}개의 결과를 찾았습니다:")
    print_separator("-")
    
    for idx, result in enumerate(results, 1):
        similarity_percent = result['similarity'] * 100
        
        print(f"\n{idx}. [{result['title']}]")
        print(f"   청크 ID: {result['chunk_id']}")
        print(f"   유사도: {similarity_percent:.2f}%")
        print(f"   글자 수: {result['metadata']['char_count']}")
        
        if show_content:
            content_preview = result['content'][:200]
            if len(result['content']) > 200:
                content_preview += "..."
            print(f"   내용: {content_preview}")
    
    print_separator("-")


def print_suggestions(result):
    """RAG 제안 출력"""
    print(f"\n💡 질문: {result['query']}")
    print_separator("-")
    print("\n📝 AI 제안:")
    print(result['suggestions'])
    print_separator("-")
    print(f"\n📚 참고한 자료 ({len(result['sources'])}개):")
    for idx, source in enumerate(result['sources'], 1):
        print(f"   {idx}. {source['title']} (유사도: {source['similarity']*100:.1f}%)")


def test_basic_search(service: BrainstormingService):
    """기본 검색 테스트"""
    print_separator()
    print("🔍 1. 기본 검색 테스트")
    print_separator()
    
    test_queries = [
        "팀 협업을 위한 브레인스토밍",
        "창의적인 아이디어를 빠르게 내는 방법",
        "문제 해결을 위한 체계적인 접근"
    ]
    
    for query in test_queries:
        print(f"\n🔎 검색: '{query}'")
        results = service.search_techniques(query, n_results=3)
        print_results(results, show_content=False)
        input("\n⏸️  계속하려면 Enter를 누르세요...")


def test_rag_suggestions(service: BrainstormingService):
    """RAG 제안 테스트"""
    print_separator()
    print("💡 2. RAG AI 제안 테스트")
    print_separator()
    
    test_scenarios = [
        "우리 팀은 신제품 아이디어를 찾고 있어요. 5명의 팀원이 있고, 회의 시간은 1시간입니다.",
        "마케팅 캠페인을 기획해야 하는데 막막해요. 어떤 방법이 좋을까요?"
    ]
    
    for scenario in test_scenarios:
        print(f"\n📌 상황: {scenario}")
        print("\n⏳ AI가 분석 중...")
        result = service.generate_suggestions(scenario, context_count=3)
        print_suggestions(result)
        input("\n⏸️  계속하려면 Enter를 누르세요...")


def interactive_mode(service: BrainstormingService):
    """대화형 모드"""
    print_separator()
    print("💬 3. 대화형 검색 모드")
    print_separator()
    print("\n명령어:")
    print("  - 검색어 입력: 브레인스토밍 기법 검색")
    print("  - 'rag [질문]': AI 제안 받기")
    print("  - 'list': 모든 기법 목록 보기")
    print("  - 'id [번호]': 특정 기법 상세보기")
    print("  - 'quit': 종료")
    print_separator()
    
    while True:
        try:
            user_input = input("\n🔍 입력 >>> ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() == 'quit':
                print("\n👋 테스트를 종료합니다.")
                break
            
            if user_input.lower() == 'list':
                print("\n📚 모든 브레인스토밍 기법:")
                techniques = service.list_all_techniques()
                for tech in techniques:
                    print(f"  [{tech['chunk_id']}] {tech['title']} ({tech['word_count']}자)")
                continue
            
            if user_input.lower().startswith('id '):
                chunk_id = user_input[3:].strip()
                result = service.get_technique_by_id(chunk_id)
                if result:
                    print(f"\n📖 [{result['title']}]")
                    print(f"   청크 ID: {result['chunk_id']}")
                    print(f"   글자 수: {result['metadata']['char_count']}")
                    print(f"\n{result['content']}")
                else:
                    print(f"❌ 청크 ID '{chunk_id}'를 찾을 수 없습니다.")
                continue
            
            if user_input.lower().startswith('rag '):
                query = user_input[4:].strip()
                if query:
                    print("\n⏳ AI가 분석 중...")
                    result = service.generate_suggestions(query, context_count=3)
                    print_suggestions(result)
                else:
                    print("❌ 질문을 입력해주세요. 예: rag 팀 협업 방법")
                continue
            
            # 일반 검색
            print(f"\n🔎 검색 중: '{user_input}'")
            results = service.search_techniques(user_input, n_results=5)
            print_results(results, show_content=True)
            
        except KeyboardInterrupt:
            print("\n\n👋 테스트를 종료합니다.")
            break
        except Exception as e:
            print(f"\n❌ 오류: {e}")


def main():
    """메인 함수"""
    print("""
╔═══════════════════════════════════════════════════════╗
║   🧠 브레인스토밍 RAG 검색 테스트                      ║
╚═══════════════════════════════════════════════════════╝
""")
    
    # 서비스 초기화
    print("⏳ 서비스 초기화 중...")
    try:
        service = BrainstormingService()
        print("✅ 서비스 초기화 완료!")
        print(f"📦 컬렉션: {service.collection_name}")
        print(f"🔢 저장된 기법: {service.collection.count()}개")
    except Exception as e:
        import traceback
        print(f"❌ 서비스 초기화 실패: {e}")
        print("\n🔍 상세 에러:")
        traceback.print_exc()
        print("\n💡 해결 방법:")
        print("   1. chroma_loader.py를 먼저 실행하여 벡터 DB를 구축하세요")
        print("   2. .env 파일에 OPENAI_API_KEY가 설정되어 있는지 확인하세요")
        sys.exit(1)
    
    # 메뉴
    while True:
        print("\n" + "=" * 60)
        print("테스트 모드를 선택하세요:")
        print("  1. 기본 검색 테스트 (미리 정의된 쿼리)")
        print("  2. RAG AI 제안 테스트 (미리 정의된 시나리오)")
        print("  3. 대화형 모드 (자유롭게 검색)")
        print("  4. 전체 테스트 (1 + 2 + 3)")
        print("  0. 종료")
        print("=" * 60)
        
        try:
            choice = input("\n선택 >>> ").strip()
            
            if choice == '0':
                print("\n👋 종료합니다.")
                break
            elif choice == '1':
                test_basic_search(service)
            elif choice == '2':
                test_rag_suggestions(service)
            elif choice == '3':
                interactive_mode(service)
            elif choice == '4':
                test_basic_search(service)
                test_rag_suggestions(service)
                interactive_mode(service)
            else:
                print("❌ 잘못된 선택입니다. 0-4 사이의 숫자를 입력하세요.")
        
        except KeyboardInterrupt:
            print("\n\n👋 종료합니다.")
            break
        except Exception as e:
            print(f"\n❌ 오류: {e}")


if __name__ == "__main__":
    main()

