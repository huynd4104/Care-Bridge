"""Backfill: map already-stored chunk `stage` values onto the canonical retrievable vocabulary.

Retrieval filters by `stage`, so a chunk stored under a value outside RETRIEVABLE_STAGES can never be
returned by a search. Document frontmatter had drifted far from the enum ("GENERAL",
"PREGNANCY,POSTPARTUM", free-text Vietnamese such as "THAI KỲ; SAU SINH"), leaving 125 of the 557
documents that declare a stage permanently invisible to the assistant.

app/rag/chunker.py now normalises at ingest time, but rows written before that change still carry the
old values. This script rewrites them in place - no re-embedding, no re-ingestion, only the stage
column changes.

Usage:
    python scripts/normalize_chunk_stages.py --dry-run   # report what would change
    python scripts/normalize_chunk_stages.py             # apply
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

from sqlalchemy import func, select, update

from app.constants.stages import RETRIEVABLE_STAGES, classify_stage
from app.core.database import AsyncSessionLocal
from app.models.db_models import MaternalKnowledgeChunk

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


async def normalize_stages(dry_run: bool = False, include_unknown: bool = False) -> int:
    async with AsyncSessionLocal() as session:
        rows = (
            await session.execute(
                select(MaternalKnowledgeChunk.stage, func.count(MaternalKnowledgeChunk.id))
                .group_by(MaternalKnowledgeChunk.stage)
            )
        ).all()

        if not rows:
            logger.warning("No knowledge chunks found; nothing to normalize.")
            return 0

        total = sum(count for _, count in rows)
        unreachable_before = sum(
            count for stage, count in rows if (stage or "").upper() not in RETRIEVABLE_STAGES
        )
        logger.info(
            "Found %d chunks across %d distinct stage values (%d chunks currently unreachable).",
            total, len(rows), unreachable_before,
        )

        planned: list[tuple[str, str, int]] = []
        unrecognised: list[tuple[str, int]] = []
        for stage, count in sorted(rows, key=lambda r: -r[1]):
            target, recognised = classify_stage(stage)
            if target == stage:
                continue
            if not recognised and not include_unknown:
                # Nothing in the value matched maternal vocabulary. Rewriting it to ALL would put
                # off-domain material ("OLDER_ADULTS", "MENOPAUSE", "GENERAL") into every retrieval.
                unrecognised.append((stage, count))
                continue
            planned.append((stage, target, count))
            logger.info("  %-55s -> %-14s (%d chunks)", (stage or "<null>")[:55], target, count)

        if unrecognised:
            total_unknown = sum(c for _, c in unrecognised)
            logger.warning(
                "SKIPPED %d chunks across %d stage values whose vocabulary is not maternal "
                "(they stay unreachable). These need a human curation decision - see the audit report. "
                "Only if you accept the precision risk: re-run with --include-unknown to force them all to ALL:",
                total_unknown, len(unrecognised),
            )
            for stage, count in unrecognised:
                logger.warning("  [skipped] %-45s (%d chunks)", (stage or "<null>")[:45], count)

        if not planned:
            logger.info("No recognised stage values need rewriting.")
            return 0

        affected = sum(count for _, _, count in planned)
        if dry_run:
            logger.info("[DRY RUN] Would update %d chunks across %d stage values.", affected, len(planned))
            return affected

        # The UPDATE below discards the previous stage values, so snapshot them first (same pattern as
        # reports/db_dedup_backup_ids_*.json from the de-duplication work). Restoring is a straight
        # replay of this file if the taxonomy change turns out to hurt retrieval precision.
        changed_stages = [old for old, _new, _count in planned]
        backup_rows = (
            await session.execute(
                select(MaternalKnowledgeChunk.id, MaternalKnowledgeChunk.stage)
                .where(MaternalKnowledgeChunk.stage.in_(changed_stages))
            )
        ).all()
        reports_dir = Path(__file__).resolve().parent.parent / "reports"
        reports_dir.mkdir(exist_ok=True)
        backup_path = reports_dir / f"stage_backfill_backup_{datetime.now():%Y%m%d_%H%M%S}.json"
        backup_path.write_text(
            json.dumps(
                {
                    "created_at": datetime.now().isoformat(timespec="seconds"),
                    "mapping": [{"from": o, "to": n, "chunks": c} for o, n, c in planned],
                    "chunks": [{"id": cid, "stage": stage} for cid, stage in backup_rows],
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        logger.info("Backed up %d previous stage values to %s", len(backup_rows), backup_path)

        for old_stage, new_stage, _count in planned:
            await session.execute(
                update(MaternalKnowledgeChunk)
                .where(MaternalKnowledgeChunk.stage == old_stage)
                .values(stage=new_stage)
            )
        await session.commit()

        after = (
            await session.execute(
                select(MaternalKnowledgeChunk.stage, func.count(MaternalKnowledgeChunk.id))
                .group_by(MaternalKnowledgeChunk.stage)
            )
        ).all()
        still_unreachable = sum(
            count for stage, count in after if (stage or "").upper() not in RETRIEVABLE_STAGES
        )
        logger.info("Updated %d chunks. New distribution: %s", affected, dict(Counter(dict(after))))
        if still_unreachable:
            logger.error("%d chunks are STILL unreachable - inspect their stage values.", still_unreachable)
        else:
            logger.info("Every chunk is now retrievable.")
        return affected


async def main() -> None:
    parser = argparse.ArgumentParser(description="Normalize stored chunk stages onto the canonical vocabulary.")
    parser.add_argument("--dry-run", action="store_true", help="Report the changes without applying them.")
    parser.add_argument(
        "--include-unknown",
        action="store_true",
        help="Also rewrite stage values whose vocabulary is not maternal (forces them to ALL). "
             "Off by default: it makes off-domain material compete in every retrieval.",
    )
    args = parser.parse_args()

    affected = await normalize_stages(dry_run=args.dry_run, include_unknown=args.include_unknown)
    print("\n" + "=" * 60)
    print(f"{'[DRY RUN] would update' if args.dry_run else 'Updated'}: {affected} chunks")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
