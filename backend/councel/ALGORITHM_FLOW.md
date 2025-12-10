# 상담 시스템 알고리즘 흐름도 및 순서도

## 목차
1. [시스템 초기화 흐름](#시스템-초기화-흐름)
2. [메인 상담 흐름 (chat 함수)](#메인-상담-흐름-chat-함수)
3. [프로토콜 가이드 생성 흐름](#프로토콜-가이드-생성-흐름)
4. [Vector DB 검색 흐름](#vector-db-검색-흐름)
5. [답변 생성 흐름](#답변-생성-흐름)
6. [Self-learning 흐름](#self-learning-흐름)

---

## 시스템 초기화 흐름

### 1. RAGTherapySystem 초기화
**파일**: `backend/councel/sourcecode/rag_therapy.py`  
**함수**: `RAGTherapySystem.__init__` (79-282줄)

#### 1.1 기본 설정
- **79-86줄**: Vector DB 경로 설정 및 존재 확인
- **88-96줄**: ChromaDB 클라이언트 초기화
- **98-99줄**: 컬렉션 이름 설정 ("vector_adler")
- **101-107줄**: OpenAI 클라이언트 초기화 (동기/비동기)
- **109-113줄**: 컬렉션 로드
- **115-227줄**: 상담 키워드 목록 로드
- **229-231줄**: 대화 히스토리 및 사용자별 세션 딕셔너리 초기화

#### 1.2 모듈 초기화
- **248-249줄**: 기본 디렉토리 경로 설정
- **252-257줄**: PersonaManager 초기화
  - → `backend/councel/sourcecode/persona/persona_manager.py:PersonaManager.__init__` (21-52줄)
- **258줄**: adler_persona 저장
- **260-265줄**: SearchEngine 초기화
  - → `backend/councel/sourcecode/persona/search_engine.py:SearchEngine.__init__` (18-26줄)
- **267-271줄**: ResponseGenerator 초기화
  - → `backend/councel/sourcecode/persona/response_generator.py:ResponseGenerator.__init__` (17-24줄)
- **273-277줄**: TherapyProtocol 초기화
  - → `backend/councel/sourcecode/persona/therapy_protocol.py:TherapyProtocol.__init__` (69-92줄)
- **279-280줄**: 백그라운드 작업용 스레드 풀 초기화

### 2. PersonaManager 초기화
**파일**: `backend/councel/sourcecode/persona/persona_manager.py`  
**함수**: `PersonaManager.__init__` (21-52줄)

#### 2.1 기본 설정
- **23-27줄**: OpenAI 클라이언트, 컬렉션, 기본 경로 설정
- **29-32줄**: 캐시 파일 경로 설정
- **34-37줄**: 페르소나 상태 플래그 초기화

#### 2.2 페르소나 로드
- **40줄**: 캐시된 페르소나 로드 시도
  - → `_load_cached_persona` (111-126줄)
- **41-44줄**: 캐시가 있고 유효하면 사용
- **46-52줄**: 캐시가 없으면 기본 페르소나로 시작
  - **47줄**: 기본 페르소나 생성
    - → `_get_default_persona` (107-108줄)
      - → `generate_persona_with_prompt_engineering` (59-104줄)
  - **52줄**: 백그라운드에서 RAG 페르소나 생성 시작
    - → `_start_background_persona_generation` (142-160줄)
      - **148줄**: `_generate_persona_from_rag` 비동기 실행 (223-444줄)

### 3. SearchEngine 초기화
**파일**: `backend/councel/sourcecode/persona/search_engine.py`  
**함수**: `SearchEngine.__init__` (18-26줄)

- **20-23줄**: OpenAI 클라이언트, 컬렉션 설정
- **24-26줄**: 상담 키워드를 set으로 변환 (O(1) 조회 최적화)

### 4. ResponseGenerator 초기화
**파일**: `backend/councel/sourcecode/persona/response_generator.py`  
**함수**: `ResponseGenerator.__init__` (17-24줄)

- **19-22줄**: OpenAI 클라이언트, 상담 키워드 설정
- **23-24줄**: 상담 키워드를 set으로 변환 (O(1) 조회 최적화)

### 5. TherapyProtocol 초기화
**파일**: `backend/councel/sourcecode/persona/therapy_protocol.py`  
**함수**: `TherapyProtocol.__init__` (69-92줄)

- **70-72줄**: OpenAI 클라이언트 설정
- **72줄**: TherapySession 객체 생성
  - → `TherapySession.__init__` (32-41줄)
- **74-92줄**: 상담 단계별 지침 딕셔너리 로드

---

## 메인 상담 흐름 (chat 함수)

### 진입점
**파일**: `backend/councel/sourcecode/rag_therapy.py`  
**함수**: `RAGTherapySystem.chat` (372-542줄)

### 단계 0: 전처리 및 종료 확인
- **374-375줄**: 사용자별 chat_history 가져오기
  - → `_get_user_chat_history` (289-298줄)
- **377-398줄**: 종료 키워드 확인
  - 종료 키워드면:
    - **382-386줄**: 세션 초기화
      - → `_reset_user_session` (301-304줄) 또는 기본 chat_history 초기화
    - **389줄**: therapy_protocol 세션 초기화
      - → `backend/councel/sourcecode/persona/therapy_protocol.py:TherapyProtocol.reset_session` (99-100줄)
    - **391-398줄**: 종료 메시지 반환

### 단계 1: 프로토콜 가이드 생성
- **401-405줄**: 프로토콜 가이드 생성
  - → `backend/councel/sourcecode/persona/therapy_protocol.py:TherapyProtocol.generate_protocol_guidance` (263-304줄)
  - [상세 흐름은 아래 프로토콜 가이드 생성 섹션 참조](#프로토콜-가이드-생성-흐름)

### 단계 2: 입력 분류
- **408줄**: 입력 분류
  - → `backend/councel/sourcecode/persona/response_generator.py:ResponseGenerator.classify_input` (170-189줄)

### 단계 3: Vector DB 검색 조건 판단
- **411줄**: 감정 + 상황 포함 여부 체크
  - → `backend/councel/sourcecode/persona/response_generator.py:ResponseGenerator.has_situation_context` (27-58줄)
- **413-422줄**: RAG 강제 사용 키워드 체크
- **425줄**: Vector DB 검색 조건 결정
  - `should_search_vector_db = has_situation_context OR force_use_rag`

### 단계 4: 프로토콜 정보 준비
- **427-433줄**: 프로토콜 정보 딕셔너리 구성

### 단계 5: Vector DB 검색 분기

#### 경로 A: should_search_vector_db = True
- **436-497줄**: Vector DB 검색 수행

##### 5.1 검색 쿼리 구성
- **438줄**: 기본 검색 쿼리 = user_input
- **439-444줄**: RAG 강제 키워드이고 히스토리에 상황이 있으면
  - **440줄**: 히스토리에 상황 확인
    - → `backend/councel/sourcecode/persona/response_generator.py:ResponseGenerator.has_situation_in_history` (111-138줄)
  - **442줄**: 히스토리에서 상황 추출
    - → `backend/councel/sourcecode/persona/response_generator.py:ResponseGenerator.extract_situation_from_history` (141-167줄)
  - **444줄**: 검색 쿼리 = 히스토리 상황 + 현재 입력

##### 5.2 Multi-step 반복 검색
- **447줄**: Multi-step 반복 검색 실행
  - → `backend/councel/sourcecode/persona/search_engine.py:SearchEngine._iterative_search_with_query_expansion_async` (357-411줄)
  - [상세 흐름은 아래 Vector DB 검색 섹션 참조](#vector-db-검색-흐름)

##### 5.3 최고 유사도 계산
- **452-460줄**: 최고 유사도 계산
  - **459줄**: distance를 similarity로 변환
    - → `backend/councel/sourcecode/persona/search_engine.py:SearchEngine.get_distance_to_similarity` (591-592줄)
      - → `_distance_to_similarity` (91-96줄)

##### 5.4 Threshold 분기
- **462줄**: threshold = 0.7
- **465-475줄**: Case A - 유사도 ≥ 0.7이고 RAG 강제가 아니면
  - **467-473줄**: LLM 단독 답변 생성
    - → `backend/councel/sourcecode/persona/response_generator.py:ResponseGenerator._generate_llm_only_response` (197-363줄)
- **476-497줄**: Case B - 유사도 < 0.7이거나 RAG 강제 키워드면
  - **480-488줄**: RAG 기반 답변 생성
    - → `backend/councel/sourcecode/persona/response_generator.py:ResponseGenerator.generate_response_with_persona` (366-610줄)
  - **495-497줄**: Self-learning (유사도 < 0.7이면)
    - **497줄**: 백그라운드로 Q&A 저장
      - → `_save_qa_to_vectordb_async` (317-369줄)

#### 경로 B: should_search_vector_db = False
- **498-508줄**: Vector DB 검색 없이 LLM 단독 답변
  - **500-506줄**: LLM 단독 답변 생성
    - → `backend/councel/sourcecode/persona/response_generator.py:ResponseGenerator._generate_llm_only_response` (197-363줄)

### 단계 6: 최종 처리
- **510-511줄**: 프로토콜 정보 추가
- **525-540줄**: 대화 히스토리 업데이트
  - **526-529줄**: 현재 대화 추가
  - **532-533줄**: 최대 10개 유지 (초과 시 오래된 것 제거)
  - **536-540줄**: 사용자별 세션 저장
- **542줄**: 응답 반환

---

## 프로토콜 가이드 생성 흐름

### 진입점
**파일**: `backend/councel/sourcecode/persona/therapy_protocol.py`  
**함수**: `TherapyProtocol.generate_protocol_guidance` (263-304줄)

### 단계 1: 세션 상태 업데이트
- **271줄**: 세션 상태 업데이트
  - → `update_session` (95-96줄)
    - → `TherapySession.update_from_history` (44-46줄)

### 단계 2: LLM 기반 상담 단계 선택
- **274줄**: LLM으로 상담 단계 선택
  - → `select_stage_with_llm` (181-260줄)
    - **184-192줄**: 최근 3개 대화 히스토리 컨텍스트 구성
    - **194-216줄**: LLM 프롬프트 구성
    - **218-239줄**: OpenAI API 호출 (비동기 또는 동기)
    - **241줄**: 단계 번호 추출
    - **244-251줄**: TherapyStage로 변환
- **275줄**: 선택된 단계를 세션에 저장

### 단계 3: 프로토콜 선택
- **278줄**: 프로토콜 선택
  - → `select_protocol` (103-121줄)
    - **106-107줄**: 첫 대화면 EAP
    - **109-113줄**: 위기 키워드면 EAP
    - **116-118줄**: 해결책 탐색 키워드면 SFBT
    - **121줄**: 기본은 INTEGRATED
- **279줄**: 선택된 프로토콜을 세션에 저장

### 단계 4: 심각도 평가
- **282줄**: 심각도 평가
  - → `assess_severity` (124-140줄)
    - **127-129줄**: 위기/높음/중간 키워드 정의
    - **133-140줄**: 키워드 매칭으로 심각도 반환
- **283줄**: 평가된 심각도를 세션에 저장

### 단계 5: 단계 가이드라인 가져오기
- **286줄**: 현재 단계 가이드라인 가져오기
  - → `get_stage_guideline` (177-178줄)

### 단계 6: 통합 프롬프트 생성
- **289-295줄**: 통합 프롬프트 생성
  - → `_build_integrated_prompt` (307-370줄)
    - **317줄**: 기본 아들러 페르소나 추가
    - **320-326줄**: 현재 상담 단계 가이드라인 추가
    - **329-336줄**: 위기 상황 대응 (심각도가 critical/high면)
    - **339-368줄**: 답변 구조 추가

### 단계 7: 반환
- **297-304줄**: 프로토콜 가이드 딕셔너리 반환

---

## Vector DB 검색 흐름

### 진입점
**파일**: `backend/councel/sourcecode/persona/search_engine.py`  
**함수**: `SearchEngine._iterative_search_with_query_expansion_async` (357-411줄)

### Step 1: 초기 검색
- **364줄**: 초기 검색 실행
  - → `retrieve_chunks_async` (58-88줄)
    - **61줄**: 임베딩 생성
      - → `create_query_embedding_async` (42-55줄)
    - **64-68줄**: ChromaDB query 실행 (비동기 스레드 풀)
    - **70-80줄**: 결과 포맷팅
    - **83-86줄**: 조건부 Re-ranker 실행
      - **84줄**: 최고 유사도 계산
        - → `_get_max_similarity` (576-588줄)
      - **85줄**: 최고 유사도 < 0.55이면 Re-ranker 실행
        - → `rerank_chunks` (99-180줄)
          - **106-121줄**: 평가 프롬프트 구성
          - **124-157줄**: OpenAI API 호출 (비동기 또는 동기)
          - **160-176줄**: 순위 파싱 및 재정렬

### Step 2: 품질 평가
- **372줄**: 품질 평가
  - → `_evaluate_search_quality` (219-258줄)
    - **230-237줄**: 평균 유사도 계산
      - **234줄**: distance를 similarity로 변환
        - → `_distance_to_similarity` (91-96줄)
    - **239-245줄**: 다양성 점수 계산 (서로 다른 소스 비율)
    - **247-248줄**: 종합 품질 점수 계산 (평균 유사도 70% + 다양성 30%)
    - **251줄**: 개선 필요 여부 판단 (품질 점수 < 0.6)

### Step 3: 반복 검색 (조건부)
- **375줄**: max_iterations > 1이고 품질이 낮으면 반복 검색
- **377-408줄**: while 루프
  - **379-384줄**: 조기 종료 조건 확인
  - **386줄**: iteration 증가
  - **389줄**: 쿼리 확장
    - → `_expand_query_with_llm` (261-329줄, use_llm=False)
      - **264-291줄**: 키워드 기반 확장 (LLM 호출 없음)
  - **394-395줄**: 확장된 쿼리로 재검색 (비동기 병렬 처리)
    - → `retrieve_chunks_async` (58-88줄) 여러 번 병렬 실행
  - **397-401줄**: 새 청크 추가 (중복 제거)
  - **404줄**: 재평가
    - → `_evaluate_search_quality` (219-258줄)
  - **407-408줄**: 품질이 충분히 개선되었으면 중단

### Step 4: 최종 처리
- **411줄**: 최종 처리 및 반환
  - → `_finalize_search_results` (332-354줄)
    - **341줄**: 최고 유사도 계산
      - → `_get_max_similarity` (576-588줄)
    - **342-343줄**: 조건부 Re-ranker 실행
      - → `rerank_chunks` (99-180줄)
    - **346줄**: 상위 n_results개만 반환
    - **347줄**: 품질 평가
      - → `_evaluate_search_quality` (219-258줄)
    - **349-354줄**: 결과 딕셔너리 반환

---

## 답변 생성 흐름

### A. LLM 단독 답변 생성

#### 진입점
**파일**: `backend/councel/sourcecode/persona/response_generator.py`  
**함수**: `ResponseGenerator._generate_llm_only_response` (197-363줄)

#### 단계 1: 프로토콜 통합 페르소나 사용
- **201줄**: 프로토콜 통합 페르소나 사용

#### 단계 2: 감정 맥락 파악
- **205-216줄**: 최근 2개 대화에서 감정 키워드 추출 (set 연산)

#### 단계 3: 히스토리 상황 확인
- **219줄**: 히스토리에 상황 확인
  - → `has_situation_in_history` (111-138줄)
- **223-261줄**: 히스토리에 상황이 있으면
  - **225줄**: 히스토리에서 상황 추출
    - → `extract_situation_from_history` (141-167줄)
  - **228-232줄**: 해결 방법 질문인지 확인
  - **234-255줄**: 해결 방법 질문이면 히스토리 상황 기반 해결 방법 제시 가이던스
  - **257-261줄**: 아니면 상황 인지 후 답변 가이던스

#### 단계 4: 대화 히스토리 구성
- **264줄**: 시스템 메시지 구성
- **267-269줄**: 최근 3개 대화 포함

#### 단계 5: 입력 구체성 확인
- **272줄**: 감정 + 상황 포함 여부 확인
  - → `has_situation_context` (27-58줄)
- **273줄**: 충분히 구체적인지 확인
  - → `is_sufficiently_detailed` (61-108줄)

#### 단계 6: 상황 가이던스 생성
- **276-299줄**: 상황 가이던스 생성
  - 충분히 구체적: 다시 물어보지 않음
  - 구체적이지 않음: 더 자세히 물어봄
  - 상황 없음: 상황 설명 유도

#### 단계 7: 프롬프트 구성
- **302-322줄**: 사용자 메시지 구성
  - 답변 구조: 감정 인정(1문장) + 자연스러운 질문(1~2문장)
- **324줄**: 사용자 메시지 추가

#### 단계 8: OpenAI API 호출
- **327-342줄**: OpenAI API 호출 (비동기 또는 동기)
  - model: gpt-4o-mini
  - temperature: 0.3
  - max_tokens: 180

#### 단계 9: 응답 반환
- **344-353줄**: 응답 딕셔너리 반환

### B. RAG 기반 답변 생성

#### 진입점
**파일**: `backend/councel/sourcecode/persona/response_generator.py`  
**함수**: `ResponseGenerator.generate_response_with_persona` (366-610줄)

#### 단계 1: 검색된 청크 확인
- **371-377줄**: 검색된 청크가 없으면 에러 메시지 반환

#### 단계 2: 컨텍스트 구성
- **380-411줄**: 상위 3개 청크로 컨텍스트 구성
  - **397-398줄**: distance를 similarity로 변환 (distance_to_similarity_func 사용)

#### 단계 3: 감정 키워드 추출
- **414-436줄**: 사용자 입력에서 감정 키워드 추출 (set 연산)

#### 단계 4: 히스토리 상황 확인
- **442줄**: 히스토리에 상황 확인
  - → `has_situation_in_history` (111-138줄)
- **446-484줄**: 히스토리에 상황이 있으면
  - **448줄**: 히스토리에서 상황 추출
    - → `extract_situation_from_history` (141-167줄)
  - **451-455줄**: 해결 방법 질문인지 확인
  - **457-478줄**: 해결 방법 질문이면 히스토리 상황 기반 해결 방법 제시 가이던스
  - **480-484줄**: 아니면 상황 인지 후 답변 가이던스

#### 단계 5: 입력 구체성 확인
- **487줄**: 감정 + 상황 포함 여부 확인
  - → `has_situation_context` (27-58줄)
- **488줄**: 충분히 구체적인지 확인
  - → `is_sufficiently_detailed` (61-108줄)

#### 단계 6: 상황 가이던스 생성
- **492-518줄**: 상황 가이던스 생성

#### 단계 7: 답변 구조 구성
- **520-547줄**: 답변 구조 구성
  - 1단계: 감정 인정 및 공감 (1~2문장)
  - 2단계: 참고 자료 기반 통찰/조언 (2~3문장)
  - 3단계: 자연스러운 질문 또는 다음 단계 제안 (1~2문장)

#### 단계 8: 프롬프트 구성
- **549-561줄**: 사용자 메시지 구성
- **564줄**: 시스템 메시지 구성
- **567-569줄**: 최근 3개 대화 포함
- **571줄**: 사용자 메시지 추가

#### 단계 9: OpenAI API 호출
- **574-590줄**: OpenAI API 호출 (비동기 또는 동기)
  - model: gpt-4o-mini
  - temperature: 0.3
  - max_tokens: 400

#### 단계 10: 응답 반환
- **592-600줄**: 응답 딕셔너리 반환

---

## Self-learning 흐름

### 진입점
**파일**: `backend/councel/sourcecode/rag_therapy.py`  
**함수**: `RAGTherapySystem._save_qa_to_vectordb_async` (317-369줄)

### 단계 1: Q&A 문서 생성
- **323-328줄**: Q&A 문서 딕셔너리 생성
  - user_query, llm_response, timestamp 포함

### 단계 2: JSON 문자열 변환
- **331줄**: Q&A 문서를 JSON 문자열로 변환

### 단계 3: 임베딩 생성
- **334줄**: 사용자 쿼리 임베딩 생성
  - → `backend/councel/sourcecode/persona/search_engine.py:SearchEngine.create_query_embedding_async` (42-55줄)

### 단계 4: 고유 ID 생성
- **337줄**: 고유 ID 생성 (self_learning_ + UUID)

### 단계 5: 중복 체크
- **340-347줄**: 이미 존재하는 ID인지 확인
  - 존재하면 저장하지 않고 반환

### 단계 6: Vector DB에 저장
- **350-365줄**: Vector DB에 저장
  - **351-360줄**: collection.add 실행
  - **361-365줄**: 중복 에러 처리

---

## 주요 알고리즘 특징

### 1. Threshold 기반 RAG 분기
- **유사도 ≥ 0.7**: LLM 단독 답변
- **유사도 < 0.7 또는 RAG 강제 키워드**: RAG + Self-learning

### 2. Multi-step 검색
- 초기 검색 → 품질 평가 → 필요시 쿼리 확장 및 재검색

### 3. 하이브리드 검색
- 벡터 검색 + 감정 키워드 가중치
- final_similarity = base_similarity + emotion_boost

### 4. 조건부 Re-ranker
- 최고 유사도 < 0.55일 때만 실행

### 5. Self-learning
- 유사도 < 0.7인 Q&A를 백그라운드로 Vector DB에 저장

### 6. 프로토콜 통합
- EAP + SFBT 기법 통합
- LLM 기반 단계 선택
- 심각도 평가 및 위기 개입

### 7. 최적화
- 키워드 set 변환 (O(1) 조회)
- 비동기 병렬 처리
- 캐싱 (페르소나 24시간)

---

## 함수 호출 관계도

```
RAGTherapySystem.chat (372줄)
├── _get_user_chat_history (289줄)
├── therapy_protocol.generate_protocol_guidance (401줄)
│   ├── update_session (271줄)
│   │   └── TherapySession.update_from_history (44줄)
│   ├── select_stage_with_llm (274줄)
│   ├── select_protocol (278줄)
│   ├── assess_severity (282줄)
│   ├── get_stage_guideline (286줄)
│   └── _build_integrated_prompt (289줄)
├── response_generator.classify_input (408줄)
├── response_generator.has_situation_context (411줄)
├── search_engine._iterative_search_with_query_expansion_async (447줄)
│   ├── retrieve_chunks_async (364줄)
│   │   ├── create_query_embedding_async (61줄)
│   │   ├── _get_max_similarity (84줄)
│   │   │   └── _distance_to_similarity (585줄)
│   │   └── rerank_chunks (86줄)
│   ├── _evaluate_search_quality (372줄)
│   │   └── _distance_to_similarity (234줄)
│   ├── _expand_query_with_llm (389줄)
│   └── _finalize_search_results (411줄)
│       ├── _get_max_similarity (341줄)
│       ├── rerank_chunks (343줄)
│       └── _evaluate_search_quality (347줄)
├── search_engine.get_distance_to_similarity (459줄)
├── response_generator._generate_llm_only_response (467줄 또는 500줄)
│   ├── has_situation_in_history (219줄)
│   ├── extract_situation_from_history (225줄)
│   ├── has_situation_context (272줄)
│   └── is_sufficiently_detailed (273줄)
├── response_generator.generate_response_with_persona (480줄)
│   ├── has_situation_in_history (442줄)
│   ├── extract_situation_from_history (448줄)
│   ├── has_situation_context (487줄)
│   └── is_sufficiently_detailed (488줄)
└── _save_qa_to_vectordb_async (497줄)
    └── search_engine.create_query_embedding_async (334줄)
```

---

## 파일별 주요 함수 목록

### rag_therapy.py
- `RAGTherapySystem.__init__` (79-282줄): 시스템 초기화
- `RAGTherapySystem.chat` (372-542줄): 메인 상담 함수
- `RAGTherapySystem._get_user_chat_history` (289-298줄): 사용자별 히스토리 가져오기
- `RAGTherapySystem._reset_user_session` (301-304줄): 사용자 세션 초기화
- `RAGTherapySystem._save_qa_to_vectordb_async` (317-369줄): Self-learning 저장

### persona_manager.py
- `PersonaManager.__init__` (21-52줄): 페르소나 관리자 초기화
- `PersonaManager._load_cached_persona` (111-126줄): 캐시된 페르소나 로드
- `PersonaManager._get_default_persona` (107-108줄): 기본 페르소나 가져오기
- `PersonaManager._start_background_persona_generation` (142-160줄): 백그라운드 페르소나 생성
- `PersonaManager._generate_persona_from_rag` (223-444줄): RAG 기반 페르소나 생성

### search_engine.py
- `SearchEngine.__init__` (18-26줄): 검색 엔진 초기화
- `SearchEngine.create_query_embedding_async` (42-55줄): 비동기 임베딩 생성
- `SearchEngine.retrieve_chunks_async` (58-88줄): 비동기 청크 검색
- `SearchEngine._iterative_search_with_query_expansion_async` (357-411줄): Multi-step 반복 검색
- `SearchEngine._evaluate_search_quality` (219-258줄): 검색 품질 평가
- `SearchEngine.rerank_chunks` (99-180줄): Re-ranker 실행
- `SearchEngine._get_max_similarity` (576-588줄): 최고 유사도 계산
- `SearchEngine.get_distance_to_similarity` (591-592줄): distance를 similarity로 변환

### therapy_protocol.py
- `TherapyProtocol.__init__` (69-92줄): 프로토콜 초기화
- `TherapyProtocol.generate_protocol_guidance` (263-304줄): 프로토콜 가이드 생성
- `TherapyProtocol.select_stage_with_llm` (181-260줄): LLM 기반 단계 선택
- `TherapyProtocol.select_protocol` (103-121줄): 프로토콜 선택
- `TherapyProtocol.assess_severity` (124-140줄): 심각도 평가
- `TherapyProtocol._build_integrated_prompt` (307-370줄): 통합 프롬프트 구성

### response_generator.py
- `ResponseGenerator.__init__` (17-24줄): 답변 생성기 초기화
- `ResponseGenerator.classify_input` (170-189줄): 입력 분류
- `ResponseGenerator.has_situation_context` (27-58줄): 감정 + 상황 포함 여부 확인
- `ResponseGenerator.is_sufficiently_detailed` (61-108줄): 충분히 구체적인지 확인
- `ResponseGenerator.has_situation_in_history` (111-138줄): 히스토리에 상황 확인
- `ResponseGenerator.extract_situation_from_history` (141-167줄): 히스토리에서 상황 추출
- `ResponseGenerator._generate_llm_only_response` (197-363줄): LLM 단독 답변 생성
- `ResponseGenerator.generate_response_with_persona` (366-610줄): RAG 기반 답변 생성

---

## 주요 상수 및 임계값

- **threshold**: 0.7 (유사도 기준)
- **reranker_threshold**: 0.55 (Re-ranker 실행 기준)
- **quality_threshold**: 0.6 (품질 개선 필요 기준)
- **max_chat_history**: 10 (최대 대화 히스토리 개수)
- **persona_cache_validity**: 86400초 (24시간)
- **max_tokens_llm_only**: 180
- **max_tokens_rag**: 400
- **n_results_default**: 5 (기본 검색 결과 개수)
- **max_iterations_default**: 1 (기본 반복 검색 횟수)

---

## 비동기 처리 흐름

### 주요 비동기 함수
1. `RAGTherapySystem.chat` (async)
2. `TherapyProtocol.generate_protocol_guidance` (async)
3. `TherapyProtocol.select_stage_with_llm` (async)
4. `SearchEngine._iterative_search_with_query_expansion_async` (async)
5. `SearchEngine.retrieve_chunks_async` (async)
6. `SearchEngine.create_query_embedding_async` (async)
7. `SearchEngine.rerank_chunks` (async)
8. `ResponseGenerator._generate_llm_only_response` (async)
9. `ResponseGenerator.generate_response_with_persona` (async)
10. `RAGTherapySystem._save_qa_to_vectordb_async` (async)

### 병렬 처리 구간
- **페르소나 생성**: Vector DB 검색 + 웹 검색 병렬 (persona_manager.py:295줄)
- **Multi-step 검색**: 확장된 쿼리로 재검색 병렬 (search_engine.py:394-395줄)
- **Self-learning**: 백그라운드 태스크로 실행 (rag_therapy.py:497줄)

---

## 에러 처리

### 주요 예외 처리 구간
1. **Vector DB 초기화 실패** (rag_therapy.py:110-113줄)
2. **페르소나 생성 실패** (persona_manager.py:442-444줄)
3. **검색 실패** (search_engine.py:270-272줄)
4. **Re-ranker 실패** (search_engine.py:178-180줄)
5. **답변 생성 실패** (response_generator.py:355-363줄, 602-610줄)
6. **Self-learning 저장 실패** (rag_therapy.py:367-369줄)

모든 에러는 로그로 기록되고, 기본값 또는 빈 응답으로 처리되어 시스템이 계속 동작할 수 있도록 설계되었습니다.

