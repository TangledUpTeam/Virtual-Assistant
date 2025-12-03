# Virtual Assistant - 아키텍처 검토 & 개선 방안

> 작성일: 2025-11-25  
> 목적: 기획 대비 구현 현황 파악 및 에이전트 기반 통합 방안 제시

---

## 📊 현재 구현 현황 분석

### ✅ 구현 완료된 모듈

| 모듈 | 상태 | 기능 | RAG | 엔드포인트 |
|------|------|------|-----|------------|
| **브레인스토밍** | ✅ 완료 | 이중 RAG 아이디어 생성 | ✅ 영구 + Ephemeral | `/api/v1/brainstorming` |
| **챗봇 기본** | ✅ 완료 | GPT-4o 대화, 히스토리 관리 | ❌ | `/api/v1/chatbot` |
| **심리 상담** | ✅ 완료 | 아들러 심리학 RAG 상담 | ✅ 영구 | `/api/v1/therapy` |
| **HR RAG** | ✅ 완료 | 인사 규정 RAG 검색 | ✅ 영구 | `/api/v1/rag` |
| **Insurance RAG** | ✅ 완료 | 보험 지식 RAG 검색 | ✅ 영구 | `/api/v1/rag` |
| **Daily Report** | ✅ 완료 | 일일 업무 보고서 FSM | ❌ | `/api/v1/daily-report` |
| **Weekly Report** | ✅ 완료 | 주간 보고서 생성 | ❌ | `/api/v1/weekly-report` |
| **Monthly Report** | ✅ 완료 | 월간 보고서 생성 | ❌ | `/api/v1/monthly-report` |
| **Performance** | ✅ 완료 | 실적 보고서 생성 | ❌ | `/api/v1/performance-report` |
| **KPI** | ✅ 완료 | KPI 데이터 정규화 | ✅ 영구 | - |
| **Planner** | ✅ 완료 | 오늘 일정 계획 | ❌ | `/api/v1/plan` |
| **Slack 연동** | ⚠️ 보류 | Slack 메시지 전송 | ❌ | - (HTTPS 필요) |
| **Tools (Function Calling)** | ✅ 완료 | Gmail, Drive, Notion, Slack | ❌ | - |

---

## ⚠️ 기획 대비 부족한 부분

### 1. **에이전트 기반 모듈 라우팅 시스템 부재** (🔥 최우선)

#### 현재 문제:
```
사용자 → 챗봇 엔드포인트 (/chatbot/message)
         ↓
       GPT-4o가 단순 대화만 처리
         ↓
       다른 모듈들이 독립적으로 존재 (연결 안 됨)
```

#### 예상 플로우 (구현 필요):
```
사용자: "11월 업무 내용과 KPI 알려줘"
         ↓
   [에이전트 라우터] (LLM 기반 의도 분석)
         ↓
    ┌─────────┴─────────┐
    ↓                   ↓
[Monthly Report]     [KPI 검색]
    ↓                   ↓
   결과 조합 → 사용자에게 반환
```

**해결 방안:**
- `IntentRouter` (이미 구현됨)를 챗봇에 통합
- LLM이 사용자 질문을 분석하여 적절한 모듈 호출
- Function Calling 방식으로 모듈들을 tool로 등록

---

### 2. **업무 매뉴얼 RAG 모듈 미구현**

#### 기획서:
- HR 메뉴얼 (✅ 구현됨)
- **업무 매뉴얼** (❌ 미구현)
- 보고서 작성 (✅ 구현됨)

#### 해결 방안:
- HR RAG와 동일한 구조로 `업무 매뉴얼 RAG` 추가
- 업무 프로세스, 가이드 문서를 ChromaDB에 임베딩
- 별도 컬렉션으로 분리하여 관리

---

### 3. **TTS (음성 합성) 미통합**

#### 현재:
- `backend/app/domain/scripts/tts_openai_test.py` 테스트 코드만 존재
- 프론트엔드와 통합 안 됨

#### 해결 방안:
- ChatService에 TTS 옵션 추가
- `/chatbot/message` 엔드포인트에 `enable_tts=true` 파라미터 추가
- OpenAI TTS API 호출 → base64 인코딩 → 프론트엔드로 전송
- 프론트엔드에서 `<audio>` 태그로 재생

---

### 4. **통합 검색 시스템 부족**

#### 현재:
- `search/intent_router.py` 있음 (daily, weekly, monthly 등 의도 분류)
- `search/retriever.py` 있음 (RAG 검색 로직)
- **BUT**: 챗봇과 통합 안 됨

#### 해결 방안:
- 챗봇에서 사용자 질문을 IntentRouter로 분석
- 의도에 따라 적절한 retriever 호출
- 검색 결과를 GPT-4o에 context로 전달

---

## 🎯 우선순위별 개선 작업

### **Priority 1: 에이전트 기반 챗봇 통합** (🔥 핵심)

#### 작업 내용:
1. **ChatService에 에이전트 라우터 통합**
   - IntentRouter를 ChatService에 추가
   - 사용자 메시지를 의도 분석 → 적절한 모듈 호출
   
2. **모듈들을 Function Calling Tool로 등록**
   ```python
   # 예시
   {
       "name": "generate_brainstorming",
       "description": "아이디어 생성이 필요할 때 호출",
       "parameters": {...}
   },
   {
       "name": "search_hr_manual",
       "description": "인사 규정 문의 시 호출",
       "parameters": {...}
   },
   {
       "name": "create_daily_report",
       "description": "일일 보고서 작성 시 호출",
       "parameters": {...}
   }
   ```

3. **통합 플로우 구현**
   ```
   사용자 메시지 입력
         ↓
   IntentRouter: 의도 분석
         ↓
   GPT-4o with Function Calling
         ↓
   적절한 모듈 tool 호출
         ↓
   결과를 GPT-4o가 자연스럽게 정리
         ↓
   사용자에게 응답
   ```

#### 예상 구현 시간:
- 2~3일 (모듈별 adapter 함수 작성 + 테스트)

---

### **Priority 2: 업무 매뉴얼 RAG 추가**

#### 작업 내용:
1. `backend/app/domain/rag/WorkManual/` 폴더 생성
2. HR RAG 코드 복사 후 수정
   - `vector_store.py` (ChromaDB 컬렉션명: `work_manual`)
   - `retriever.py` (검색 로직)
   - `schemas.py` (요청/응답 스키마)
3. 업무 매뉴얼 문서 수집 및 임베딩
4. API 엔드포인트 추가: `/api/v1/rag/work-manual/search`

#### 예상 구현 시간:
- 1~2일 (HR RAG 템플릿 재사용 가능)

---

### **Priority 3: TTS 통합**

#### 작업 내용:
1. **백엔드: TTS 서비스 추가**
   ```python
   # backend/app/domain/chatbot/tts_service.py
   class TTSService:
       def text_to_speech(self, text: str) -> bytes:
           """OpenAI TTS API 호출"""
           response = openai.audio.speech.create(
               model="tts-1",
               voice="shimmer",
               input=text
           )
           return response.content
   ```

2. **API 엔드포인트 수정**
   ```python
   # /chatbot/message 응답에 audio 필드 추가
   {
       "assistant_message": "안녕하세요",
       "audio": "base64_encoded_audio" (선택)
   }
   ```

3. **프론트엔드: Audio 재생**
   ```javascript
   // renderer/chat/chatUI.js
   function playAudio(base64Audio) {
       const audio = new Audio(`data:audio/mp3;base64,${base64Audio}`);
       audio.play();
   }
   ```

#### 예상 구현 시간:
- 1일 (OpenAI TTS API 사용)

---

### **Priority 4: Slack 연동 (보류 → HTTPS 후)**

#### 현재 이슈:
- Slack Webhook은 HTTPS 필요
- 로컬 개발 환경에서는 테스트 어려움

#### 해결 방안:
- ngrok 또는 로컬 터널링 도구 사용 (개발용)
- 프로덕션 배포 후 정식 연동

---

## 🛠️ 구현 로드맵 (우선순위 순)

### Week 1: 에이전트 통합 (🔥 최우선)
```
Day 1-2: IntentRouter + ChatService 통합
Day 3-4: 모듈별 Function Calling Tool 작성
Day 5: 통합 테스트 및 디버깅
```

### Week 2: RAG 확장
```
Day 1-2: 업무 매뉴얼 RAG 구현
Day 3: 통합 검색 시스템 개선
Day 4-5: 테스트 및 문서화
```

### Week 3: TTS 통합
```
Day 1: TTS 서비스 구현
Day 2: API 엔드포인트 수정
Day 3: 프론트엔드 audio 재생
Day 4-5: UX 개선 (음성 속도, 볼륨 조절)
```

### Week 4: 최적화 & 문서화
```
Day 1-2: 성능 최적화 (캐싱, 병렬 처리)
Day 3-4: API 문서 자동 생성 (Swagger)
Day 5: 발표 자료 준비
```

---

## 📐 에이전트 아키텍처 제안

### 현재 구조:
```
Frontend → API Gateway → 각 모듈 독립 엔드포인트
                          ├─ /chatbot
                          ├─ /brainstorming
                          ├─ /therapy
                          ├─ /daily-report
                          └─ /rag
```

### 개선된 구조 (에이전트 기반):
```
Frontend → API Gateway → [Chatbot Agent]
                              ↓
                        IntentRouter (LLM)
                              ↓
                    ┌─────────┴─────────┐
                    ↓                   ↓
            [Module Registry]    [Function Calling]
                    ↓                   ↓
      ┌─────────────┼─────────────┐
      ↓             ↓             ↓
Brainstorming   Therapy    Daily Report
      ↓             ↓             ↓
   HR RAG      Work RAG      KPI Search
      ↓             ↓             ↓
    결과 조합 → GPT-4o → 자연스러운 응답
```

### 핵심 컴포넌트:

#### 1. **IntentRouter** (의도 분석기)
- 사용자 질문을 LLM으로 분석
- 의도(intent) 추출: `daily`, `weekly`, `kpi`, `brainstorming`, `therapy`, `hr_manual`, `work_manual` 등

#### 2. **ModuleRegistry** (모듈 레지스트리)
```python
MODULE_REGISTRY = {
    "brainstorming": BrainstormingService,
    "therapy": TherapyService,
    "daily_report": DailyReportService,
    "hr_rag": HRRAGService,
    "work_rag": WorkRAGService,
    "kpi_search": KPIService,
}
```

#### 3. **AgentOrchestrator** (에이전트 오케스트레이터)
- IntentRouter 결과를 받아서
- 적절한 모듈 호출
- 결과를 GPT-4o에게 전달하여 자연스럽게 정리

---

## 🔧 구현 예시: 에이전트 통합

### `backend/app/domain/chatbot/agent.py` (신규 파일)

```python
"""
Chatbot Agent
사용자 질문을 분석하여 적절한 모듈로 라우팅하는 에이전트
"""

from typing import Dict, Any, Optional
from app.domain.search.intent_router import IntentRouter
from app.domain.brainstorming.service import BrainstormingService
from app.domain.therapy.service import TherapyService
from app.domain.daily.service import DailyReportService
# ... 다른 서비스 import

class ChatbotAgent:
    """통합 에이전트"""
    
    def __init__(self):
        self.intent_router = IntentRouter()
        self.modules = {
            "brainstorming": BrainstormingService(),
            "therapy": TherapyService(),
            "daily": DailyReportService(),
            # ... 다른 모듈들
        }
    
    async def process_query(self, user_query: str, session_id: str) -> Dict[str, Any]:
        """
        사용자 질문 처리
        
        1. 의도 분석
        2. 적절한 모듈 호출
        3. 결과 반환
        """
        # 1. 의도 분석
        intent_result = self.intent_router.route(user_query)
        
        # 2. 모듈 호출
        if intent_result.intent == "brainstorming":
            result = await self.modules["brainstorming"].generate_ideas(...)
        elif intent_result.intent == "therapy":
            result = self.modules["therapy"].chat(user_query)
        elif intent_result.intent == "daily":
            result = await self.modules["daily"].get_report(...)
        else:
            result = {"error": "모듈을 찾을 수 없습니다"}
        
        return {
            "intent": intent_result.intent,
            "result": result,
            "reason": intent_result.reason
        }
```

### `backend/app/domain/chatbot/service.py` 수정

```python
class ChatService:
    def __init__(self):
        # ... 기존 코드
        self.agent = ChatbotAgent()  # 🔥 에이전트 추가
    
    async def process_message(self, session_id: str, user_message: str) -> str:
        # 1. 에이전트로 의도 분석 및 모듈 호출
        agent_result = await self.agent.process_query(user_message, session_id)
        
        # 2. 결과가 있으면 GPT-4o에게 자연스럽게 정리 요청
        if agent_result.get("result"):
            prompt = f"""
            사용자 질문: {user_message}
            모듈 실행 결과: {agent_result['result']}
            
            위 결과를 사용자에게 자연스럽게 설명해주세요.
            """
            # GPT-4o 호출...
        
        # 3. 일반 대화는 기존 로직 사용
        else:
            # 기존 ChatService 로직...
```

---

## 📝 추가 개선 사항

### 1. **캐싱 시스템**
- RAG 검색 결과 캐싱 (Redis)
- LLM 응답 캐싱 (동일한 질문 반복 시)

### 2. **스트리밍 응답**
- GPT-4o 스트리밍으로 응답 속도 개선
- 프론트엔드에서 실시간으로 응답 표시

### 3. **사용자 피드백 시스템**
- 응답에 👍/👎 버튼 추가
- 피드백 데이터로 프롬프트 개선

### 4. **멀티모달 지원**
- 이미지 업로드 → GPT-4o-vision으로 분석
- PDF 업로드 → 자동 임베딩 후 RAG 검색

---

## 🎯 요약: 다음 단계

### 즉시 시작 가능한 작업 (Priority 1):
1. ✅ **에이전트 통합**: IntentRouter + ChatService 연결
2. ✅ **Function Calling**: 모듈들을 tool로 등록
3. ✅ **통합 테스트**: 사용자 시나리오별 테스트

### 중기 작업 (Priority 2):
4. ✅ **업무 매뉴얼 RAG** 추가
5. ✅ **TTS 통합** (백엔드 + 프론트엔드)

### 장기 작업 (Priority 3):
6. ⚠️ **Slack 연동** (HTTPS 환경 구축 후)
7. ⚠️ **성능 최적화** (캐싱, 병렬 처리)
8. ⚠️ **멀티모달** 지원

---

**작성 완료!** 🎉

**궁금한 점이나 추가 논의가 필요한 부분이 있으면 알려주세요!** 😊

