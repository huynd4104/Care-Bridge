"""Remove documents that are not about maternal & newborn care from the AI Nurse knowledge base.

Why this exists: the 2026-09-22 audit (04_Implement/AINursePromptAudit) found ~16% of the corpus was off-domain -
school sexuality-education curricula, gender-based-violence case management, elderly-care market reports,
population reports, bioterrorism, hospital history pages, IPC facility checklists, food-tax policy. Chunks tagged
`ALL` from those documents competed in *every* retrieval, and some of them won (e.g. "Thuốc lá và đái tháo đường"
surfacing for a pre-eclampsia question).

The list of documents is curated by hand in data/off_domain_manifest.tsv (group, file, title, chunks). Chunks are
matched by EXACT title - never a substring - so a kept document can never be caught by accident.

Deleting rows is irreversible without re-embedding (Gemini quota), so --apply always writes every targeted row,
embedding included, to reports/backups/ first. --restore puts them back byte-for-byte.

Usage:
    python scripts/prune_off_domain_documents.py              # dry run (default): report only
    python scripts/prune_off_domain_documents.py --apply      # backup -> delete DB rows -> delete source files
    python scripts/prune_off_domain_documents.py --restore reports/backups/off_domain_prune_<ts>.jsonl.gz
"""

from __future__ import annotations

import argparse
import asyncio
import gzip
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text

from app.config import RAW_DOCS_DIR
from app.core.database import AsyncSessionLocal

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

SERVICE_ROOT = Path(__file__).resolve().parent.parent
MANIFEST_PATH = SERVICE_ROOT / "data" / "off_domain_manifest.tsv"
BACKUP_DIR = SERVICE_ROOT / "reports" / "backups"

_COLUMNS = "id, title, stage, topic, source, section, content, chunk_index, embedding::text AS embedding, created_at"


def load_manifest(path: Path = MANIFEST_PATH) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    header: list[str] | None = None
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        cells = line.split("\t")
        if header is None:
            header = cells
            continue
        rows.append(dict(zip(header, cells)))
    titles = [r["title"] for r in rows]
    if len(set(titles)) != len(titles):
        raise SystemExit("Manifest has duplicate titles - refusing to continue.")
    return rows


async def count_by_title(titles: list[str]) -> dict[str, int]:
    async with AsyncSessionLocal() as s:
        result = await s.execute(
            text("SELECT title, count(*) FROM maternal_knowledge_chunks WHERE title = ANY(:t) GROUP BY title"),
            {"t": titles},
        )
        return {title: n for title, n in result.all()}


async def apply(manifest: list[dict[str, str]]) -> None:
    titles = [r["title"] for r in manifest]
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    backup_path = BACKUP_DIR / f"off_domain_prune_{datetime.now():%Y%m%d_%H%M%S}.jsonl.gz"

    async with AsyncSessionLocal() as s:
        total_before = (await s.execute(text("SELECT count(*) FROM maternal_knowledge_chunks"))).scalar_one()
        result = await s.execute(
            text(f"SELECT {_COLUMNS} FROM maternal_knowledge_chunks WHERE title = ANY(:t) ORDER BY id"),
            {"t": titles},
        )
        backed_up = 0
        with gzip.open(backup_path, "wt", encoding="utf-8") as fh:
            for row in result.mappings():
                record = dict(row)
                record["created_at"] = record["created_at"].isoformat() if record["created_at"] else None
                fh.write(json.dumps(record, ensure_ascii=False) + "\n")
                backed_up += 1
        logger.info("Backed up %d rows (with embeddings) to %s", backed_up, backup_path)

        deleted = (
            await s.execute(text("DELETE FROM maternal_knowledge_chunks WHERE title = ANY(:t)"), {"t": titles})
        ).rowcount
        if deleted != backed_up:
            await s.rollback()
            raise SystemExit(f"Deleted {deleted} rows but backed up {backed_up} - rolled back.")
        await s.commit()
        total_after = (await s.execute(text("SELECT count(*) FROM maternal_knowledge_chunks"))).scalar_one()

    logger.info("DB chunks: %d -> %d (removed %d)", total_before, total_after, deleted)

    removed_files = 0
    for r in manifest:
        path = Path(RAW_DOCS_DIR) / r["file"]
        if path.exists():
            path.unlink()
            removed_files += 1
    logger.info("Removed %d source files from %s", removed_files, RAW_DOCS_DIR)
    logger.info("Restore with: python scripts/prune_off_domain_documents.py --restore %s", backup_path)


async def restore(backup_path: Path) -> None:
    restored = 0
    async with AsyncSessionLocal() as s:
        with gzip.open(backup_path, "rt", encoding="utf-8") as fh:
            for line in fh:
                record = json.loads(line)
                record["created_at"] = datetime.fromisoformat(record["created_at"]) if record["created_at"] else None
                await s.execute(
                    text(
                        "INSERT INTO maternal_knowledge_chunks "
                        "(id, title, stage, topic, source, section, content, chunk_index, embedding, created_at) "
                        "VALUES (:id, :title, :stage, :topic, :source, :section, :content, :chunk_index, "
                        "CAST(:embedding AS vector), :created_at) ON CONFLICT (id) DO NOTHING"
                    ),
                    record,
                )
                restored += 1
        await s.commit()
    logger.info("Restored %d rows from %s (source files: `git checkout` them back)", restored, backup_path)


async def main() -> None:
    parser = argparse.ArgumentParser(description="Prune off-domain documents from the AI Nurse knowledge base.")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--apply", action="store_true", help="Back up, then delete the DB rows and source files.")
    group.add_argument("--restore", type=Path, help="Re-insert rows from a backup written by --apply.")
    args = parser.parse_args()

    if args.restore:
        await restore(args.restore)
        return

    manifest = load_manifest()
    counts = await count_by_title([r["title"] for r in manifest])
    files_present = sum(1 for r in manifest if (Path(RAW_DOCS_DIR) / r["file"]).exists())
    logger.info(
        "Manifest: %d documents | in DB: %d titles, %d chunks | source files present: %d",
        len(manifest), len(counts), sum(counts.values()), files_present,
    )
    if not args.apply:
        logger.info("Dry run - nothing changed. Re-run with --apply to delete.")
        return
    await apply(manifest)


if __name__ == "__main__":
    asyncio.run(main())
