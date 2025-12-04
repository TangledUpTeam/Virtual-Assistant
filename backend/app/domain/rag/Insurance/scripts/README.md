# Insurance RAG Scripts

이 디렉토리는 PDF 추출 → 청킹 → 임베딩/저장 3단계 파이프라인을 실행하기 위한 최소 스크립트를 제공합니다.

## 요구사항

- Python 환경: conda env `dy`
- 환경변수: `backend/.env`에 `OPENAI_API_KEY` 설정

## 1) 추출 (extracted_pages.json)

```bash
cd C:\dev\himedia\Virtual-Assistant\backend\app\domain\rag\Insurance\scripts
python run_extract_pdf.py  # 있으면 사용, 없으면 이미 생성된 extracted_pages.json 사용
```

## 2) 청킹 (chunks.json + runs 로그)

```bash
python run_chunking.py
```

- 산출물: `scripts/chunks.json` (최신본)
- 실행 로그/결과: `scripts/runs/<YYYYMMDD-HHMMSS>/chunks.json`, `summary.txt`

## 3) 임베딩/저장 (Chroma)

```bash
python run_embed_store.py --chunks scripts/chunks.json --reset  # 필요 시 초기화
```

- 실행 로그/결과: `scripts/runs/<YYYYMMDD-HHMMSS>/embed_summary.txt`
- 컬렉션: `insurance_documents`

## 실패 시 점검

- `.env`에서 `OPENAI_API_KEY` 정의 여부
- 입력 파일 존재: `scripts/extracted_pages.json`, `scripts/chunks.json`
- Chroma 경로: `backend/app/domain/rag/Insurance/chroma_db`

## 디렉토리 정리 원칙

- 핵심 스크립트만 유지: `run_chunking.py`, `run_embed_store.py`, `_utils.py`
- 예제/디버그/구식 러너는 제거 또는 `scripts/runs/backup-<timestamp>/`로 이동
