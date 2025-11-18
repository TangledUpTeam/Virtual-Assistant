# ⚠️ Chroma Cloud 연동 이슈 및 해결 방안

## 📋 발생한 문제

Chroma Cloud API 버전 문제로 인해 ingestion 파이프라인 실행이 실패했습니다.

### 문제 1: API 버전 호환성
```
Exception: {"error":"Unimplemented","message":"The v1 API is deprecated. Please use /v2 apis"}
```

**원인**: 
- Chroma Cloud가 v1 API를 deprecated하고 v2 API로 마이그레이션
- `chromadb==0.6.3`: v2 API 지원하지만 응답 파싱 오류 (`_type` 필드 누락)
- `chromadb==0.4.24`: v1 API 사용, Chroma Cloud에서 더 이상 지원하지 않음

### 문제 2: 라이브러리 호환성
```
KeyError: '_type'
```

**원인**:
- ChromaDB Python 클라이언트 0.6.x와 Chroma Cloud 서버 간의 응답 스키마 불일치

---

## 💡 해결 방안

### ✅ 권장 방안 1: 로컬 Chroma 서버 사용

가장 안정적이고 빠른 해결 방법입니다.

#### 1-1. Chroma 서버 설치 및 실행

```bash
# Docker로 실행 (권장)
docker pull chromadb/chroma
docker run -p 8000:8000 chromadb/chroma

# 또는 Python으로 실행
pip install chromadb
chroma run --path ./chroma_data
```

#### 1-2. `chroma_client.py` 수정

```python
import chromadb

class ChromaCloudService:
    def __init__(self):
        print("🔗 Chroma 로컬 서버 연결 중...")
        
        # 로컬 서버 연결
        self.client = chromadb.HttpClient(
            host="localhost",
            port=8000
        )
        
        print("✅ Chroma 연결 성공")
```

#### 1-3. 실행

```bash
cd backend
python ingestion/init_ingest.py
```

---

### ✅ 권장 방안 2: Pinecone 사용

Pinecone은 안정적이고 프로덕션 레디한 Cloud Vector DB입니다.

#### 2-1. Pinecone 설치

```bash
pip install pinecone-client
```

#### 2-2. 새 파일 생성: `backend/ingestion/pinecone_client.py`

```python
from pinecone import Pinecone, ServerlessSpec

PINECONE_API_KEY = "YOUR_API_KEY"
INDEX_NAME = "virtual-assistant"

class PineconeService:
    def __init__(self):
        self.pc = Pinecone(api_key=PINECONE_API_KEY)
        
        # 인덱스 생성 (없으면)
        if INDEX_NAME not in self.pc.list_indexes().names():
            self.pc.create_index(
                name=INDEX_NAME,
                dimension=3072,  # text-embedding-3-large
                metric="cosine",
                spec=ServerlessSpec(cloud="aws", region="us-east-1")
            )
        
        self.index = self.pc.Index(INDEX_NAME)
    
    def upsert(self, vectors):
        """
        vectors: [
            {
                "id": "chunk_001",
                "values": [0.1, 0.2, ...],  # 임베딩 벡터
                "metadata": {...}
            },
            ...
        ]
        """
        self.index.upsert(vectors=vectors)
    
    def query(self, vector, top_k=5, filter=None):
        """검색"""
        return self.index.query(
            vector=vector,
            top_k=top_k,
            filter=filter,
            include_metadata=True
        )
```

#### 2-3. `ingest_reports.py` 수정

```python
from ingestion.pinecone_client import PineconeService
from ingestion.embed import embed_texts

def ingest_reports(chunks, api_key=None):
    # 임베딩 생성
    texts = [chunk["chunk_text"] for chunk in chunks]
    embeddings = embed_texts(texts, api_key=api_key)
    
    # Pinecone 형식으로 변환
    vectors = []
    for i, chunk in enumerate(chunks):
        vectors.append({
            "id": chunk["id"],
            "values": embeddings[i],
            "metadata": chunk["metadata"]
        })
    
    # Pinecone에 업로드
    service = PineconeService()
    service.upsert(vectors)
```

---

### ✅ 권장 방안 3: Qdrant 사용

Qdrant는 빠르고 오픈소스이며, Docker로 쉽게 배포할 수 있습니다.

#### 3-1. Qdrant 서버 실행

```bash
docker run -p 6333:6333 qdrant/qdrant
```

#### 3-2. Qdrant 클라이언트 설치

```bash
pip install qdrant-client
```

#### 3-3. 새 파일 생성: `backend/ingestion/qdrant_client.py`

```python
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

class QdrantService:
    def __init__(self):
        self.client = QdrantClient(host="localhost", port=6333)
        
        # 컬렉션 생성
        collections = [c.name for c in self.client.get_collections().collections]
        
        if "reports" not in collections:
            self.client.create_collection(
                collection_name="reports",
                vectors_config=VectorParams(size=3072, distance=Distance.COSINE)
            )
        
        if "kpi" not in collections:
            self.client.create_collection(
                collection_name="kpi",
                vectors_config=VectorParams(size=3072, distance=Distance.COSINE)
            )
    
    def upsert(self, collection_name, points):
        """
        points: [
            PointStruct(
                id="chunk_001",
                vector=[0.1, 0.2, ...],
                payload={"metadata": {...}}
            ),
            ...
        ]
        """
        self.client.upsert(collection_name=collection_name, points=points)
    
    def search(self, collection_name, vector, limit=5, filter=None):
        """검색"""
        return self.client.search(
            collection_name=collection_name,
            query_vector=vector,
            limit=limit,
            query_filter=filter
        )
```

---

## 🎯 최종 권장사항

| 방안 | 장점 | 단점 | 추천도 |
|------|------|------|--------|
| **로컬 Chroma** | 빠른 설정, 무료, 개발용으로 최적 | 프로덕션 확장성 제한 | ⭐⭐⭐⭐⭐ |
| **Pinecone** | 프로덕션 레디, 안정적, 관리 불필요 | 유료 (무료 티어 있음) | ⭐⭐⭐⭐ |
| **Qdrant** | 빠름, 오픈소스, 자체 호스팅 가능 | 서버 관리 필요 | ⭐⭐⭐⭐ |
| **Chroma Cloud** | 관리 불필요 | **현재 API 호환성 문제** | ❌ |

---

## 📝 다음 단계

### 옵션 A: 로컬 Chroma (빠른 시작)

```bash
# 1. Docker로 Chroma 실행
docker run -p 8000:8000 chromadb/chroma

# 2. chroma_client.py 수정 (위 코드 참조)

# 3. 실행
cd backend
python ingestion/init_ingest.py
```

### 옵션 B: Pinecone (프로덕션)

```bash
# 1. Pinecone 가입 및 API 키 발급
# https://www.pinecone.io/

# 2. pinecone_client.py 생성 (위 코드 참조)

# 3. ingest_reports.py, ingest_kpi.py 수정

# 4. 실행
cd backend
python ingestion/init_ingest.py
```

---

## 📞 문의

- **로컬 Chroma 추천**: 개발 및 테스트용으로 가장 빠르고 간단
- **Pinecone 추천**: 프로덕션 배포 시
- **Qdrant 추천**: 자체 호스팅이 필요한 경우

어떤 옵션을 선택하시겠습니까?

