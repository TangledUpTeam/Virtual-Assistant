# Insurance RAG 모듈 폴더 구조 안내

이 문서는 Insurance RAG 파이프라인을 실제로 돌릴 때 필요한 폴더/파일 구조와 역할을 쉽고 자세하게 설명합니다. 각 경로는 Windows 기준 절대 경로 예시를 함께 제공합니다.

## 최상위 위치
- `C:/dev/himedia/Virtual-Assistant/backend/app/domain/rag/Insurance/`
  - Insurance 도메인 RAG 파이프라인의 루트 폴더입니다.

## 핵심 폴더와 파일

### 1) documents
- 경로: `backend/app/domain/rag/Insurance/documents/`
- 역할: 입력 PDF 파일들을 보관하는 디렉터리
- 사용법:
  - `*.pdf` 파일을 여기에 넣으면 `scripts/run_extractor.py`가 디렉터리 전체를 자동 처리합니다.
  - 예: `C:/dev/himedia/Virtual-Assistant/backend/app/domain/rag/Insurance/documents/보험약관.pdf`

### 2) scripts
- 경로: `backend/app/domain/rag/Insurance/scripts/`
- 역할: 파이프라인 실행용 스크립트와 러닝 로그를 관리
- 주요 파일:
  - `run_extractor.py`: PDF → 페이지별 텍스트/마크다운 추출 (빠른 모드 기본: Vision 비활성)
    - 출력: `scripts/extracted_pages.json` + `scripts/runs/<timestamp>/extracted_pages.json`
  - `run_chunking.py`: 추출 결과를 토큰 기반 청크로 분할 (기본: 800/120 오버랩)
    - 출력: `scripts/chunks.json` + `scripts/runs/<timestamp>/chunks.json`, `summary.txt`
  - `run_embed_store.py`: 청크 임베딩 후 ChromaDB에 저장
    - 출력: `scripts/runs/<timestamp>/embed_summary.txt`
  - `_utils.py`: 공통 유틸 (타임스탬프, 디렉터리 생성, JSON/TXT 저장 등)
- 러닝 기록:
  - `scripts/runs/<timestamp>/` 하위에 각 단계별 산출물과 요약이 저장됩니다.

### 3) chroma_db
- 경로: `backend/app/domain/rag/Insurance/chroma_db/`
- 역할: 로컬 ChromaDB 퍼시스트 디렉터리
- 내용:
  - 컬렉션: `insurance_documents`
  - `run_embed_store.py --reset` 실행 시 이 디렉터리가 초기화되고 재생성됩니다.

### 4) services
- 경로: `backend/app/domain/rag/Insurance/services/`
- 역할: 도메인 서비스 레이어 (PDF 추출, RAG 파이프라인 등)
- 주요 하위 경로:
  - `document_processor/`
    - `extractor.py`: PDF 페이지 분석/처리 로직 (텍스트/테이블/이미지 감지, Vision/LLM 통합)
  - `rag_pipeline.py`: (필요 시) RAG 전체 파이프라인 서비스 구성체

### 5) infrastructure
- 경로: `backend/app/domain/rag/Insurance/infrastructure/`
- 역할: 외부 시스템 연동 (벡터스토어, 임베딩 등)
- 주요 하위 경로:
  - `vectorstore/chroma.py`: ChromaDB 벡터스토어 구현체
  - `embeddings/openai.py`: OpenAI 임베딩 제공자 구현체

### 6) core
- 경로: `backend/app/domain/rag/Insurance/core/`
- 역할: 공통 모델, 설정, 예외 등
- 주요 파일:
  - `models.py`: `InsuranceDocument` 등 데이터 모델
  - `config.py`: API 키, 임베딩 모델/차원, 배치 크기, 컬렉션 이름 등 설정
  - `exceptions.py`: 도메인/인프라 공용 예외 정의

### 7) data / output
- 경로: `backend/app/domain/rag/Insurance/data/`, `backend/app/domain/rag/Insurance/output/`
- 역할: 원본/가공 데이터 보관 (프로젝트에 따라 사용 여부 상이)
- 내용:
  - `output/`에는 처리된 KPI/리포트 샘플 결과 등이 저장될 수 있습니다.

## 실행 흐름 요약 (3단계)
1. 추출 (Extract)
   - 커맨드:
     ```bash
     cd C:/dev/himedia/Virtual-Assistant/backend/app/domain/rag/Insurance/scripts
     python run_extractor.py
     ```
   - 입력: `documents/*.pdf`
   - 출력: `scripts/extracted_pages.json`, `scripts/runs/<timestamp>/extracted_pages.json`

2. 청킹 (Chunk)
   - 커맨드:
     ```bash
     python run_chunking.py
     ```
   - 입력: `scripts/extracted_pages.json`
   - 출력: `scripts/chunks.json`, `scripts/runs/<timestamp>/chunks.json`, `summary.txt`

3. 임베딩 저장 (Embed + Store)
   - 커맨드:
     ```bash
     python run_embed_store.py
     # 초기화 후 깔끔 업서트 원하면
     python run_embed_store.py --reset
     ```
   - 입력: `scripts/chunks.json`
   - 출력: `scripts/runs/<timestamp>/embed_summary.txt`
   - 저장 위치: `chroma_db/` (컬렉션: `insurance_documents`)

## 자주 쓰는 팁
- 실행 위치 에러 방지: 항상 `scripts` 폴더에서 실행하거나, 절대 경로로 스크립트를 지정하세요.
- 빠른 추출 모드: 기본적으로 Vision/LLM을 비활성화하여 속도를 높입니다. OCR가 꼭 필요한 문서만 선택적으로 Vision을 켜서 재추출하세요.
- 중복 ID 방지: 청킹 단계에서 `id`를 파일명+페이지+청크 인덱스로 만들면 안전합니다. 예: `mydoc_p12_c3`.
- 컬렉션 초기화: 중복이 신경 쓰이면 `--reset`으로 `chroma_db/`를 초기화하고 임베딩을 다시 저장하세요.

## 오류/로그 위치
- 각 단계의 상세 로그/요약은 `scripts/runs/<timestamp>/` 하위에 저장됩니다.
- 크로마 텔레메트리 경고(예: `Failed to send telemetry event ...`)는 무해하며, 임베딩/저장이 완료되면 컬렉션 카운트만 확인하면 됩니다.

---
이 구조를 따르면 PDF → 추출 → 청킹 → 임베딩 저장까지 한 번에 운용 가능합니다. 필요한 추가 섹션(검색 테스트, 질의 엔드포인트 등)이 있으면 알려주세요. 