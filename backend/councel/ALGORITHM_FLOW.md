# 상담 시스템 알고리즘 흐름도

## 목차
1. [전체 흐름도](#전체-흐름도)
2. [파일별 흐름도](#파일별-흐름도)
   - [rag_therapy.py](#rag_therapypy)
   - [persona_manager.py](#persona_managerpy)
   - [therapy_protocol.py](#therapy_protocolpy)
   - [search_engine.py](#search_enginepy)
   - [response_generator.py](#response_generatorpy)
3. [최고 유사도 vs 품질 평가 설명](#최고-유사도-vs-품질-평가-설명)

---

## 전체 흐름도

```
시스템 초기화
  ↓
RAGTherapySystem.__init__
  ├─→ Vector DB 초기화
  ├─→ OpenAI 클라이언트 초기화
  ├─→ PersonaManager 초기화
  │     ├─→ 캐시 로드 시도
  │     ├─→ [캐시 있음] → 캐시된 페르소나 사용
  │     └─→ [캐시 없음] → 기본 페르소나 사용 + 백그라운드 RAG 페르소나 생성
  ├─→ SearchEngine 초기화
  ├─→ ResponseGenerator 초기화
  └─→ TherapyProtocol 초기화

사용자 입력 (chat 함수)
  ↓
종료 키워드 확인
  ├─→ [종료 키워드] → 세션 초기화 → 종료 메시지 반환
  └─→ [일반 입력] → 계속 진행
      ↓
프로토콜 가이드 생성
  ├─→ 세션 상태 업데이트
  ├─→ LLM 기반 상담 단계 선택
  ├─→ 프로토콜 선택 (EAP/SFBT/INTEGRATED)
  ├─→ 심각도 평가
  └─→ 통합 프롬프트 생성
      ↓
입력 분류
  ↓
Vector DB 검색 조건 판단
  ├─→ 감정 + 상황 포함 여부 확인
  ├─→ RAG 강제 사용 키워드 확인
  └─→ should_search_vector_db = (감정+상황) OR (RAG 강제)
      ↓
[should_search_vector_db = True]
  ├─→ 검색 쿼리 구성
  │     ├─→ [RAG 강제 + 히스토리 상황 있음] → 히스토리 상황 + 현재 입력
  │     └─→ [그 외] → 현재 입력
  ├─→ Multi-step 반복 검색
  │     ├─→ 초기 검색
  │     ├─→ 품질 평가
  │     ├─→ [품질 낮음] → 쿼리 확장 → 재검색 (반복)
  │     └─→ 최종 결과 반환
  ├─→ 최고 유사도 계산
  └─→ 통합 답변 생성
      ├─→ 검색 결과와 유사도 전달
      ├─→ 유사도에 따라 검색 결과 활용 정도 결정
      │     ├─→ [유사도 ≥ 0.7] → 상위 1-2개 청크, 간단한 조언 (3~4문장)
      │     └─→ [유사도 < 0.7] → 상위 3개 청크, 상세한 조언 (4~7문장)
      └─→ [유사도 < 0.7] → Self-learning (백그라운드 저장)

[should_search_vector_db = False]
  └─→ 통합 답변 생성 (검색 결과 없음, 2~3문장)
      ↓
프로토콜 정보 추가
  ↓
대화 히스토리 업데이트 (최대 10개 유지)
  ↓
응답 반환
```

---

## 파일별 흐름도

### rag_therapy.py

#### RAGTherapySystem.__init__ (79-282줄)

```
시작
  ↓
Vector DB 경로 설정 및 존재 확인
  ↓
ChromaDB 클라이언트 초기화
  ↓
컬렉션 로드 ("vector_adler")
  ↓
OpenAI 클라이언트 초기화 (동기/비동기)
  ↓
상담 키워드 목록 로드
  ↓
대화 히스토리 초기화
  ↓
PersonaManager 초기화
  ├─→ OpenAI 클라이언트, 컬렉션, 기본 경로 설정
  ├─→ 캐시 파일 경로 설정
  ├─→ 페르소나 상태 플래그 초기화
  ├─→ 캐시된 페르소나 로드 시도
  │     ├─→ [캐시 있음 AND 유효] → 캐시된 페르소나 사용
  │     └─→ [캐시 없음 OR 만료] → 기본 페르소나 생성 + 백그라운드 RAG 페르소나 생성
  └─→ adler_persona 저장
      ↓
SearchEngine 초기화
  ├─→ OpenAI 클라이언트, 컬렉션 설정
  └─→ 상담 키워드를 set으로 변환
      ↓
ResponseGenerator 초기화
  ├─→ OpenAI 클라이언트, 상담 키워드 설정
  └─→ 상담 키워드를 set으로 변환
      ↓
TherapyProtocol 초기화
  ├─→ OpenAI 클라이언트 설정
  ├─→ TherapySession 객체 생성
  └─→ 상담 단계별 지침 딕셔너리 로드
      ↓
백그라운드 작업용 스레드 풀 초기화
  ↓
완료
```

#### RAGTherapySystem.chat (372-542줄)

```
사용자 입력 받기
  ↓
사용자별 chat_history 가져오기
  ↓
종료 키워드 확인
  ├─→ [종료 키워드] → 세션 초기화 → 종료 메시지 반환
  └─→ [일반 입력] → 계속 진행
      ↓
프로토콜 가이드 생성
  └─→ therapy_protocol.generate_protocol_guidance
      ↓
입력 분류
  └─→ response_generator.classify_input
      ↓
감정 + 상황 포함 여부 체크
  └─→ response_generator.has_situation_context
      ↓
RAG 강제 사용 키워드 체크
  ↓
Vector DB 검색 조건 결정
  └─→ should_search_vector_db = (감정+상황) OR (RAG 강제)
      ↓
[should_search_vector_db = True]
  ├─→ 검색 쿼리 구성
  │     ├─→ [RAG 강제 + 히스토리 상황 있음]
  │     │     ├─→ 히스토리에서 상황 확인
  │     │     ├─→ 히스토리에서 상황 추출
  │     │     └─→ 검색 쿼리 = 히스토리 상황 + 현재 입력
  │     └─→ [그 외] → 검색 쿼리 = 현재 입력
  ├─→ Multi-step 반복 검색
  │     └─→ search_engine._iterative_search_with_query_expansion_async
  ├─→ 최고 유사도 계산
  │     └─→ final_similarity 중 최댓값 사용 (하이브리드 검색 적용)
  │           └─→ final_similarity = base_similarity + emotion_boost
  └─→ 통합 답변 생성
      └─→ response_generator.generate_response
          ├─→ 검색 결과와 유사도 전달
          ├─→ 유사도에 따라 검색 결과 활용 정도 결정
          │     ├─→ [유사도 ≥ 0.7] → 상위 1-2개 청크, 간단한 조언 (3~4문장)
          │     └─→ [유사도 < 0.7] → 상위 3개 청크, 상세한 조언 (4~7문장)
          └─→ [유사도 < 0.7] → Self-learning (백그라운드)
                └─→ _save_qa_to_vectordb_async

[should_search_vector_db = False]
  └─→ 통합 답변 생성
      └─→ response_generator.generate_response (검색 결과 없음, 2~3문장)
      ↓
프로토콜 정보 추가
  ↓
대화 히스토리 업데이트
  ├─→ 현재 대화 추가
  ├─→ 최대 10개 유지 (초과 시 오래된 것 제거)
  └─→ 사용자별 세션 저장
      ↓
응답 반환
```

---

### persona_manager.py

#### PersonaManager.__init__ (21-52줄)

```
시작
  ↓
OpenAI 클라이언트, 컬렉션, 기본 경로 설정
  ↓
캐시 파일 경로 설정
  ↓
페르소나 상태 플래그 초기화
  ↓
캐시된 페르소나 로드 시도
  ├─→ [캐시 있음 AND 유효 (24시간 이내)]
  │     ├─→ 캐시된 페르소나 사용
  │     ├─→ _persona_ready = True
  │     └─→ _rag_persona_ready = True
  └─→ [캐시 없음 OR 만료]
        ├─→ 기본 페르소나 생성
        │     └─→ _get_default_persona
        │           └─→ generate_persona_with_prompt_engineering
        ├─→ _persona_ready = True
        ├─→ _rag_persona_ready = False
        └─→ 백그라운드에서 RAG 페르소나 생성 시작
              └─→ _start_background_persona_generation
                    └─→ _generate_persona_from_rag (비동기 실행)
                          ↓
완료
```

#### PersonaManager._generate_persona_from_rag (223-444줄)

```
시작
  ↓
검색 쿼리 목록 구성 (3개)
  ├─→ "Alfred Adler individual psychology core principles"
  ├─→ "inferiority complex and superiority striving"
  └─→ "social interest and community feeling"
      ↓
Vector DB 검색 (병렬 처리)
  ├─→ 쿼리 1 검색
  ├─→ 쿼리 2 검색
  └─→ 쿼리 3 검색
      ├─→ 임베딩 생성
      ├─→ ChromaDB query 실행
      └─→ 결과 포맷팅
      ↓
결과 병합 및 중복 제거
  ↓
상위 5개 청크만 사용
  ↓
웹 검색으로 최신 정보 수집 (Vector DB 검색과 병렬)
  └─→ _search_web_for_adler
      ↓
[검색된 청크 없음 AND 웹 정보 없음]
  └─→ 기본 페르소나 반환
      ↓
[검색 결과 있음]
  ├─→ Vector DB 청크 텍스트 추출
  ├─→ 웹 검색 정보 추가
  └─→ LLM을 사용하여 페르소나 프롬프트 생성
        ├─→ 컨텍스트 구성
        ├─→ OpenAI API 호출
        └─→ 생성된 페르소나 반환
            ↓
[생성 실패]
  └─→ 기본 페르소나 반환
      ↓
완료
```

---

### therapy_protocol.py

#### TherapyProtocol.generate_protocol_guidance (263-304줄)

```
시작
  ↓
세션 상태 업데이트
  └─→ update_session
      └─→ TherapySession.update_from_history
          ↓
LLM 기반 상담 단계 선택
  └─→ select_stage_with_llm
      ├─→ 최근 3개 대화 히스토리 컨텍스트 구성
      ├─→ LLM 프롬프트 구성
      ├─→ OpenAI API 호출 (비동기 또는 동기)
      ├─→ 단계 번호 추출
      └─→ TherapyStage로 변환
          ↓
선택된 단계를 세션에 저장
  ↓
프로토콜 선택
  └─→ select_protocol
      ├─→ [첫 대화] → EAP
      ├─→ [위기 키워드] → EAP
      ├─→ [해결책 탐색 키워드] → SFBT
      └─→ [기본] → INTEGRATED
          ↓
선택된 프로토콜을 세션에 저장
  ↓
심각도 평가
  └─→ assess_severity
      ├─→ 위기/높음/중간 키워드 정의
      └─→ 키워드 매칭으로 심각도 반환
          ↓
평가된 심각도를 세션에 저장
  ↓
현재 단계 가이드라인 가져오기
  └─→ get_stage_guideline
      ↓
통합 프롬프트 생성
  └─→ _build_integrated_prompt
      ├─→ 기본 아들러 페르소나 추가
      ├─→ 현재 상담 단계 가이드라인 추가
      ├─→ [심각도가 critical/high] → 위기 상황 대응 추가
      └─→ 답변 구조 추가
          ↓
프로토콜 가이드 딕셔너리 반환
  ↓
완료
```

---

### search_engine.py

#### SearchEngine._iterative_search_with_query_expansion_async (357-411줄)

```
시작
  ↓
초기화 (all_chunks = [], seen_ids = set(), iteration = 0)
  ↓
Step 1: 초기 검색 (하이브리드 검색)
  └─→ retrieve_chunks_async
      ├─→ 임베딩 생성
      │     └─→ create_query_embedding_async
      ├─→ ChromaDB query 실행 (비동기 스레드 풀)
      │     └─→ n_results × 2개 검색 (더 많이 검색 후 필터링)
      ├─→ 결과 포맷팅
      ├─→ 하이브리드 검색 스코어링 적용
      │     └─→ _apply_hybrid_scoring (공통 함수)
      │           ├─→ base_similarity 계산 (distance → similarity 변환)
      │           ├─→ emotion_boost 계산 (감정 키워드 매칭 보너스)
      │           ├─→ final_similarity = base_similarity + emotion_boost (최대 1.0)
      │           └─→ final_similarity 기준으로 정렬
      ├─→ 상위 n_results개만 선택
      └─→ 조건부 Re-ranker 실행
          ├─→ 최고 유사도 계산 (final_similarity 사용)
          └─→ [최고 유사도 < 0.55] → Re-ranker 실행
                └─→ rerank_chunks
                    ├─→ 평가 프롬프트 구성
                    ├─→ OpenAI API 호출
                    └─→ 순위 파싱 및 재정렬
          ↓
초기 검색 결과를 all_chunks에 추가 (중복 제거)
  ↓
Step 2: 품질 평가
  └─→ _evaluate_search_quality
      ├─→ 평균 유사도 계산
      │     └─→ 각 청크의 distance를 similarity로 변환 후 평균 계산
      ├─→ 다양성 점수 계산 (서로 다른 소스 비율)
      │     └─→ diversity_score = 서로 다른 소스 개수 / 전체 청크 개수
      ├─→ 종합 품질 점수 계산
      │     └─→ quality_score = 평균 유사도 × 0.7 + 다양성 점수 × 0.3
      └─→ 개선 필요 여부 판단 (품질 점수 < 0.6)
          ↓
Step 3: 반복 검색 (조건부)
  ├─→ [max_iterations > 1 AND 품질 낮음] → 반복 검색
  │     └─→ while 루프
  │           ├─→ 조기 종료 조건 확인
  │           ├─→ iteration 증가
  │           ├─→ 쿼리 확장
  │           │     └─→ _expand_query_with_llm (키워드 기반 확장)
  │           ├─→ 확장된 쿼리로 재검색 (비동기 병렬 처리)
  │           │     └─→ retrieve_chunks_async 여러 번 병렬 실행
  │           ├─→ 새 청크 추가 (중복 제거)
  │           └─→ 재평가
  │                 └─→ _evaluate_search_quality
  │                       └─→ [품질 충분히 개선] → 중단
  └─→ [max_iterations = 1 OR 품질 충분] → 반복 검색 생략
      ↓
Step 4: 최종 처리
  └─→ _finalize_search_results
      ├─→ 최고 유사도 계산
      │     └─→ final_similarity 중 최댓값 사용 (하이브리드 검색 결과)
      ├─→ 조건부 Re-ranker 실행
      │     └─→ [최고 유사도 < 0.55] → rerank_chunks 실행
      ├─→ 상위 n_results개만 반환
      ├─→ 품질 평가
      │     └─→ _evaluate_search_quality (평균 유사도 70% + 다양성 30%)
      └─→ 결과 딕셔너리 반환
          ↓
완료
```

---

### response_generator.py

#### ResponseGenerator.generate_response (통합 함수)

```
시작
  ↓
프로토콜 통합 페르소나 사용
  ↓
검색 결과 및 유사도 확인
  ├─→ [검색 결과 있음]
  │     ├─→ 유사도에 따라 청크 활용 정도 결정
  │     │     ├─→ [유사도 ≥ 0.7] → 상위 1-2개 청크, 간단한 조언
  │     │     └─→ [유사도 < 0.7] → 상위 3개 청크, 상세한 조언
  │     └─→ 컨텍스트 구성
  └─→ [검색 결과 없음] → LLM 단독 모드
      ↓
감정 맥락 파악
  └─→ 최근 2개 대화에서 감정 키워드 추출 (set 연산)
      ↓
감정 키워드 추출 (검색 결과가 있을 때)
  └─→ 사용자 입력에서 감정 키워드 추출 (set 연산)
      ↓
히스토리 상황 확인
  └─→ has_situation_in_history
      ├─→ [히스토리에 상황 있음]
      │     ├─→ 히스토리에서 상황 추출
      │     │     └─→ extract_situation_from_history
      │     ├─→ 해결 방법 질문인지 확인
      │     └─→ [해결 방법 질문]
      │           └─→ 히스토리 상황 기반 해결 방법 제시 가이던스
      │           └─→ [일반 질문]
      │                 └─→ 상황 인지 후 답변 가이던스
      └─→ [히스토리에 상황 없음] → 계속 진행
          ↓
입력 구체성 확인
  ├─→ 감정 + 상황 포함 여부 확인
  │     └─→ has_situation_context
  └─→ 충분히 구체적인지 확인
        └─→ is_sufficiently_detailed
            ↓
상황 가이던스 생성
  ├─→ [충분히 구체적] → 다시 물어보지 않음
  ├─→ [구체적이지 않음] → 더 자세히 물어봄
  └─→ [상황 없음] → 상황 설명 유도
      ↓
답변 구조 구성 (검색 결과 유무와 유사도에 따라)
  ├─→ [유사도 < 0.7 AND 검색 결과 있음]
  │     └─→ 1. 공감(1문장) + 2. 상세 조언(2~3문장) + 3. 질문(1~2문장) = 4~7문장
  ├─→ [유사도 ≥ 0.7 AND 검색 결과 있음]
  │     └─→ 1. 공감(1문장) + 2. 간단한 조언(1~2문장) + 3. 질문(1~2문장) = 3~4문장
  └─→ [검색 결과 없음]
        └─→ 1. 공감(1문장) + 2. 질문(1~2문장) = 2~3문장
      ↓
프롬프트 구성
  ├─→ 시스템 메시지 구성
  ├─→ 최근 3개 대화 포함
  └─→ 사용자 메시지 추가
      ↓
OpenAI API 호출
  ├─→ model: gpt-4o-mini
  ├─→ temperature: 0.3
  └─→ max_tokens: 유사도에 따라 동적 조정
      ├─→ [유사도 < 0.7] → 400 (4~7문장)
      ├─→ [유사도 ≥ 0.7] → 250 (3~4문장)
      └─→ [검색 결과 없음] → 180 (2~3문장)
      ↓
응답 딕셔너리 반환
  ↓
완료
```

---

## 최고 유사도 vs 품질 평가 설명

### 최고 유사도 (max_similarity)

**목적**: 검색된 청크들 중에서 가장 높은 유사도를 가진 청크의 유사도 값

**계산 방법**:
- **하이브리드 검색 적용** (기본적으로 모든 검색에 적용):
  - `base_similarity = distance → similarity 변환 (1 / (1 + distance))`
  - `emotion_boost = 감정 키워드 매칭 보너스 (최대 0.2)`
  - `final_similarity = base_similarity + emotion_boost` (최대 1.0)
  - 최고 유사도 = 모든 청크의 `final_similarity` 중 최댓값
  - `retrieve_chunks_async` 함수에서 자동으로 하이브리드 검색이 적용됨

**사용 용도**:
- Threshold 분기 결정 (0.7 기준)
- Re-ranker 실행 여부 결정 (0.55 기준)
- RAG 사용 여부 판단

### 품질 평가 (quality_score)

**목적**: 검색 결과의 전체적인 품질을 평가 (평균 유사도 + 다양성)

**계산 방법**:
1. **평균 유사도 계산**:
   - 각 청크의 `distance`를 `similarity`로 변환
   - 모든 청크의 `similarity` 평균 계산

2. **다양성 점수 계산**:
   - `diversity_score = 서로 다른 소스 개수 / 전체 청크 개수`
   - 예: 5개 청크 중 3개가 다른 소스 → 다양성 점수 = 3/5 = 0.6

3. **종합 품질 점수 계산**:
   - `quality_score = 평균 유사도 × 0.7 + 다양성 점수 × 0.3`
   - 예: 평균 유사도 0.8, 다양성 0.6 → 품질 점수 = 0.8 × 0.7 + 0.6 × 0.3 = 0.74

**사용 용도**:
- 반복 검색 필요 여부 판단 (품질 점수 < 0.6이면 재검색)
- 검색 결과의 전반적인 품질 모니터링

### 핵심 차이점

- **최고 유사도**: 개별 청크 중 가장 높은 유사도 (단일 값)
- **품질 평가**: 전체 검색 결과의 평균 유사도와 다양성을 종합한 점수
- **독립적 계산**: 최고 유사도와 품질 평가는 서로 다른 목적으로 별도로 계산됨
- **합치지 않음**: 최고 유사도는 품질 평가 점수와 합쳐지지 않음
