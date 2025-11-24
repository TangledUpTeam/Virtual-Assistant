"""
LangSmith 추적 테스트 스크립트
"""

from app.domain.rag.HR.retriever import RAGRetriever
from app.domain.rag.HR.schemas import QueryRequest

def test_langsmith():
    print("=" * 80)
    print("LangSmith 추적 테스트")
    print("=" * 80)
    
    # RAG Retriever 초기화
    retriever = RAGRetriever()
    
    # 테스트 쿼리
    test_query = "휴가 신청은 어떻게 하나요?"
    print(f"\n질문: {test_query}")
    print("-" * 80)
    
    # 쿼리 실행
    request = QueryRequest(query=test_query)
    response = retriever.query(request)
    
    # 결과 출력
    print(f"\n답변:\n{response.answer}")
    print(f"\n검색된 문서: {len(response.retrieved_chunks)}개")
    print(f"처리 시간: {response.processing_time:.2f}초")
    print(f"사용 모델: {response.model_used}")
    
    print("\n" + "=" * 80)
    print("✅ 테스트 완료!")
    print("🔍 LangSmith 대시보드를 확인하세요:")
    print("   https://smith.langchain.com")
    print("   프로젝트: virtual-assistant-rag")
    print("=" * 80)

if __name__ == "__main__":
    test_langsmith()

