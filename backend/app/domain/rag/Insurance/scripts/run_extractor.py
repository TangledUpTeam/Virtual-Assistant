#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Step 1: Extract PDF pages into extracted_pages.json with runs logging."""

import argparse
import json
import sys
from pathlib import Path
from dotenv import load_dotenv
from _utils import timestamp, ensure_dir, write_json, write_text

SCRIPT_DIR = Path(__file__).parent
INSURANCE_ROOT = SCRIPT_DIR.parent
BACKEND_ROOT = INSURANCE_ROOT.parent.parent.parent.parent

# .env 로드 (OPENAI_API_KEY 등)
load_dotenv(BACKEND_ROOT / ".env")

# import 경로 추가
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.domain.rag.Insurance.services.document_processor.extractor import PDFExtractor, PageResult

OUTPUT_JSON = SCRIPT_DIR / "extracted_pages.json"
DOCUMENTS_DIR = INSURANCE_ROOT / "documents"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extract PDF(s) into JSON pages for RAG pipeline")
    parser.add_argument("--pdf", help="Path to input PDF file (optional). If omitted, processes all PDFs in documents/")
    parser.add_argument("--max_pages", type=int, default=0, help="Limit number of pages (0 = all)")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    # Determine input list
    pdf_list: list[Path] = []
    if args.pdf:
        pdf_path = Path(args.pdf)
        pdf_list = [pdf_path]
    else:
        # Collect all PDFs under Insurance/documents
        ensure_dir(DOCUMENTS_DIR)
        pdf_list = sorted(DOCUMENTS_DIR.glob("**/*.pdf"))
    
    if not pdf_list:
        print(f"❌ No PDF files found. Provide --pdf or place files under {DOCUMENTS_DIR}")
        sys.exit(1)

    print("=" * 80)
    print("[1/4] PDF Extraction")
    print("=" * 80)
    print(f"Input source: {args.pdf or DOCUMENTS_DIR}")

    # Runs logging setup
    run_id = timestamp()
    run_dir = SCRIPT_DIR / "runs" / run_id
    ensure_dir(run_dir)
    run_json = run_dir / "extracted_pages.json"
    run_summary = run_dir / "summary.txt"

    extractor = PDFExtractor()
    all_pages: list[dict] = []

    try:
        for pdf_path in pdf_list:
            if not pdf_path.exists():
                print(f"   ❌ Skipping missing: {pdf_path}")
                continue
            print(f"   · Extracting: {pdf_path}")
            # Fast mode: disable Vision for speed unless explicitly needed
            pages: list[PageResult] = extractor.extract_pdf(pdf_path=str(pdf_path), use_vision=False)
            if args.max_pages and args.max_pages > 0:
                pages = pages[:args.max_pages]
            pages_dict = [p.to_dict() for p in pages]
            # annotate source in metadata-like manner
            for d in pages_dict:
                d.setdefault("source", str(pdf_path))
            print(f"     ✓ {len(pages_dict)} pages")
            all_pages.extend(pages_dict)

        print(f"✓ Total extracted pages: {len(all_pages)}")

        # Save outputs (aggregate)
        write_json(run_json, all_pages)
        write_json(OUTPUT_JSON, all_pages)  # latest copy for next step

        # Summary
        modes = {}
        for p in all_pages:
            modes[p.get("mode", "unknown")] = modes.get(p.get("mode", "unknown"), 0) + 1
        summary = (
            f"Sources: {len(pdf_list)} PDFs\n"
            f"Pages: {len(all_pages)}\n"
            f"Modes: {json.dumps(modes, ensure_ascii=False)}\n"
            f"Output(latest): {OUTPUT_JSON}\n"
            f"Output(run): {run_json}\n"
        )
        write_text(run_summary, summary)
        print(f"✓ Saved: {run_json}")
        print(f"✓ Latest: {OUTPUT_JSON}")
        print("Done. Next: run_chunking.py")
    except Exception as e:
        write_text(run_summary, f"Failed: {e}")
        print(f"❌ Extraction failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
