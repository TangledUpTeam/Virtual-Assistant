# 🚨 동시성(Concurrency) 이슈 정리

**작성자:** 진모  
**작성일:** 2025-11-20  
**중요도:** ⚠️ 높음 (서버 배포 전 필수 확인)

---

## 📋 요약

현재 프로젝트의 여러 모듈에서 **SessionManager**를 사용하고 있으나, **동시성 처리가 일관되지 않아** 서버 환경에서 **데이터 손실 또는 충돌 위험**이 있습니다.

---

## 🔍 문제 정의

### 문제 1: 동시 접근 시 데이터 손실 (Race Condition)

**시나리오:**
```
시간 1: 사용자 A가 세션 생성 요청
시간 1: 사용자 B가 세션 생성 요청 (동시!)

Thread A: sessions["abc"] = context_A  ← 저장
Thread B: sessions["abc"] = context_B  ← 덮어씀!

결과: context_A 데이터 손실! 💥
```

### 문제 2: 메모리 누수 또는 잘못된 상태

**시나리오:**
```
Thread A: if "abc" not in sessions:  ← 확인 (없음)
Thread B: if "abc" not in sessions:  ← 확인 (없음, 동시)
Thread A:     sessions["abc"] = {}   ← 생성
Thread B:     sessions["abc"] = {}   ← 다시 생성 (덮어씀)

결과: Thread A의 작업 내용 손실!
```

---

## 📊 현재 상태 분석

### 모듈별 동시성 처리 현황

| 모듈 | 파일 | Lock 사용 | Atomic 연산 | 위험도 |
|------|------|-----------|-------------|--------|
| **brainstorming** | `session_manager.py` | ✅ Yes (`threading.Lock` + `asyncio.Lock`) | ⚠️ Partial | 🟡 중간 |
| **daily** | `session_manager.py` | ❌ **No** | ❌ **No** | 🔴 **높음** |
| **chatbot** | `session_manager.py` | ✅ Yes (`threading.Lock`) | ⚠️ Partial | 🟡 중간 |
| **rag** | `retriever.py` | ❓ 확인 필요 | ❓ 확인 필요 | ❓ 미확인 |
| **planner** | - | ❓ 확인 필요 | ❓ 확인 필요 | ❓ 미확인 |

---

## 🚨 위험한 코드 예시

### ❌ **문제 코드 (daily/session_manager.py)**

```python
class SessionManager:
    def __init__(self):
        self._sessions: Dict[str, DailyFSMContext] = {}  # ← Lock 없음!
    
    def create_session(self, context: DailyFSMContext) -> str:
        session_id = str(uuid.uuid4())
        self._sessions[session_id] = context  # ← Race condition 발생 가능!
        return session_id
    
    def get_session(self, session_id: str) -> Optional[DailyFSMContext]:
        return self._sessions.get(session_id)  # ← 읽는 중 삭제될 수 있음!
```

**문제점:**
- 여러 스레드가 동시에 `_sessions` 딕셔너리에 접근
- 한 스레드가 쓰는 동안 다른 스레드가 읽으면 충돌
- Python dict는 thread-safe하지 않음!

---

## ✅ 해결 방안

### 방안 1: 전역 Lock (간단, 성능 낮음)

```python
import threading

class SessionManager:
    def __init__(self):
        self._sessions = {}
        self._lock = threading.Lock()  # ← 전역 Lock
    
    def create_session(self, context):
        with self._lock:  # ← 한 번에 하나씩만
            session_id = str(uuid.uuid4())
            self._sessions[session_id] = context
            return session_id
    
    def get_session(self, session_id):
        with self._lock:  # ← 안전하게 읽기
            return self._sessions.get(session_id)
```

**장점:**
- ✅ 구현 간단
- ✅ 안전성 보장

**단점:**
- ❌ 성능 병목 (모든 세션이 같은 Lock 대기)
- ❌ 동시 처리 능력 낮음

---

### 방안 2: 세션별 Lock (권장 ⭐)

```python
import threading
from collections import defaultdict
from threading import RLock

class SessionManager:
    def __init__(self):
        self._sessions = {}
        self._session_locks = defaultdict(RLock)  # ← 세션별 Lock
        self._global_lock = RLock()  # 딕셔너리 생성용
    
    def create_session(self, context):
        session_id = str(uuid.uuid4())
        
        with self._session_locks[session_id]:  # ← 세션별 Lock
            with self._global_lock:  # ← 딕셔너리 수정 시만
                self._sessions[session_id] = context
        
        return session_id
    
    def get_session(self, session_id):
        with self._session_locks[session_id]:  # ← 안전하게 읽기
            return self._sessions.get(session_id)
```

**장점:**
- ✅ 세션별 독립적 Lock (Java의 ConcurrentHashMap 수준)
- ✅ 성능 우수 (병렬 처리 가능)
- ✅ 확장성 좋음

**단점:**
- ⚠️ 구현 복잡
- ⚠️ 메모리 사용량 증가 (Lock 객체 많아짐)

---

### 방안 3: 공통 Base Class 생성 (장기적 해결)

```python
# backend/app/domain/common/base_session_manager.py

from collections import defaultdict
from threading import RLock
from abc import ABC, abstractmethod

class BaseSessionManager(ABC):
    """
    모든 SessionManager가 상속받는 기본 클래스
    - 세션별 Lock으로 fine-grained 동시성 제어
    - Atomic 연산 보장
    """
    
    def __init__(self):
        self._sessions = {}
        self._session_locks = defaultdict(RLock)
        self._global_lock = RLock()
    
    def _safe_get_or_create(self, session_id, factory_func):
        """Atomic한 get-or-create 패턴"""
        with self._session_locks[session_id]:
            if session_id not in self._sessions:
                with self._global_lock:
                    if session_id not in self._sessions:
                        self._sessions[session_id] = factory_func()
            return self._sessions[session_id]
    
    def _safe_get(self, session_id):
        """안전한 조회"""
        with self._session_locks[session_id]:
            return self._sessions.get(session_id)
    
    def _safe_delete(self, session_id):
        """안전한 삭제"""
        with self._session_locks[session_id]:
            with self._global_lock:
                if session_id in self._sessions:
                    del self._sessions[session_id]
```

**사용 예시:**
```python
# 각 모듈에서 상속
class DailySessionManager(BaseSessionManager):
    def create_session(self, context):
        session_id = str(uuid.uuid4())
        self._safe_get_or_create(session_id, lambda: context)
        return session_id
```

---

## 🎯 권장 조치 사항

### 단기 (즉시 필요) - 우선순위 순

1. **daily/session_manager.py 수정 (🔴 긴급)**
   - 최소한 전역 Lock 추가
   - 작업자: daily 모듈 담당자
   - 예상 시간: 10분

2. **다른 모듈 Lock 상태 확인**
   - rag, planner, search 등
   - 작업자: 각 모듈 담당자
   - 예상 시간: 5분/모듈

3. **chatbot, brainstorming 개선 (🟡 중요)**
   - 전역 Lock → 세션별 Lock
   - 작업자: 진모
   - 예상 시간: 30분

### 중기 (FastAPI 연동 후)

1. **부하 테스트 실행**
   - 동시 사용자 100명 시뮬레이션
   - Lock contention 측정

2. **성능 병목 확인**
   - Profiling 도구 사용
   - 개선 필요 부분 식별

### 장기 (배포 전 필수)

1. **공통 Base Class 구현**
   - `BaseSessionManager` 생성
   - 모든 모듈 통일

2. **통합 테스트**
   - 전체 모듈 동시성 테스트
   - 데이터 무결성 검증

---

## 💡 추가 고려사항

### FastAPI 환경

FastAPI는 기본적으로 **멀티스레드**로 요청을 처리합니다:

```python
# 요청 1 (Thread 1)
@router.post("/daily/start")
async def start_daily(request):
    session_manager.create_session(context)  # ← 동시 실행!

# 요청 2 (Thread 2)
@router.post("/daily/start")
async def start_daily(request):
    session_manager.create_session(context)  # ← 동시 실행!
```

**→ Lock 없으면 충돌 발생!**

### 다중 서버 배포 시 (추후)

현재 `SessionManager`는 **메모리 기반**이므로:

```
서버 A의 SessionManager ≠ 서버 B의 SessionManager
```

**해결책 (추후 고려):**
- Redis (세션 공유)
- PostgreSQL (영속성)
- Sticky Session (사용자를 특정 서버에 고정)

---

## 📚 참고 자료

### Python의 Thread Safety

**Thread-safe:**
- `queue.Queue`
- `threading.Lock`
- `collections.deque` (일부 연산)

**NOT Thread-safe:**
- `dict` ❌
- `list` ❌
- `set` ❌

### Java와 비교

| Java | Python |
|------|--------|
| `ConcurrentHashMap` | `dict` + `defaultdict(Lock)` |
| `AtomicInteger` | `threading.Lock` + counter |
| `synchronized` | `with lock:` |
| `ReentrantLock` | `threading.RLock` |

---

## 🤝 논의 사항

1. **우선순위 합의**
   - 어떤 모듈부터 수정할지

2. **공통 모듈 필요성**
   - Base Class 만들 것인지
   - 각자 독립적으로 처리할 것인지

3. **코드 리뷰 프로세스**
   - 동시성 관련 코드는 필수 리뷰

4. **테스트 전략**
   - 부하 테스트 언제 할지
   - 누가 담당할지

---

## ✅ 체크리스트

각 모듈 담당자는 아래를 확인해주세요:

- [ ] SessionManager에 Lock 사용 여부 확인
- [ ] 동시 접근 가능한 공유 자원 파악
- [ ] Race condition 위험 코드 식별
- [ ] 개선 방안 논의 및 적용
- [ ] 테스트 코드 작성

---

## 📞 문의

질문이나 추가 논의가 필요하면:
- Slack: @진모
- 이슈: GitHub Issues에 `concurrency` 태그로 등록

---

**⚠️ 중요:** 이 문서는 서버 배포 전 필수 체크 사항입니다.  
무시하면 프로덕션 환경에서 **심각한 버그** 발생 가능!

