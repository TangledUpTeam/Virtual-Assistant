# HR RAG 시스템 아키텍처

## 전체 시스템 플로우

```mermaid
graph TB
    Start([사용자 질문 입력]) --> CheckHR{HR 키워드<br/>확인}
    CheckHR -->|HR 질문| CallAPI[hrService.js<br/>RAG API 호출]
    CheckHR -->|일반 질문| Other[일반 챗봇 처리]
    
    CallAPI --> APIEndpoint[/api/v1/rag/query<br/>FastAPI 엔드포인트]
    
    APIEndpoint --> RAGRetriever[RAGRetriever.query<br/>질의응답 처리]
    
    RAGRetriever --> BuildChain{RAG 체인<br/>구성}
    BuildChain --> RetrieveStep[retrieve_and_filter<br/>문서 검색 및 필터링]
    BuildChain --> GenerateStep[generate_answer<br/>답변 생성]
    
    RetrieveStep --> VectorSearch[VectorStore.search<br/>벡터 검색]
    
    VectorSearch --> TranslateQuery[쿼리 한→영 번역<br/>GPT-4o-mini]
    TranslateQuery --> EmbedQuery[쿼리 임베딩 생성<br/>text-embedding-3-large]
    EmbedQuery --> ChromaSearch[ChromaDB 검색<br/>top_k * 3]
    
    ChromaSearch --> CalcSimilarity[Cosine Similarity<br/>계산]
    CalcSimilarity --> DynamicThreshold[동적 Threshold<br/>계산 및 필터링]
    
    DynamicThreshold --> FilterChunks[상위 k개<br/>청크 선택]
    FilterChunks --> BuildContext[컨텍스트<br/>구성]
    
    BuildContext --> GenerateStep
    GenerateStep --> LLM[GPT-4o<br/>답변 생성]
    LLM --> Response[QueryResponse<br/>반환]
    
    Response --> Frontend[프론트엔드<br/>답변 표시]
    
    style Start fill:#e1f5ff
    style CheckHR fill:#fff4e1
    style CallAPI fill:#e8f5e9
    style APIEndpoint fill:#f3e5f5
    style RAGRetriever fill:#e3f2fd
    style VectorSearch fill:#fff9c4
    style LLM fill:#ffebee
    style Response fill:#e8f5e9
    style Frontend fill:#e1f5ff
```

## 데이터 흐름 (Document Ingestion)

```mermaid
graph LR
    PDF[PDF 파일<br/>업로드] --> PDFProcessor[PDFProcessor<br/>process_pdf]
    
    PDFProcessor --> ExtractText[텍스트 추출<br/>PyMuPDF]
    PDFProcessor --> ExtractTable[표 추출<br/>pdfplumber]
    PDFProcessor --> ExtractImage[이미지 추출<br/>GPT-4 Vision]
    
    ExtractText --> ProcessedDoc[ProcessedDocument<br/>생성]
    ExtractTable --> ProcessedDoc
    ExtractImage --> ProcessedDoc
    
    ProcessedDoc --> DocumentConverter[DocumentConverter<br/>create_chunks]
    
    DocumentConverter --> Chunking[RecursiveCharacterTextSplitter<br/>청킹]
    Chunking --> DocumentChunks[DocumentChunk<br/>리스트]
    
    DocumentChunks --> VectorStore[VectorStore<br/>add_chunks]
    
    VectorStore --> TranslateChunks[청크 한→영 번역<br/>GPT-4o-mini]
    TranslateChunks --> EmbedChunks[임베딩 생성<br/>text-embedding-3-large]
    EmbedChunks --> ChromaAdd[ChromaDB<br/>저장]
    
    ChromaAdd --> JSON[JSON 파일<br/>저장<br/>임베딩 포함]
    
    style PDF fill:#e1f5ff
    style PDFProcessor fill:#fff4e1
    style ProcessedDoc fill:#e8f5e9
    style DocumentConverter fill:#f3e5f5
    style VectorStore fill:#fff9c4
    style ChromaAdd fill:#ffebee
    style JSON fill:#e8f5e9
```

## 컴포넌트 상세 구조

```mermaid
classDiagram
    class hrService {
        +isHRQuestion(text) boolean
        +queryHRDocument(query) Promise
        +getHRKeywords() Array
    }
    
    class RAGRetriever {
        -vector_store: VectorStore
        -llm: ChatOpenAI
        -rag_chain: Chain
        +query(request) QueryResponse
        +needs_search(query) boolean
        +query_smalltalk(query) string
        -_build_rag_chain() Chain
    }
    
    class VectorStore {
        -client: ChromaDB
        -collection: Collection
        +search(query, top_k) Dict
        +add_chunks(chunks) int
        +embed_text(text) List[float]
        +translate_to_english(text) string
        +calculate_cosine_similarity(vec1, vec2) float
    }
    
    class PDFProcessor {
        +process_pdf(pdf_path) ProcessedDocument
        +process_text(text_path) ProcessedDocument
        -_extract_text(page) ProcessedContent
        -_extract_tables(page) List[ProcessedContent]
        -_extract_images(page) List[ProcessedContent]
        -_describe_image_with_gpt4(image) string
    }
    
    class DocumentConverter {
        -text_splitter: RecursiveCharacterTextSplitter
        +create_chunks(processed_doc) List[DocumentChunk]
        +convert_to_markdown(content) string
        +validate_chunks(chunks) boolean
    }
    
    class RAGConfig {
        +OPENAI_API_KEY: str
        +OPENAI_MODEL: str
        +EMBEDDING_MODEL: str
        +TRANSLATION_MODEL: str
        +CHROMA_COLLECTION_NAME: str
        +RAG_TOP_K: int
        +RAG_MIN_SIMILARITY_THRESHOLD: float
        +RAG_MAX_SIMILARITY_THRESHOLD: float
    }
    
    hrService --> RAGRetriever : API 호출
    RAGRetriever --> VectorStore : 검색 요청
    RAGRetriever --> RAGConfig : 설정 사용
    VectorStore --> RAGConfig : 설정 사용
    PDFProcessor --> DocumentConverter : 처리된 문서 전달
    DocumentConverter --> VectorStore : 청크 추가
    PDFProcessor --> RAGConfig : 설정 사용
```

## RAG 체인 상세 플로우

```mermaid
sequenceDiagram
    participant User as 사용자
    participant Frontend as hrService.js
    participant API as /api/v1/rag/query
    participant Retriever as RAGRetriever
    participant VectorStore as VectorStore
    participant ChromaDB as ChromaDB
    participant LLM as GPT-4o
    participant Translator as GPT-4o-mini
    
    User->>Frontend: HR 질문 입력
    Frontend->>Frontend: isHRQuestion() 확인
    Frontend->>API: POST /api/v1/rag/query
    API->>Retriever: query(request)
    
    Retriever->>Retriever: _build_rag_chain() 구성
    
    Note over Retriever: retrieve_and_filter 단계
    Retriever->>VectorStore: search(query, top_k * 3)
    VectorStore->>Translator: translate_to_english(query)
    Translator-->>VectorStore: 영어 번역 텍스트
    VectorStore->>VectorStore: embed_text(번역 텍스트)
    VectorStore->>ChromaDB: query(query_embeddings)
    ChromaDB-->>VectorStore: 검색 결과 (documents, metadatas, embeddings)
    VectorStore->>VectorStore: calculate_cosine_similarity()
    VectorStore->>VectorStore: 동적 threshold 계산
    VectorStore->>VectorStore: threshold 기반 필터링
    VectorStore-->>Retriever: 필터링된 청크 리스트
    
    Retriever->>Retriever: 컨텍스트 구성
    
    Note over Retriever: generate_answer 단계
    Retriever->>LLM: prompt_template | llm | parser
    LLM-->>Retriever: 생성된 답변
    
    Retriever-->>API: QueryResponse
    API-->>Frontend: JSON 응답
    Frontend-->>User: 답변 표시
```

## 동적 Threshold 계산 로직

```mermaid
flowchart TD
    Start([검색 결과 수신]) --> CheckEmpty{검색 결과<br/>있음?}
    
    CheckEmpty -->|없음| DefaultThreshold[기본 Threshold<br/>MIN 사용]
    CheckEmpty -->|있음| ExtractScores[유사도 점수<br/>추출]
    
    ExtractScores --> CalcMax[최고 점수<br/>계산]
    ExtractScores --> CalcAvg[평균 점수<br/>계산]
    
    CalcMax --> CalcDynamic[동적 Threshold<br/>max + avg / 2]
    CalcAvg --> CalcDynamic
    
    CalcDynamic --> CheckMin{Threshold < MIN?}
    CheckMin -->|예| SetMin[MIN으로 설정]
    CheckMin -->|아니오| CheckMax{Threshold > MAX?}
    
    CheckMax -->|예| SetMax[MAX로 설정]
    CheckMax -->|아니오| UseDynamic[계산된 값 사용]
    
    SetMin --> Filter[Threshold로<br/>필터링]
    SetMax --> Filter
    UseDynamic --> Filter
    DefaultThreshold --> Filter
    
    Filter --> SelectTopK[상위 k개<br/>선택]
    SelectTopK --> End([최종 청크 리스트])
    
    style Start fill:#e1f5ff
    style CalcDynamic fill:#fff4e1
    style Filter fill:#e8f5e9
    style End fill:#e1f5ff
```

## 주요 설정값

```mermaid
mindmap
  root((HR RAG 설정))
    임베딩
      모델: text-embedding-3-large
      차원: 3072
      번역 모델: GPT-4o-mini
    LLM
      모델: GPT-4o
      Temperature: 0.7
      Max Tokens: 2000
    청킹
      Chunk Size: 400
      Chunk Overlap: 50
      Min Size: 300
      Max Size: 500
    검색
      Top K: 3
      Min Threshold: 0.25
      Max Threshold: 0.375
      동적 Threshold: 활성화
    저장소
      ChromaDB: PersistentClient
      Collection: rag_documents
      경로: ./internal_docs/chroma
```

