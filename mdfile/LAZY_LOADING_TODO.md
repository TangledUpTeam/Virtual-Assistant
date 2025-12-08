# 🚀 Lazy Loading 적용 TODO

## 📌 현재 상황 (2025-11-20)

### 문제점
- 서버 시작 시 **모든 모듈을 미리 로드**
- 현재 2개 모듈 (브레인스토밍, 챗봇)
- **4~5개 모듈 추가 예정** → 서버 시작 시간 10초 이상 예상

### 현재 구조
```python
# backend/app/api/v1/endpoints/brainstorming.py (Line 39-61)
# 모듈 import 시점에 초기화 실행 ❌

session_manager = SessionManager()  # 즉시 실행
openai_client = OpenAI(...)  # 즉시 실행
chroma_client = chromadb.PersistentClient(...)  # 즉시 실행
permanent_collection = chroma_client.get_collection(...)  # 즉시 실행
```

**결과:**
- 서버 시작 시 모든 모듈 초기화 (현재 5초 소요)
- 사용하지 않는 모듈도 메모리 점유
- 한 모듈 실패 시 전체 서버 시작 실패

---

## 💡 해결 방법: Lazy Loading

### 개념
엔드포인트가 **처음 호출될 때만** 초기화

### 예시 코드
```python
# backend/app/api/v1/endpoints/brainstorming.py
from functools import lru_cache
from fastapi import Depends

# 전역 변수 삭제 ❌
# session_manager = SessionManager()

# Lazy 초기화 함수 추가 ✅
@lru_cache()
def get_brainstorming_service():
    """첫 호출 시에만 초기화 (이후 캐싱)"""
    session_manager = SessionManager()
    openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    chroma_client = chromadb.PersistentClient(
        path=persist_directory,
        settings=ChromaSettings(anonymized_telemetry=False)
    )
    
    try:
        permanent_collection = chroma_client.get_collection(
            name="brainstorming_techniques"
        )
    except Exception as e:
        permanent_collection = None
    
    return {
        "session_manager": session_manager,
        "openai_client": openai_client,
        "chroma_client": chroma_client,
        "permanent_collection": permanent_collection
    }

# 엔드포인트에서 사용 ✅
@router.post("/session")
async def create_session(service = Depends(get_brainstorming_service)):
    session_id = service["session_manager"].create_session()
    return SessionResponse(session_id=session_id, message="세션 생성 완료")
```

### 장점
✅ 서버 시작 빠름 (1초 이내)
✅ 사용하는 모듈만 메모리 로드
✅ 한 모듈 실패해도 서버는 시작됨
✅ 확장성 좋음 (10개 모듈도 문제없음)

### 적용 대상 모듈
1. `backend/app/api/v1/endpoints/brainstorming.py`
2. `backend/app/api/v1/endpoints/chatbot.py`
3. (향후 추가될 4~5개 모듈)

---

## 📅 작업 계획

### 우선순위: 중간
- 현재는 2개 모듈이라 괜찮음
- **7~10개 모듈 시점**에 필수

### 예상 작업 시간
- 모듈당 30분~1시간
- 전체 2~3시간

### 작업 순서
1. `brainstorming.py` Lazy Loading 적용
2. `chatbot.py` Lazy Loading 적용
3. 테스트 (기능 동작 확인)
4. 새 모듈 추가 시 Lazy 패턴 적용

---

## 🔗 참고 자료
- [FastAPI Dependency Injection](https://fastapi.tiangolo.com/tutorial/dependencies/)
- [Python lru_cache](https://docs.python.org/3/library/functools.html#functools.lru_cache)

