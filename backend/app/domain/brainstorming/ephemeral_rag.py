"""
임시 RAG (Ephemeral RAG) 모듈

세션별 임시 데이터를 처리합니다:
1. Q3 자유연상 입력을 임베딩
2. 임시 ChromaDB 컬렉션에 저장
3. Q1 목적과 Q3 연상 간의 코사인 유사도 기반 키워드 추출
4. 영구 RAG (SCAMPER, Mind Mapping, Starbursting)와 결합하여 아이디어 생성
"""

import json
from pathlib import Path
from typing import List, Dict, Optional
import chromadb
from openai import OpenAI
from dotenv import load_dotenv
import os


class EphemeralRAG:
    """
    세션별 임시 RAG 처리 클래스
    
    각 세션마다 독립적인 ChromaDB 컬렉션을 생성하고,
    Q3 자유연상 데이터를 임베딩하여 저장합니다.
    """
    
    def __init__(self, session_id: str, collection_name: str, chroma_client=None):
        """
        초기화
        
        Args:
            session_id: 세션 ID
            collection_name: ChromaDB 컬렉션 이름 (예: ephemeral_session_xxx)
            chroma_client: 기존 ChromaDB 클라이언트 (선택적, 없으면 새로 생성)
        """
        # .env 파일 로드
        load_dotenv()
        
        self.session_id = session_id
        self.collection_name = collection_name
        
        # OpenAI 클라이언트 초기화
        self.openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.embedding_model = os.getenv("EMBEDDING_MODEL", "text-embedding-3-large")
        
        # ChromaDB 클라이언트 (전달받거나 새로 생성)
        if chroma_client:
            self.chroma_client = chroma_client
            print(f"✅ 기존 ChromaDB 클라이언트 재사용")
        else:
            # ChromaDB 클라이언트 초기화 (영구 RAG와 동일한 persist directory 사용)
            current_file = Path(__file__).resolve()
            module_dir = current_file.parent
            self.persist_directory = str(module_dir / "data" / "chroma")
            
            self.chroma_client = chromadb.PersistentClient(path=self.persist_directory)
            print(f"✅ 새 ChromaDB 클라이언트 생성")
        
        # 임시 컬렉션 생성 (이미 존재하면 가져오기)
        try:
            self.collection = self.chroma_client.get_collection(name=self.collection_name)
            print(f"✅ 기존 임시 컬렉션 로드: {self.collection_name}")
        except:
            self.collection = self.chroma_client.create_collection(
                name=self.collection_name,
                metadata={"session_id": session_id, "type": "ephemeral"}
            )
            print(f"✅ 새 임시 컬렉션 생성: {self.collection_name}")
    
    def embed_text(self, text: str) -> List[float]:
        """
        텍스트를 임베딩 벡터로 변환
        
        Args:
            text: 임베딩할 텍스트
            
        Returns:
            List[float]: 임베딩 벡터
        """
        try:
            response = self.openai_client.embeddings.create(
                model=self.embedding_model,
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            print(f"❌ 임베딩 실패: {e}")
            raise
    
    def add_associations(self, associations: List[str]) -> bool:
        """
        Q3 자유연상 데이터를 임베딩하여 임시 컬렉션에 추가
        
        Args:
            associations: 자유연상 단어/문구 리스트
            
        Returns:
            bool: 성공 여부
        """
        try:
            documents = []
            embeddings = []
            ids = []
            metadatas = []
            
            for idx, association in enumerate(associations):
                # 임베딩 생성
                embedding = self.embed_text(association)
                
                documents.append(association)
                embeddings.append(embedding)
                ids.append(f"assoc_{idx}")
                metadatas.append({
                    "type": "q3_association",
                    "index": idx,
                    "session_id": self.session_id
                })
            
            # ChromaDB에 추가
            self.collection.add(
                documents=documents,
                embeddings=embeddings,
                ids=ids,
                metadatas=metadatas
            )
            
            print(f"✅ {len(associations)}개의 연상 단어를 임시 컬렉션에 추가했습니다.")
            return True
            
        except Exception as e:
            print(f"❌ 연상 단어 추가 실패: {e}")
            return False
    
    def extract_keywords_by_similarity(self, purpose: str, top_k: int = 5) -> List[Dict]:
        """
        Q1 목적과 Q3 연상 간의 코사인 유사도를 계산하여 상위 키워드 추출
        
        Args:
            purpose: Q1 목적 (예: "모바일 앱 아이디어")
            top_k: 추출할 상위 키워드 개수
            
        Returns:
            List[Dict]: 상위 키워드 리스트 (각각 document, distance 포함)
        """
        try:
            # Q1 목적 임베딩
            purpose_embedding = self.embed_text(purpose)
            
            # ChromaDB에서 유사도 기반 검색
            results = self.collection.query(
                query_embeddings=[purpose_embedding],
                n_results=top_k
            )
            
            keywords = []
            if results['documents'] and len(results['documents'][0]) > 0:
                for i in range(len(results['documents'][0])):
                    keywords.append({
                        'keyword': results['documents'][0][i],
                        'distance': results['distances'][0][i] if results['distances'] else None,
                        'similarity': 1 - results['distances'][0][i] if results['distances'] else None,
                        'metadata': results['metadatas'][0][i] if results['metadatas'] else None
                    })
            
            print(f"\n✅ Q1과 가장 유사한 상위 {len(keywords)}개 키워드:")
            for i, kw in enumerate(keywords, 1):
                print(f"   {i}. {kw['keyword']} (유사도: {kw['similarity']:.4f})")
            
            return keywords
            
        except Exception as e:
            print(f"❌ 키워드 추출 실패: {e}")
            return []
    
    def search_associations(self, query: str, n_results: int = 5) -> List[Dict]:
        """
        임시 컬렉션에서 연상 단어 검색
        
        Args:
            query: 검색 쿼리
            n_results: 반환할 결과 개수
            
        Returns:
            List[Dict]: 검색 결과 리스트
        """
        try:
            query_embedding = self.embed_text(query)
            
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results
            )
            
            search_results = []
            if results['documents'] and len(results['documents'][0]) > 0:
                for i in range(len(results['documents'][0])):
                    search_results.append({
                        'document': results['documents'][0][i],
                        'distance': results['distances'][0][i] if results['distances'] else None,
                        'metadata': results['metadatas'][0][i] if results['metadatas'] else None
                    })
            
            return search_results
            
        except Exception as e:
            print(f"❌ 검색 실패: {e}")
            return []
    
    def delete_collection(self) -> bool:
        """
        임시 컬렉션 삭제
        
        세션 종료 시 호출하여 임시 데이터를 완전히 제거합니다.
        
        Returns:
            bool: 성공 여부
        """
        try:
            self.chroma_client.delete_collection(name=self.collection_name)
            print(f"✅ 임시 컬렉션 삭제 완료: {self.collection_name}")
            return True
        except Exception as e:
            print(f"❌ 컬렉션 삭제 실패: {e}")
            return False
    
    def get_collection_count(self) -> int:
        """
        컬렉션에 저장된 항목 개수 조회
        
        Returns:
            int: 항목 개수
        """
        try:
            return self.collection.count()
        except:
            return 0


# 테스트 코드
if __name__ == "__main__":
    import sys
    sys.path.append(str(Path(__file__).resolve().parent))
    from session_manager import SessionManager
    
    print("=" * 60)
    print("임시 RAG 테스트")
    print("=" * 60)
    
    # 1. 세션 생성
    print("\n[1] 세션 생성")
    manager = SessionManager()
    session_id = manager.create_session()
    session = manager.get_session(session_id)
    print(f"    세션 ID: {session_id}")
    print(f"    컬렉션 이름: {session['chroma_collection']}")
    
    # 2. Ephemeral RAG 초기화
    print("\n[2] Ephemeral RAG 초기화")
    ephemeral_rag = EphemeralRAG(
        session_id=session_id,
        collection_name=session['chroma_collection']
    )
    
    # 3. Q1 목적 설정
    print("\n[3] Q1 목적 설정")
    q1_purpose = "건강 관리 모바일 앱 아이디어"
    manager.update_session(session_id, {'q1_purpose': q1_purpose})
    print(f"    Q1: {q1_purpose}")
    
    # 4. Q3 자유연상 추가
    print("\n[4] Q3 자유연상 추가")
    q3_associations = [
        "운동", "식단", "수면", "스트레칭", "요가",
        "칼로리", "걸음 수", "심박수", "명상", "물 마시기",
        "체중 기록", "목표 설정", "친구와 경쟁", "보상", "알림"
    ]
    manager.update_session(session_id, {'q3_associations': q3_associations})
    ephemeral_rag.add_associations(q3_associations)
    print(f"    추가된 연상 단어: {len(q3_associations)}개")
    print(f"    컬렉션 항목 수: {ephemeral_rag.get_collection_count()}개")
    
    # 5. Q1과 Q3 간 유사도 기반 키워드 추출
    print("\n[5] Q1-Q3 유사도 기반 키워드 추출")
    top_keywords = ephemeral_rag.extract_keywords_by_similarity(q1_purpose, top_k=7)
    
    # 6. 특정 쿼리로 검색
    print("\n[6] 특정 쿼리로 검색")
    search_query = "운동과 관련된 기능"
    search_results = ephemeral_rag.search_associations(search_query, n_results=3)
    print(f"    검색 쿼리: {search_query}")
    for i, result in enumerate(search_results, 1):
        print(f"    {i}. {result['document']} (거리: {result['distance']:.4f})")
    
    # 7. 임시 컬렉션 삭제
    print("\n[7] 임시 컬렉션 삭제")
    ephemeral_rag.delete_collection()
    
    # 8. 세션 삭제
    print("\n[8] 세션 삭제")
    manager.delete_session(session_id)
    print(f"    남은 세션 수: {manager.get_session_count()}개")
    
    print("\n" + "=" * 60)
    print("✅ 테스트 완료")
    print("=" * 60)

