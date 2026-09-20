#!/usr/bin/env python3
"""Retrieval-only diagnostic: for every golden case, does the expected source document reach the prompt?

No LLM call (only query embeddings), so it is cheap to run before/after a retrieval change.

Usage:
    python scripts/diagnose_retrieval.py [--top-k 4] [--show-misses]
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

import frontmatter  # noqa: E402

from app.rag.vector_store import get_vector_store  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

SIMILARITY_THRESHOLD = 0.20  # same filter as RagChatService.chat


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default="data/golden_evaluation_dataset.json")
    parser.add_argument("--top-k", type=int, default=4)
    parser.add_argument("--show-misses", action="store_true")
    args = parser.parse_args()

    cases = json.loads((PROJECT_ROOT / args.dataset).read_text(encoding="utf-8"))
    raw_dir = PROJECT_ROOT / "data" / "raw_documents"
    title_of = {}
    store = get_vector_store()
    hits = total = gate = 0
    misses = []
    latencies = []
    for case in cases:
        files = {e["source_file"] for e in case.get("evidence_quotes", [])}
        if not files:
            continue
        expected = set()
        for f in files:
            if f not in title_of:
                title_of[f] = str(frontmatter.load(raw_dir / f).get("title", "")).strip()
            expected.add(title_of[f])
        t0 = time.perf_counter()
        chunks = await store.similarity_search(query=case["question"], stage=case.get("stage") or "PREGNANCY", top_k=args.top_k)
        latencies.append(time.perf_counter() - t0)
        valid = [c for c in chunks if (c.get("similarity") or 0) >= SIMILARITY_THRESHOLD]
        titles = {str(c.get("title", "")).strip() for c in valid}
        total += 1
        gate += not valid
        if expected & titles:
            hits += 1
        else:
            misses.append((case["id"], sorted(expected), sorted(titles)))
    latencies.sort()
    print(f"retrieval hit: {hits}/{total} = {hits / total:.1%} | grounding gate (0 chunks): {gate} | "
          f"latency p50 {latencies[len(latencies) // 2]:.2f}s p95 {latencies[int(len(latencies) * 0.95)]:.2f}s")
    if args.show_misses:
        for cid, exp, got in misses:
            print(f"- {cid}\n    expected: {exp}\n    got:      {[t[:60] for t in got]}")


if __name__ == "__main__":
    asyncio.run(main())
