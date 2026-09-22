"""Restore each stored chunk's `stage` from the stage its source document declares.

Why this exists: `tests/test_ingestion_and_chunker.py::test_batch_ingestion_directory` used to run a real
ingestion against whatever database the environment pointed at. On 2026-09-22 that test re-ingested the
whole corpus while `DocumentChunker` still coerced every unrecognised stage to "ALL", which promoted
~13.5k chunks of non-maternal material (sexuality education, gender-based violence, elderly care,
biosecurity) into the bucket that competes in *every* retrieval.

This script rebuilds the stage column from the source frontmatter under data/raw_documents, applying the
current conservative classifier: values recognised as maternal become canonical, everything else is left
exactly as the document declares it (and therefore stays out of search, which is the intended behaviour).

Only the `stage` column is touched - no re-chunking, no re-embedding, no Gemini calls.

Usage:
    python scripts/restore_stages_from_source.py --dry-run
    python scripts/restore_stages_from_source.py
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import frontmatter
from sqlalchemy import func, select, update

from app.config import RAW_DOCS_DIR
from app.constants.stages import RETRIEVABLE_STAGES, classify_stage
from app.core.database import AsyncSessionLocal
from app.models.db_models import MaternalKnowledgeChunk

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def declared_stage_by_title(docs_dir: Path) -> dict[str, str]:
    """Map document title -> the stage string its own frontmatter declares."""
    declared: dict[str, str] = {}
    for path in sorted(docs_dir.iterdir()):
        if path.suffix.lower() not in (".md", ".markdown"):
            continue
        try:
            post = frontmatter.load(path)
            metadata = post.metadata or {}
        except Exception as exc:  # pragma: no cover - malformed frontmatter
            logger.debug("Skipping %s (%s)", path.name, exc)
            continue

        title = metadata.get("title") or path.stem.replace("_", " ").title()
        raw = metadata.get("stage") or metadata.get("applicableStages")
        if raw is None:
            continue
        if isinstance(raw, (list, tuple, set)):
            raw = ", ".join(str(p).strip() for p in raw if str(p).strip())
        declared[str(title)] = str(raw)
    return declared


async def restore(dry_run: bool = False) -> int:
    docs_dir = Path(RAW_DOCS_DIR)
    if not docs_dir.exists():
        logger.error("Source directory not found: %s", docs_dir)
        return 0

    declared = declared_stage_by_title(docs_dir)
    logger.info("Read a declared stage from %d source documents.", len(declared))
    if not declared:
        logger.error("No source frontmatter found; refusing to touch the database.")
        return 0

    async with AsyncSessionLocal() as session:
        rows = (
            await session.execute(
                select(MaternalKnowledgeChunk.title, MaternalKnowledgeChunk.stage,
                       func.count(MaternalKnowledgeChunk.id))
                .group_by(MaternalKnowledgeChunk.title, MaternalKnowledgeChunk.stage)
            )
        ).all()

        planned: list[tuple[str, str, str, int]] = []   # title, current, target, chunks
        unmatched = 0
        for title, current, count in rows:
            raw = declared.get(title)
            if raw is None:
                unmatched += count
                continue
            canonical, recognised = classify_stage(raw)
            target = canonical if recognised else raw
            if target != current:
                planned.append((title, current, target, count))

        if unmatched:
            logger.info("%d chunks have no matching source document; leaving them untouched.", unmatched)

        if not planned:
            logger.info("Every chunk already matches its source document's stage. Nothing to do.")
            return 0

        affected = sum(c for _, _, _, c in planned)
        demoted = sum(c for _, cur, tgt, c in planned
                      if cur in RETRIEVABLE_STAGES and tgt not in RETRIEVABLE_STAGES)
        summary = Counter((cur, tgt) for _, cur, tgt, _ in planned)
        logger.info("Planned: %d chunks across %d documents (%d stage transitions).",
                    affected, len(planned), len(summary))
        for (cur, tgt), n in summary.most_common(20):
            chunks = sum(c for _, a, b, c in planned if a == cur and b == tgt)
            logger.info("  %-14s -> %-45s  (%d docs, %d chunks)", cur, tgt[:45], n, chunks)
        logger.info("Of these, %d chunks return to a non-searchable stage (intended: off-domain material).",
                    demoted)

        if dry_run:
            logger.info("[DRY RUN] No changes written.")
            return affected

        backup_rows = (
            await session.execute(select(MaternalKnowledgeChunk.id, MaternalKnowledgeChunk.stage))
        ).all()
        reports_dir = Path(__file__).resolve().parent.parent / "reports"
        reports_dir.mkdir(exist_ok=True)
        backup_path = reports_dir / f"stage_restore_backup_{datetime.now():%Y%m%d_%H%M%S}.json"
        backup_path.write_text(
            json.dumps(
                {
                    "created_at": datetime.now().isoformat(timespec="seconds"),
                    "reason": "Restore stages from source frontmatter after an unintended test re-ingestion.",
                    "transitions": [{"title": t, "from": c, "to": g, "chunks": n} for t, c, g, n in planned],
                    "chunks": [{"id": cid, "stage": stage} for cid, stage in backup_rows],
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        logger.info("Backed up %d current stage values to %s", len(backup_rows), backup_path)

        for title, _current, target, _count in planned:
            await session.execute(
                update(MaternalKnowledgeChunk)
                .where(MaternalKnowledgeChunk.title == title)
                .values(stage=target)
            )
        await session.commit()

        after = (
            await session.execute(
                select(MaternalKnowledgeChunk.stage, func.count(MaternalKnowledgeChunk.id))
                .group_by(MaternalKnowledgeChunk.stage)
            )
        ).all()
        searchable = sum(n for st, n in after if (st or "").upper() in RETRIEVABLE_STAGES)
        total = sum(n for _, n in after)
        logger.info("Done. %d/%d chunks searchable across %d distinct stage values.",
                    searchable, total, len(after))
        return affected


async def main() -> None:
    parser = argparse.ArgumentParser(description="Restore chunk stages from their source documents.")
    parser.add_argument("--dry-run", action="store_true", help="Report the changes without applying them.")
    args = parser.parse_args()

    affected = await restore(dry_run=args.dry_run)
    print("\n" + "=" * 60)
    print(f"{'[DRY RUN] would update' if args.dry_run else 'Updated'}: {affected} chunks")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
