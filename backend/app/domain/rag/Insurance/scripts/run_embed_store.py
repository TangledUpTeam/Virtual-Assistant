#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Step 3: Embed chunks and persist them to ChromaDB with runs logging."""

import argparse
import json
import shutil
import sys
from pathlib import Path
from dotenv import load_dotenv
from _utils import timestamp, ensure_dir, write_text

SCRIPT_DIR = Path(__file__).parent
INSURANCE_ROOT = SCRIPT_DIR.parent
BACKEND_ROOT = INSURANCE_ROOT.parent.parent.parent.parent
CHROMA_DIR = INSURANCE_ROOT / "chroma_db"

# .env 로드
load_dotenv(BACKEND_ROOT / ".env")

sys.path.insert(0, str(BACKEND_ROOT))

from app.domain.rag.Insurance.core.models import InsuranceDocument
from app.domain.rag.Insurance.infrastructure.embeddings.openai import OpenAIEmbeddingProvider
from app.domain.rag.Insurance.infrastructure.vectorstore.chroma import ChromaVectorStore


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Embed chunks.json into ChromaDB")
    parser.add_argument(
        "--chunks",
        default=str(SCRIPT_DIR / "chunks.json"),
        help="Path to chunks.json"
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Start from a clean Chroma directory"
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    chunks_path = Path(args.chunks)
    print("=" * 80)
    print("[3/4] Embedding & Storing Chunks")
    print("=" * 80)
    print(f"Using Chroma directory: {CHROMA_DIR}")

    RUN_ID = timestamp()
    RUN_DIR = SCRIPT_DIR / "runs" / RUN_ID
    ensure_dir(RUN_DIR)
    summary_path = RUN_DIR / "embed_summary.txt"

    try:
        # Load chunks
        with open(chunks_path, "r", encoding="utf-8") as f:
            chunks = json.load(f)
        print(f"Loaded {len(chunks)} chunks from {chunks_path}")

        # Optional reset
        if args.reset and CHROMA_DIR.exists():
            print("Resetting Chroma directory...")
            shutil.rmtree(CHROMA_DIR, ignore_errors=True)
        CHROMA_DIR.mkdir(parents=True, exist_ok=True)

        # Init providers
        embedder = OpenAIEmbeddingProvider()
        store = ChromaVectorStore(persist_directory=str(CHROMA_DIR), collection_name="insurance_documents")

        # Prepare documents and compute embeddings
        import time as _t
        start = _t.perf_counter()
        documents = [
            InsuranceDocument(id=c.get("id"), content=c.get("content", ""), metadata=c.get("metadata", {}))
            for c in chunks
        ]
        if documents:
            texts = [doc.content for doc in documents]
            embeddings = embedder.embed_texts(texts)
            store.add_documents(documents, embeddings)
        duration = _t.perf_counter() - start

        # Collection stats
        count = store.get_document_count()
        summary = (
            f"Chunks: {len(chunks)}\n"
            f"Collection: insurance_documents\n"
            f"Total docs in collection: {count}\n"
            f"Chroma dir: {CHROMA_DIR}\n"
            f"Embed+Upsert duration: {duration:.2f}s\n"
            f"Input chunks: {chunks_path}\n"
        )
        write_text(summary_path, summary)
        print(f"Done! Collection 'insurance_documents' now has {count} documents")
    except Exception as e:
        write_text(summary_path, f"Failed: {e}")
        print(f"Failed: {e}")
