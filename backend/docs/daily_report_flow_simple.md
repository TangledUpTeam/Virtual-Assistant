# 일일보고서 시스템 간략 플로우

## 📋 간략 시퀀스 다이어그램

```mermaid
sequenceDiagram
    participant U as 사용자
    participant F as 프론트엔드
    participant API as Backend
    participant DB as PostgreSQL
    participant FSM as Daily FSM
    participant PDF as PDF Gen
    participant VDB as VectorDB

    Note over U,API: Phase 1. 추천업무
    U->>F: 작성 시작
    F->>API: /plan/today
    API->>DB: 전날 보고서 조회
    DB-->>API: 미종결 업무 + 익일 계획
    alt 전날 데이터 부족 시
        API->>VDB: 유사 업무 패턴 검색
        VDB-->>API: 과거 유사 업무
    end
    API->>API: LLM 추천업무 생성<br/>(전날 데이터 + VectorDB 패턴)
    API-->>F: 추천업무 전달

    Note over U,API: Phase 2. 업무 선택
    U->>F: 선택
    F->>API: /daily/select_main_tasks

    Note over U,API: Phase 3. FSM 질문
    F->>API: /daily/start
    API->>FSM: FSM 시작
    FSM-->>F: 첫 질문
    loop 시간대
        U->>F: 답변
        F->>API: /daily/answer
        API->>FSM: 처리
        FSM-->>F: 다음 질문
    end
    U->>F: 특이사항/익일계획 입력
    F->>API: 저장

    Note over API,PDF: Phase 4. 보고서 생성
    API->>API: 일일보고서 빌드
    API->>DB: 저장
    API->>PDF: PDF 생성
    API->>VDB: RAG 저장
    API-->>F: 완료

    F-->>U: PDF 다운로드
```

---

## 🔑 핵심 포인트

### Phase 1: 추천업무
1. **PostgreSQL**: 전날 보고서에서 미종결 업무 + 익일 계획 추출
2. **VectorDB** (조건부): 전날 데이터가 없거나 부족할 때 과거 유사 업무 패턴 검색
3. **LLM**: 전날 데이터 + VectorDB 패턴을 결합하여 추천 업무 생성

### Phase 2: 업무 선택
- 사용자가 추천된 업무 중에서 선택
- 메모리에 임시 저장

### Phase 3: FSM 질문-답변
- 시간대별로 자연어 입력 받기
- LLM으로 구조화된 데이터로 변환
- 이슈사항, 익일 계획 수집

### Phase 4: 보고서 생성
- 의미적 유사도로 미종결 업무 자동 매칭
- PostgreSQL 저장
- PDF 생성 및 저장
- VectorDB 저장 (RAG 검색용)

