# 상담(Therapy) 시스템 전체 플로우 문서

## 📋 개요
백엔드 서버 시작부터 프론트엔드 채팅 입력 및 답변 수신까지의 전체 알고리즘 순서도와 파일 간 호출 관계를 정리한 문서입니다.

---

## 🔄 전체 플로우 순서도

```
[1] 백엔드 서버 시작
    ↓
[2] FastAPI 앱 초기화 (main.py)
    ↓
[3] Vector DB 자동 생성 프로세스 (automatic_save.py)
    ├─ [3-1] 청크 파일 생성 (create_chunk_files.py)
    │   └─ PDF → 텍스트 추출 → 의미 단위 청킹 → JSON 저장
    ├─ [3-2] OpenAI 임베딩 생성 (create_openai_embeddings.py)
    │   └─ 청크 파일 로드 → OpenAI API 호출 → 임베딩 벡터 생성 → JSON 저장
    └─ [3-3] Vector DB 저장 (save_to_vectordb.py)
        └─ 임베딩 파일 로드 → ChromaDB 저장 → 컬렉션 생성
    ↓
[4] API 라우터 등록 (router.py)
    ↓
[5] TherapyService 싱글톤 초기화 (therapy.py)
    ↓
[6] RAGTherapySystem 초기화 (service.py → rag_therapy.py)
    ↓
[7] 페르소나 생성 (rag_therapy.py)
    ↓
[8] 프론트엔드 사용자 입력
    ↓
[9] 키워드 감지 (chatService.js)
    ↓
[10] Therapy API 호출 (chatService.js)
    ↓
[11] API 엔드포인트 처리 (therapy.py)
    ↓
[12] TherapyService.chat() 호출 (service.py)
    ↓
[13] RAGTherapySystem.chat() 호출 (rag_therapy.py)
    ↓
[14] Vector DB 검색 및 답변 생성
    ↓
[15] 응답 반환 (프론트엔드)
    ↓
[16] UI에 표시 (chatPanel.js)
```

---

## 📁 파일별 상세 호출 경로

### 1️⃣ 백엔드 서버 시작

**파일**: `backend/app/main.py`

#### 서버 시작 시 실행 순서:

```35:58:backend/app/main.py
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    애플리케이션 시작/종료 시 실행되는 함수
    """
    # 시작 시
    print("🚀 Starting Virtual Desk Assistant API...")
    print(f"📊 Database: {settings.DATABASE_URL}")
    
    # 데이터베이스 테이블 생성 (개발용)
    # 프로덕션에서는 Alembic 마이그레이션 사용
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created")
    
    # Vector DB 자동 생성 (심리 상담 시스템용)
    try:
        success = automatic_save()
        if success:
            pass
        else:
            print("⚠️  Therapy Vector DB initialization failed")
    except Exception as e:
        print(f"⚠️  Therapy Vector DB initialization error: {e}")
    
    yield
    
    # 종료 시
    print("👋 Shutting down...")
```

**라우터 등록**:
```83:84:backend/app/main.py
# API 라우터 등록
app.include_router(api_router, prefix=settings.API_PREFIX)
```

**호출 경로**:
- `main.py:51` → `backend/councel/sourcecode/automatic_save.py:232` (automatic_save 함수 호출)
- `main.py:84` → `backend/app/api/v1/router.py:103` (Therapy 라우터 등록)

---

### 2️⃣ Vector DB 자동 생성 프로세스

**파일**: `backend/councel/sourcecode/automatic_save.py`

#### 전체 프로세스 실행:

```200:224:backend/councel/sourcecode/automatic_save.py
    # 전체 프로세스 실행
    def run(self) -> bool:

        print("\n" + "="*60)
        print("자동 저장 프로세스 시작")
        print("="*60)
        
        try:
            # Step 1: 청크 파일 생성
            if not self.step1_create_chunks():
                raise Exception("청크 파일 생성 실패")
            
            # Step 2: 임베딩 파일 생성
            if not self.step2_create_embeddings():
                raise Exception("임베딩 파일 생성 실패")
            
            # Step 3: Vector DB 저장
            if not self.step3_save_to_vectordb():
                raise Exception("Vector DB 저장 실패")
            
            # 성공
            print("\n" + "="*60)
            print("전체 프로세스 완료!")
            print("="*60)
            return True
```

#### Step 1: 청크 파일 생성

**파일**: `backend/councel/sourcecode/automatic_save/create_chunk_files.py`

**프로세스**:
1. `backend/councel/dataset/adler/` 폴더의 PDF 파일 읽기
2. PyMuPDF(fitz)로 PDF에서 텍스트 추출
3. tiktoken을 사용하여 토큰 수 계산
4. 의미 단위로 청킹 (최대 500 토큰, 20% overlap)
5. `backend/councel/dataset/adler/chunkfiles/` 폴더에 JSON 파일로 저장

**호출 경로**:
- `automatic_save.py:88` → `automatic_save.py:106` (step1_create_chunks)
- `automatic_save.py:106` → `automatic_save/create_chunk_files.py` (스크립트 실행)

#### Step 2: OpenAI 임베딩 생성

**파일**: `backend/councel/sourcecode/automatic_save/create_openai_embeddings.py`

**프로세스**:
1. `chunkfiles/` 폴더의 JSON 파일 로드
2. OpenAI API 호출 (`text-embedding-3-large` 모델 사용)
3. 각 청크에 대한 임베딩 벡터 생성
4. 배치 처리 (100개씩)
5. `backend/councel/dataset/adler/embeddings/` 폴더에 JSON 파일로 저장

**호출 경로**:
- `automatic_save.py:119` → `automatic_save.py:137` (step2_create_embeddings)
- `automatic_save.py:137` → `automatic_save/create_openai_embeddings.py` (스크립트 실행)

#### Step 3: Vector DB 저장

**파일**: `backend/councel/sourcecode/automatic_save/save_to_vectordb.py`

**프로세스**:
1. `embeddings/` 폴더의 JSON 파일 로드
2. ChromaDB 클라이언트 초기화
3. `vector_adler` 컬렉션 생성 (없는 경우)
4. 임베딩 벡터, 텍스트, 메타데이터를 ChromaDB에 저장
5. `backend/councel/vector_db/` 폴더에 영구 저장

**호출 경로**:
- `automatic_save.py:150` → `automatic_save.py:188` (step3_save_to_vectordb)
- `automatic_save.py:188` → `automatic_save/save_to_vectordb.py` (스크립트 실행)

**참고사항**:
- 각 단계는 파일/폴더 존재 여부를 확인하여 이미 생성된 경우 건너뜀
- Vector DB에 이미 데이터가 있으면 저장 단계를 건너뜀
- 오류 발생 시 롤백 기능 제공

---

### 3️⃣ API 라우터 등록

---

### 3️⃣ API 라우터 등록

**파일**: `backend/app/api/v1/router.py`

```102:107:backend/app/api/v1/router.py
# Therapy 엔드포인트
api_router.include_router(
    therapy_router,
    prefix="/therapy",
    tags=["Therapy"]
)
```

**호출 경로**:
- `router.py:15` → `backend/app/api/v1/endpoints/therapy.py:16` (router import)
- `router.py:104` → `backend/app/api/v1/endpoints/therapy.py:16` (router 등록)

---

### 4️⃣ Therapy 엔드포인트 초기화

**파일**: `backend/app/api/v1/endpoints/therapy.py`

#### TherapyService 싱글톤 인스턴스 생성:

```18:19:backend/app/api/v1/endpoints/therapy.py
# TherapyService 싱글톤 인스턴스
therapy_service = TherapyService()
```

**호출 경로**:
- `therapy.py:19` → `backend/app/domain/therapy/service.py:28` (TherapyService.__new__)
- `therapy.py:19` → `backend/app/domain/therapy/service.py:33` (TherapyService.__init__)

---

### 5️⃣ TherapyService 초기화

**파일**: `backend/app/domain/therapy/service.py`

#### 싱글톤 패턴으로 인스턴스 생성:

```24:28:backend/app/domain/therapy/service.py
    # 심리 상담 시스템 인스턴스 생성
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
```

#### RAGTherapySystem 초기화:

```30:44:backend/app/domain/therapy/service.py
    # 시스템 초기화 함수
    def __init__(self):

        # RAG 심리 상담 시스템이 없으면 초기화
        if self._rag_system is None:
            # Vector DB 경로 설정
            base_dir = Path(__file__).parent.parent.parent.parent
            vector_db_dir = base_dir / "councel" / "vector_db"
            
            try:
                # RAG 상담 시스템 초기화
                self._rag_system = RAGTherapySystem(str(vector_db_dir))
            except Exception as e:
                print(f"RAG 심리 상담 시스템 초기화 실패: {e}")
                self._rag_system = None
```

**호출 경로**:
- `service.py:42` → `backend/councel/sourcecode/persona/rag_therapy.py:44` (RAGTherapySystem.__init__)

---

### 6️⃣ RAGTherapySystem 초기화

**파일**: `backend/councel/sourcecode/persona/rag_therapy.py`

#### 초기화 과정:

```44:91:backend/councel/sourcecode/persona/rag_therapy.py
    # 초기화 함수
    def __init__(self, vector_db_path: str):

        # Vector DB 경로 설정
        self.db_path = Path(vector_db_path)
        
        # Vector DB 존재 확인
        if not self.db_path.exists():
            raise FileNotFoundError(f"Vector DB 경로가 존재하지 않습니다") # 나중에 삭제 예정
        
        # ChromaDB 클라이언트 초기화
        self.client = chromadb.PersistentClient(path=str(self.db_path))
        
        # 컬렉션 이름 (save_to_vectordb.py와 동일)
        self.collection_name = "vector_adler"
        
        # OpenAI 클라이언트 초기화
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY가 환경 변수에 설정되지 않았습니다.")
        self.openai_client = OpenAI(api_key=api_key)
        
        # 컬렉션 로드
        try:
            self.collection = self.client.get_collection(name=self.collection_name)
        except Exception as e:
            raise ValueError(f"컬렉션 '{self.collection_name}'을 찾을 수 없습니다: {e}")
        
        # 감정/상담 키워드 목록
        self.counseling_keywords = [
            "힘들어", "상담", "짜증", "우울", "불안", "스트레스", 
            "고민", "걱정", "슬프", "외로", "화나", "답답",
            "counseling", "therapy", "help", "depressed", "anxious"
        ]
        
        # 대화 히스토리 (단기 기억)
        self.chat_history = []
        
        # 로거 초기화 (스코어링 로그 저장용)
        base_dir = Path(__file__).parent.parent.parent  # backend/councel/
        test_dir = base_dir / "test"  # backend/councel/test/
        log_file_prefix = "scoring_log_v2"  # 로그 파일명 (필요시 변경)
        
        self.therapy_logger = TherapyLogger(
            openai_client=self.openai_client,
            log_dir=str(test_dir),
            log_file_prefix=log_file_prefix
        )
        
        # ========================================
        # 페르소나 생성 방식 선택 (테스트용)
        # ========================================
        # 아래 두 함수 중 하나를 주석 처리하여 사용할 방식을 선택
        
        # [함수 A] RAG 기반 페르소나 생성 (Vector DB + 웹 검색)
        self.adler_persona = self.generate_persona_with_rag()
        
        # [함수 B] 프롬프트 엔지니어링 기반 페르소나 생성 (하드코딩)
        # self.adler_persona = self.generate_persona_with_prompt_engineering()
        
        # ========================================
```

#### 페르소나 생성:

```98:99:backend/councel/sourcecode/persona/rag_therapy.py
        # [함수 A] RAG 기반 페르소나 생성 (Vector DB + 웹 검색)
        self.adler_persona = self.generate_persona_with_rag()
```

**호출 경로**:
- `rag_therapy.py:98` → `rag_therapy.py:107` (generate_persona_with_rag)
- `rag_therapy.py:107` → `rag_therapy.py:177` (_generate_persona_from_rag)

---

### 7️⃣ 프론트엔드 사용자 입력

**파일**: `renderer/chat/chatPanel.js`

#### 메시지 전송 핸들러:

```78:118:renderer/chat/chatPanel.js
async function handleSendMessage() {
  const text = chatInput.value.trim();
  
  if (!text) return;
  
  // 사용자 메시지 추가
  addMessage('user', text);
  
  // 입력창 초기화
  chatInput.value = '';
  
  // 버튼 비활성화 (응답 대기)
  sendBtn.disabled = true;
  sendBtn.textContent = '...';
  
  try {
    // AI 응답 받기
    const response = await callChatModule(text);
    
    // 응답 타입에 따라 처리
    if (response.type === 'task_recommendations') {
      // 추천 업무 카드 UI 표시
      addTaskRecommendations(response.data);
    } else if (response.type === 'therapy') {
      // 심리 상담 응답 (아들러 페르소나)
      addTherapyMessage(response.data, response.mode);
    } else if (response.type === 'error') {
      addMessage('assistant', response.data);
    } else {
      // 일반 텍스트 응답
      addMessage('assistant', response.data);
    }
  } catch (error) {
    console.error('❌ 채팅 오류:', error);
    addMessage('assistant', '죄송합니다. 오류가 발생했습니다. 😢');
  } finally {
    // 버튼 다시 활성화
    sendBtn.disabled = false;
    sendBtn.textContent = '전송';
  }
}
```

**호출 경로**:
- `chatPanel.js:95` → `renderer/chat/chatService.js:78` (callChatModule)

---

### 8️⃣ 키워드 감지 및 라우팅

**파일**: `renderer/chat/chatService.js`

#### 심리 상담 키워드 확인:

```61:71:renderer/chat/chatService.js
function isTherapyRelated(text) {
  const therapyKeywords = [
    '힘들어', '상담', '짜증', '우울', '불안', '스트레스',
    '고민', '걱정', '슬프', '외로', '화나', '답답',
    '아들러', 'adler', 'counseling', 'therapy', 'help',
    'depressed', 'anxious', '심리'
  ];
  
  const lowerText = text.toLowerCase();
  return therapyKeywords.some(keyword => lowerText.includes(keyword));
}
```

#### 메시지 라우팅:

```78:94:renderer/chat/chatService.js
export async function callChatModule(userText) {
  console.log('📨 사용자 메시지:', userText);
  
  // 심리 상담 관련 키워드가 있으면 Therapy API 호출
  if (isTherapyRelated(userText)) {
    console.log('🎭 심리 상담 모드 감지');
    return await sendTherapyMessage(userText);
  }
  
  // "오늘 뭐할지 추천" 등의 키워드가 있으면 TodayPlan API 호출
  if (userText.includes('오늘') && (userText.includes('추천') || userText.includes('뭐할'))) {
    return await getTodayPlan();
  }
  
  // 챗봇 API 호출
  return await sendChatbotMessage(userText);
}
```

**호출 경로**:
- `chatService.js:82` → `chatService.js:61` (isTherapyRelated)
- `chatService.js:84` → `chatService.js:101` (sendTherapyMessage)

---

### 9️⃣ Therapy API 호출

**파일**: `renderer/chat/chatService.js`

#### API 요청 전송:

```101:133:renderer/chat/chatService.js
async function sendTherapyMessage(userText) {
  try {
    const response = await fetch(`${API_BASE_URL}/therapy/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        message: userText
      })
    });
    
    if (!response.ok) {
      throw new Error(`심리 상담 API 호출 실패: ${response.status}`);
    }
    
    const result = await response.json();
    console.log('🎭 아들러 상담사 응답:', result);
    
    return {
      type: 'therapy',
      data: result.answer,
      mode: result.mode,
      used_chunks: result.used_chunks
    };
  } catch (error) {
    console.error('❌ 심리 상담 API 오류:', error);
    return {
      type: 'error',
      data: '심리 상담 시스템에 연결할 수 없습니다. 백엔드 서버를 확인해주세요.'
    };
  }
}
```

**API 엔드포인트**: `POST http://localhost:8000/api/v1/therapy/chat`

**호출 경로**:
- `chatService.js:103` → `backend/app/api/v1/endpoints/therapy.py:38` (chat_therapy 엔드포인트)

---

### 🔟 API 엔드포인트 처리

**파일**: `backend/app/api/v1/endpoints/therapy.py`

#### 요청 처리:

```33:64:backend/app/api/v1/endpoints/therapy.py
# 심리 상담 채팅 엔드포인트
@router.post("/chat", response_model=TherapyResponse)
async def chat_therapy(request: TherapyRequest):

    try:
        # 서비스 사용 가능 여부 확인
        if not therapy_service.is_available():
            raise HTTPException(
                status_code=503, 
                detail="심리 상담 시스템이 현재 사용 불가능합니다. Vector DB를 확인해주세요."
            )
        
        # 상담 진행 (스코어링 옵션 전달)
        response = therapy_service.chat(
            request.message, 
            enable_scoring=request.enable_scoring
        )
        
        return TherapyResponse(
            answer=response["answer"],
            mode=response["mode"],
            used_chunks=response.get("used_chunks", []),
            continue_conversation=response.get("continue_conversation", True)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"상담 처리 중 오류가 발생했습니다: {str(e)}"
        )
```

**호출 경로**:
- `therapy.py:50` → `backend/app/domain/therapy/service.py:48` (is_available)
- `therapy.py:57` → `backend/app/domain/therapy/service.py:57` (chat)

---

### 1️⃣1️⃣ TherapyService.chat() 호출

**파일**: `backend/app/domain/therapy/service.py`

#### 상담 처리:

```52:80:backend/app/domain/therapy/service.py
    # 상담 응답 생성
    # 사용자의 입력을 받아 응답 생성 -> RAG 심리 상담 시스템의 chat 함수 호출
    def chat(self, user_input: str, enable_scoring: bool = True) -> Dict[str, Any]:

        # 상담 시스템 사용 가능 여부가 불가능하면 return 반환
        if not self.is_available():
            return {
                "answer": "죄송합니다. 심리 상담 시스템이 현재 사용 불가능합니다.",
                "used_chunks": [],
                "mode": "error",
                "continue_conversation": False,
                "scoring": None,
            }
        
        try:
            # RAG 시스템으로 상담 진행 (스코어링 옵션 전달)
            response = self._rag_system.chat(user_input, enable_scoring=enable_scoring)
            return response
        except Exception as e:
            print(f"상담 처리 중 오류: {e}")
            import traceback
            traceback.print_exc()
            return {
                "answer": f"죄송합니다. 상담 처리 중 오류가 발생했습니다: {str(e)}",
                "used_chunks": [],
                "mode": "error",
                "continue_conversation": True,
                "scoring": None,
            }
```

**호출 경로**:
- `service.py:84` → `backend/councel/sourcecode/persona/rag_therapy.py:560` (RAGTherapySystem.chat)

---

### 1️⃣2️⃣ RAGTherapySystem.chat() - 핵심 로직

**파일**: `backend/councel/sourcecode/persona/rag_therapy.py`

#### 상담 처리 메인 함수:

```536:580:backend/councel/sourcecode/persona/rag_therapy.py
    # 상담 함수(사용자 입력 -> 답변 생성 + 품질 평가)
    def chat(self, user_input: str, enable_scoring: bool = True) -> Dict[str, Any]:

        # 종료 키워드 확인 (exit, 고마워, 끝)
        user_input_lower = user_input.strip().lower()
        exit_keywords = ["exit", "고마워", "끝"]
        if any(keyword in user_input_lower for keyword in exit_keywords):
            return {
                "answer": "상담을 마무리하겠습니다. 오늘 함께 시간을 보내주셔서 감사합니다. 언제든 다시 찾아주세요.",
                "used_chunks": [],
                "used_chunks_detailed": [],
                "mode": "exit",
                "continue_conversation": False
            }
        
        # 1. 입력 분류
        input_type = self.classify_input(user_input)
        
        # 2. 영어로 번역 (Vector DB 검색용)
        english_input = self.translate_to_english(user_input)
        
        # 3. 입력 유형에 따른 처리 (모든 모드에서 아들러 페르소나 사용)
        retrieved_chunks = self.retrieve_chunks(english_input, n_results=5)
        
        response = self.generate_response_with_persona(user_input, retrieved_chunks, mode=input_type)
        
        # 4. 로그 저장 (TherapyLogger 사용)
        response = self.therapy_logger.log_conversation(
            user_input=user_input,
            response=response,
            retrieved_chunks=retrieved_chunks,
            enable_scoring=enable_scoring
        )
        
        # 대화 히스토리에 추가 (단기 기억)
        self.chat_history.append({
            "user": user_input,
            "assistant": response["answer"]
        })
        
        # 히스토리가 너무 길어지면 오래된 것 제거 (최대 10개 유지)
        if len(self.chat_history) > 10:
            self.chat_history = self.chat_history[-10:]
        
        return response
```

#### 내부 함수 호출 순서:

1. **입력 분류** (`classify_input`):
   - `rag_therapy.py:575` → `rag_therapy.py:326` (classify_input)

2. **영어 번역** (`translate_to_english`):
   - `rag_therapy.py:578` → `rag_therapy.py:294` (translate_to_english)

3. **Vector DB 검색** (`retrieve_chunks`):
   - `rag_therapy.py:581` → `rag_therapy.py:416` (retrieve_chunks)
   - `rag_therapy.py:419` → `rag_therapy.py:313` (create_query_embedding)
   - `rag_therapy.py:440` → `rag_therapy.py:348` (rerank_chunks) - Re-ranker 적용

4. **페르소나 기반 답변 생성** (`generate_response_with_persona`):
   - `rag_therapy.py:583` → `rag_therapy.py:471` (generate_response_with_persona)
   - `rag_therapy.py:495` → `rag_therapy.py:447` (summarize_chunk) - 청크 요약

5. **로그 저장** (`therapy_logger.log_conversation`):
   - `rag_therapy.py:586` → `backend/councel/sourcecode/persona/therapy_logger.py` (TherapyLogger)

---

### 1️⃣3️⃣ 답변 생성 상세 과정

#### Vector DB 검색:

```416:443:backend/councel/sourcecode/persona/rag_therapy.py
def retrieve_chunks(self, user_input: str, n_results: int = 5, use_reranker: bool = True) -> List[Dict[str, Any]]:

    # 질문을 임베딩으로 변환
    query_embedding = self.create_query_embedding(user_input)
    
    # 유사도 검색
    results = self.collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results
    )
    
    # 결과 포맷팅
    retrieved_chunks = []
    if results['ids'] and results['ids'][0]:
        for i in range(len(results['ids'][0])):
            chunk = {
                'id': results['ids'][0][i],
                'text': results['documents'][0][i],
                'metadata': results['metadatas'][0][i],
                'distance': results['distances'][0][i] if 'distances' in results else None
            }
            retrieved_chunks.append(chunk)
    
    # Re-ranker 적용
    if use_reranker and retrieved_chunks:
        retrieved_chunks = self.rerank_chunks(user_input, retrieved_chunks)
    
    return retrieved_chunks
```

#### 페르소나 기반 답변 생성:

```471:556:backend/councel/sourcecode/persona/rag_therapy.py
def generate_response_with_persona(self, user_input: str, retrieved_chunks: List[Dict[str, Any]], mode: str = "adler") -> Dict[str, Any]:

    # 검색된 청크가 없는 경우
    # 고민중인건 RAG를 여기에서 사용해서 자가학습 RAG를 만들지 안할지 고민중
    if not retrieved_chunks:
        return {
            "answer": "죄송합니다. 관련된 자료를 찾을 수 없습니다. 다른 질문을 해주시겠어요?",
            "used_chunks": [],
            "used_chunks_detailed": [],
            "continue_conversation": True
        }
    
    # 컨텍스트 구성
    context_parts = []
    used_chunks = []
    used_chunks_detailed = []
    
    for i, chunk in enumerate(retrieved_chunks[:2], 1):  # 상위 2개 청크 사용(3개로 하니까 답변이 너무 길어짐)
        chunk_text = chunk['text']
        source = chunk['metadata'].get('source', '알 수 없음')
        context_parts.append(f"[자료 {i}]\n{chunk_text}\n(출처: {source})")
        used_chunks.append(f"{source}: {chunk_text[:50]}...")
        
        # 상세 청크 정보 (로깅용)
        chunk_summary = self.summarize_chunk(chunk_text)
        used_chunks_detailed.append({
            "chunk_id": chunk['id'],
            "source": source,
            "metadata": chunk['metadata'],
            "summary_kr": chunk_summary,
            "distance": chunk.get('distance')
        })
    
    context = "\n\n".join(context_parts)
    
    # 아들러 페르소나 사용
    persona_prompt = self.adler_persona
    user_message = f"""참고 자료:
                        {context}

                        사용자 질문: {user_input}

                        위 자료를 바탕으로 아들러 개인심리학 관점에서 답변해주세요.
                        격려와 용기를 주는 톤으로, 열등감을 성장의 기회로 재해석하고 사회적 관심을 강조해주세요.

                        **중요: 답변은 1~2문장 이내로 매우 간결하게 작성해주세요.**
                    """
    
    # 대화 히스토리 추가 (단기 기억)
    messages = [{"role": "system", "content": persona_prompt}]
    
    # 최근 2개의 대화만 포함 (컨텍스트 길이 관리)
    for history in self.chat_history[-2:]:
        messages.append({"role": "user", "content": history["user"]})
        messages.append({"role": "assistant", "content": history["assistant"]})
    
    messages.append({"role": "user", "content": user_message})
    
    # OpenAI API 호출
    try:
        response = self.openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.3,  # 낮은 temperature로 일관된 답변 생성
            max_tokens=80  # 답변 길이 제한 (1000 -> 200 -> 100 -> 80)
        )
        
        answer = response.choices[0].message.content.strip()
        
        return {
            "answer": answer,
            "used_chunks": used_chunks,
            "used_chunks_detailed": used_chunks_detailed,
            "mode": mode,
            "continue_conversation": True
        }
    
    except Exception as e:
        print(f"[오류] OpenAI 답변 생성 실패: {e}")
        return {
            "answer": "죄송합니다. 답변 생성 중 오류가 발생했습니다. 다시 시도해주세요.",
            "used_chunks": [],
            "used_chunks_detailed": [],
            "mode": mode,
            "continue_conversation": True
        }
```

---

### 1️⃣4️⃣ 응답 반환 및 UI 표시

#### 응답 반환 경로 (역순):

1. `rag_therapy.py:603` → `service.py:85` (response 반환)
2. `service.py:85` → `therapy.py:57` (response 반환)
3. `therapy.py:62` → `chatService.js:117` (JSON 응답)
4. `chatService.js:120` → `chatPanel.js:95` (response 객체)
5. `chatPanel.js:103` → `chatPanel.js:151` (addTherapyMessage)

#### UI에 표시:

```151:177:renderer/chat/chatPanel.js
function addTherapyMessage(text, mode) {
  // 상태에 저장
  messages.push({ role: 'therapy', text, mode });
  
  // DOM에 추가
  const messageDiv = document.createElement('div');
  messageDiv.className = 'message assistant therapy';
  
  // 아들러 아이콘 추가
  const icon = document.createElement('div');
  icon.className = 'therapy-icon';
  icon.textContent = '🎭';
  icon.title = '아들러 심리 상담사';
  
  const bubble = document.createElement('div');
  bubble.className = 'bubble therapy-bubble';
  bubble.textContent = text;
  
  messageDiv.appendChild(icon);
  messageDiv.appendChild(bubble);
  messagesContainer.appendChild(messageDiv);
  
  // 스크롤을 맨 아래로
  messagesContainer.scrollTop = messagesContainer.scrollHeight;
  
  console.log(`🎭 [아들러 상담사 - ${mode}]: ${text}`);
}
```

---

## 📊 호출 체인 요약표

| 순서 | 출발 파일:줄 | 도착 파일:줄 | 설명 |
|------|-------------|-------------|------|
| 1 | `main.py:51` | `automatic_save.py:232` | automatic_save 함수 호출 |
| 2 | `automatic_save.py:209` | `create_chunk_files.py` | Step 1: 청크 파일 생성 |
| 3 | `automatic_save.py:213` | `create_openai_embeddings.py` | Step 2: 임베딩 생성 |
| 4 | `automatic_save.py:217` | `save_to_vectordb.py` | Step 3: Vector DB 저장 |
| 5 | `main.py:84` | `router.py:103` | Therapy 라우터 등록 |
| 6 | `router.py:15` | `therapy.py:16` | router import |
| 7 | `therapy.py:19` | `service.py:25` | TherapyService 싱글톤 생성 |
| 8 | `therapy.py:19` | `service.py:31` | TherapyService 초기화 |
| 9 | `service.py:41` | `rag_therapy.py:45` | RAGTherapySystem 초기화 |
| 10 | `rag_therapy.py:99` | `rag_therapy.py:112` | 페르소나 생성 시작 |
| 11 | `rag_therapy.py:112` | `rag_therapy.py:181` | RAG 기반 페르소나 생성 |
| 12 | `chatPanel.js:259` | `chatService.js:313` | 사용자 메시지 라우팅 |
| 13 | `chatService.js:317` | `chatService.js:297` | 키워드 감지 |
| 14 | `chatService.js:319` | `chatService.js:345` | Therapy API 호출 |
| 15 | `chatService.js:347` | `therapy.py:35` | API 엔드포인트 도달 |
| 16 | `therapy.py:39` | `service.py:47` | 서비스 사용 가능 여부 확인 |
| 17 | `therapy.py:46` | `service.py:54` | chat() 호출 |
| 18 | `service.py:68` | `rag_therapy.py:537` | RAGTherapySystem.chat() 호출 |
| 19 | `rag_therapy.py:552` | `rag_therapy.py:329` | 입력 분류 |
| 20 | `rag_therapy.py:555` | `rag_therapy.py:298` | 영어 번역 |
| 21 | `rag_therapy.py:558` | `rag_therapy.py:420` | Vector DB 검색 |
| 22 | `rag_therapy.py:423` | `rag_therapy.py:316` | 임베딩 생성 |
| 23 | `rag_therapy.py:444` | `rag_therapy.py:352` | Re-ranker 적용 |
| 24 | `rag_therapy.py:560` | `rag_therapy.py:449` | 답변 생성 |
| 25 | `rag_therapy.py:473` | `rag_therapy.py:586` | 청크 요약 |
| 26 | `rag_therapy.py:580` | `service.py:69` | 응답 반환 |
| 27 | `service.py:69` | `therapy.py:51` | 응답 반환 |
| 28 | `therapy.py:51` | `chatService.js:361` | JSON 응답 |
| 29 | `chatService.js:364` | `chatPanel.js:259` | response 객체 반환 |
| 30 | `chatPanel.js:267` | `chatPanel.js:151` | UI에 표시 |

---

## 🔑 주요 컴포넌트 설명

### 1. **TherapyService** (싱글톤)
- 위치: `backend/app/domain/therapy/service.py`
- 역할: RAGTherapySystem을 래핑하여 FastAPI에서 사용 가능하도록 함
- 초기화: 서버 시작 시 한 번만 실행

### 2. **RAGTherapySystem** (핵심 로직)
- 위치: `backend/councel/sourcecode/persona/rag_therapy.py`
- 역할: 
  - Vector DB 검색
  - 페르소나 기반 답변 생성
  - 대화 히스토리 관리
  - 스코어링 로깅

### 3. **페르소나 시스템**
- RAG 기반 동적 생성: Vector DB + 웹 검색으로 아들러 페르소나 생성
- 하드코딩 대체: 생성 실패 시 기본 페르소나 사용

### 4. **Vector DB 검색**
- ChromaDB 사용
- 컬렉션: `vector_adler`
- Re-ranker: 검색 결과 재정렬로 관련성 향상

### 5. **프론트엔드 라우팅**
- 키워드 기반 자동 라우팅
- Therapy 키워드 감지 시 자동으로 `/therapy/chat` API 호출

---

## 📝 참고사항

1. **Vector DB 초기화**: 서버 시작 시 `automatic_save()` 함수가 실행되어 다음 순서로 Vector DB를 생성합니다:
   - PDF 파일에서 텍스트 추출 및 청킹
   - OpenAI API를 사용한 임베딩 생성
   - ChromaDB에 저장
   - 이미 파일/데이터가 존재하면 해당 단계를 건너뜀

2. **초기화 순서**: 서버 시작 시 TherapyService가 자동으로 초기화되며, RAGTherapySystem도 함께 초기화됩니다.

3. **페르소나 생성**: 초기화 시 한 번만 생성되며, 이후 모든 상담에서 재사용됩니다. RAG 기반 페르소나 생성은 Vector DB 검색과 웹 검색을 통해 동적으로 생성됩니다.

4. **대화 히스토리**: 최대 10개의 대화를 유지하며, 최근 2개만 답변 생성 시 컨텍스트로 사용됩니다.

5. **스코어링**: `enable_scoring` 옵션으로 답변 품질 평가를 활성화할 수 있습니다. 기본값은 `True`입니다.

6. **Re-ranker**: 검색된 청크들을 LLM으로 재정렬하여 관련성을 높입니다.

7. **서버 시작 시간**: Vector DB 초기화와 페르소나 생성으로 인해 서버 시작 시간이 다소 걸릴 수 있습니다.

---

## 🎯 핵심 플로우 요약

```
[사용자 입력] 
  → [키워드 감지] 
  → [Therapy API 호출] 
  → [입력 분류 & 번역] 
  → [Vector DB 검색] 
  → [Re-ranker 적용] 
  → [페르소나 기반 답변 생성] 
  → [로그 저장] 
  → [응답 반환] 
  → [UI 표시]
```

---

**문서 작성일**: 2025-01-28  
**작성자**: AI Assistant  
**버전**: 2.0

**주요 업데이트**:
- Vector DB 자동 생성 프로세스 추가 (청킹 → 임베딩 → 저장)
- 최신 코드 반영 (주석 및 함수명 업데이트)
- 전체 플로우 순서도 개선

