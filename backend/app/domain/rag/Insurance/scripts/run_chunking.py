#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
2단계: 청킹

extracted_pages.json을 읽어서 청킹 후 chunks.json으로 저장
"""

import sys
import json
import time
from pathlib import Path
import tiktoken
from _utils import timestamp, ensure_dir, write_json, write_text

# 경로 설정
script_dir = Path(__file__).resolve().parent
backend_root = script_dir.parent.parent.parent.parent.parent

if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))

# 입출력 경로
INPUT_JSON = script_dir / "extracted_pages.json"
OUTPUT_JSON = script_dir / "chunks.json"
RUN_ID = timestamp()
RUN_DIR = script_dir / "runs" / RUN_ID

# 토큰화 설정
MAX_TOKENS = 800
OVERLAP_TOKENS = 120
ENCODING = tiktoken.get_encoding("cl100k_base")


def chunk_text(text: str, max_tokens: int = MAX_TOKENS, overlap: int = OVERLAP_TOKENS):
    """텍스트를 토큰 단위로 청킹"""
    if not text or not text.strip():
        return []
    
    try:
        tokens = ENCODING.encode(text)
    except Exception:
        return []
    
    # 짧으면 그대로 반환
    if len(tokens) <= max_tokens:
        return [text]
    
    chunks = []
    stride = max_tokens - overlap
    
    # stride 최소값 보장
    if stride < 100:
        stride = 100
    
    # 간단한 범위 기반 청킹
    for start_idx in range(0, len(tokens), stride):
        end_idx = min(start_idx + max_tokens, len(tokens))
        chunk_tokens = tokens[start_idx:end_idx]
        
        try:
            decoded_chunk = ENCODING.decode(chunk_tokens)
            if len(decoded_chunk.strip()) >= 20:
                chunks.append(decoded_chunk)
        except Exception:
            continue
        
        # 마지막 청크면 종료
        if end_idx >= len(tokens):
            break
    
    return chunks


def main() -> None:
    print("=" * 80)
    print("2단계: 청킹")
    print("=" * 80)

    # 1. 입력 파일 확인
    print(f"\n[1] 입력 파일 확인: {INPUT_JSON}")
    if not INPUT_JSON.exists():
        print(f"❌ {INPUT_JSON.name} 파일이 없습니다.")
        sys.exit(1)
    print("✓ 파일 존재")

    # 2. JSON 로드
    print(f"\n[2] JSON 로드 중...")
    overall_start = time.perf_counter()
    try:
        with open(INPUT_JSON, "r", encoding="utf-8") as f:
            pages = json.load(f)
        print(f"✓ {len(pages)}개 페이지 로드")
    except Exception as e:
        print(f"❌ JSON 로드 실패: {e}")
        sys.exit(1)

    # 3. 청킹 시작
    print(f"\n[3] 청킹 시작...")
    print(f"   - max_tokens: {MAX_TOKENS}")
    print(f"   - overlap_tokens: {OVERLAP_TOKENS}")

    all_chunks = []
    empty_pages = 0
    chunk_start = time.perf_counter()

    for idx, page_data in enumerate(pages, start=1):
        page_num = page_data.get("page", 0)
        content = page_data.get("content", "").strip()

        # 진행상황 출력
        if idx % 20 == 0 or idx == 1:
            elapsed = time.perf_counter() - chunk_start
            print(f"   · 처리 중: {idx}/{len(pages)} | 누적 {elapsed:.1f}s | 청크 {len(all_chunks)}개")

        if not content:
            empty_pages += 1
            continue

        try:
            # 청킹
            chunk_texts = chunk_text(content, MAX_TOKENS, OVERLAP_TOKENS)
            
            if not chunk_texts:
                continue

            # 메타데이터 추가
            for i, chunk_content in enumerate(chunk_texts):
                chunk_dict = {
                    "id": f"page{page_num}_chunk{i}",
                    "content": chunk_content,
                    "metadata": {
                        "page": page_num,
                        "chunk_index": i,
                        "source": "insurance_manual.pdf"
                    }
                }
                all_chunks.append(chunk_dict)
        
        except Exception as e:
            print(f"   ❌ 페이지 {idx} 에러: {e}")
            continue

    chunk_duration = time.perf_counter() - chunk_start
    print("✓ 청킹 완료")
    print(f"   - 처리된 페이지: {len(pages) - empty_pages}/{len(pages)}")
    print(f"   - 빈 페이지: {empty_pages}")
    print(f"   - 생성된 청크: {len(all_chunks)}개")
    print(f"   - 청킹 소요 시간: {chunk_duration:.2f}s")

    # 4. 결과 저장 (runs/<ts>/chunks.json + latest copy)
    print(f"\n[4] 결과 저장 중...")
    ensure_dir(RUN_DIR)
    run_chunks = RUN_DIR / "chunks.json"
    run_summary = RUN_DIR / "summary.txt"
    save_start = time.perf_counter()
    try:
        write_json(run_chunks, all_chunks)
        # latest 복사본 유지
        write_json(OUTPUT_JSON, all_chunks)
        save_duration = time.perf_counter() - save_start
        summary = (
            f"처리된 페이지: {len(pages) - empty_pages}/{len(pages)}\n"
            f"빈 페이지: {empty_pages}\n"
            f"생성된 청크: {len(all_chunks)}개\n"
            f"청킹 소요 시간: {chunk_duration:.2f}s\n"
            f"입력: {INPUT_JSON}\n"
            f"출력(latest): {OUTPUT_JSON}\n"
            f"출력(run): {run_chunks}\n"
        )
        write_text(run_summary, summary)
        print(f"✓ 저장 완료: {run_chunks} (소요: {save_duration:.2f}s)")
    except Exception as e:
        print(f"❌ 저장 실패: {e}")
        sys.exit(1)

    total_duration = time.perf_counter() - overall_start
    print("\n" + "=" * 80)
    print("✅ 청킹 완료!")
    print("=" * 80)
    print(f"총 소요 시간: {total_duration:.2f}s")
    print(f"\n다음 단계: run_embed_store.py 실행")


if __name__ == "__main__":
    main()
