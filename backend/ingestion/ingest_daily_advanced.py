"""
일일보고서 고급 Ingestion 파이프라인
"""
import os
import sys
import json
import re
from pathlib import Path
from typing import List, Dict, Any, Optional

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv(project_root / ".env")

from app.domain.report.service import ReportProcessingService
from app.domain.report.advanced_chunker import chunk_daily_report
from app.domain.report.metadata_extractor import build_metadata
from ingestion.embed_flexible import embed_texts
from app.infrastructure.vector_store_advanced import get_vector_store


DATA_DIR = project_root / "Data" / "mock_reports" / "daily"
BATCH_SIZE = 100


def parse_single_json_file(file_path: Path) -> Optional[Dict[str, Any]]:
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read().strip()
    
    if not content:
        return None
    
    try:
        return json.loads(content)
    except json.JSONDecodeError as e:
        print(f"  ⚠️  JSON 파싱 오류: {e}")
        return None


def scan_daily_files(base_dir: Path) -> List[Path]:
    txt_files = list(base_dir.rglob("*.txt"))
    return sorted(txt_files)


def ingest_daily_reports_advanced(
    api_key: Optional[str] = None,
    model_type: Optional[str] = None,
    use_llm_refine: bool = True
):
    print("=" * 80)
    print("📊 일일보고서 고급 Ingestion 시작")
    print("=" * 80)
    print()
    
    api_key = api_key or os.getenv("OPENAI_API_KEY")
    model_type = model_type or os.getenv("EMBEDDING_MODEL_TYPE", "openai")
    
    service = ReportProcessingService(api_key=api_key)
    vector_store = get_vector_store()
    
    txt_files = scan_daily_files(DATA_DIR)
    print(f"✅ {len(txt_files)}개 파일 발견")
    print()
    
    all_chunks = []
    
    for idx, file_path in enumerate(txt_files):
        print(f"[{idx+1}/{len(txt_files)}] 처리 중: {file_path.name}")
        
        raw_json = parse_single_json_file(file_path)
        if not raw_json:
            print(f"  ⚠️  JSON 파싱 실패")
            continue
        
        try:
            canonical = service.normalize_daily(raw_json)
            chunks = chunk_daily_report(canonical, api_key, use_llm_refine)
            
            for chunk in chunks:
                chunk["metadata"] = build_metadata(chunk, canonical)
            
            all_chunks.extend(chunks)
            print(f"  ✅ {len(chunks)}개 청크 생성")
        
        except Exception as e:
            print(f"  ❌ 오류: {e}")
            continue
    
    print()
    print(f"총 {len(all_chunks)}개 청크 생성 완료")
    print()
    
    print("⏳ 임베딩 생성 중...")
    texts = [chunk["text"] for chunk in all_chunks]
    embeddings = embed_texts(texts, model_type, api_key, BATCH_SIZE)
    print(f"✅ {len(embeddings)}개 임베딩 생성 완료")
    print()
    
    print("⏳ VectorDB 저장 중...")
    vector_store.insert_chunks(all_chunks, embeddings)
    print("✅ 저장 완료")
    print()


if __name__ == "__main__":
    ingest_daily_reports_advanced()

