"""Tests for DocumentChunker and Ingestion Pipeline."""

import os

import pytest

from app.config import RAW_DOCS_DIR
from app.models.schemas import DocumentChunkDTO
from app.rag.chunker import DocumentChunker
from app.services.ingestion_service import IngestionService


def test_document_chunker_markdown_file():
    chunker = DocumentChunker(chunk_size=500, chunk_overlap=100)
    files = list(RAW_DOCS_DIR.glob("*.md"))
    assert len(files) > 0, "Expected at least 1 markdown file in raw_documents"

    sample_file = files[0]
    chunks = chunker.chunk_file(sample_file)
    assert len(chunks) > 0
    first_chunk = chunks[0]
    assert first_chunk.title is not None
    assert first_chunk.content is not None
    assert len(first_chunk.content) > 0


class _RecordingVectorStore:
    """Captures what ingestion would write instead of touching the real database."""

    def __init__(self) -> None:
        self.written: list[DocumentChunkDTO] = []

    async def get_existing_titles(self, session=None) -> set[str]:
        return set()          # nothing exists yet, so every document is processed

    async def replace_document_chunks(self, chunks, session=None) -> int:
        self.written.extend(chunks)
        return len(chunks)

    async def add_chunks(self, chunks, session=None) -> int:
        self.written.extend(chunks)
        return len(chunks)


@pytest.mark.asyncio
async def test_batch_ingestion_directory(tmp_path):
    """Ingest a temporary corpus through a fake store.

    This test used to call ingest_directory() against data/raw_documents with the real vector store, so
    running pytest re-ingested the whole knowledge base into whatever database the environment pointed
    at. On 2026-09-22 that silently rewrote ~13.5k chunk stages in the working database. The pipeline is
    now exercised against a temporary directory and an in-memory store; nothing leaves the test process.
    """
    (tmp_path / "cam_nang_test.md").write_text(
        "---\ntitle: Cẩm nang kiểm thử\nstage: PREGNANCY\ntopic: NUTRITION\n---\n\n"
        "## Bổ sung vi chất\n\nMẹ bầu nên bổ sung axit folic mỗi ngày theo chỉ định của Bác sĩ. " * 20,
        encoding="utf-8",
    )
    (tmp_path / "cham_soc_be.md").write_text(
        "---\ntitle: Chăm sóc bé\nstage: BABY_CARE\n---\n\n"
        "## Theo dõi trẻ sơ sinh\n\nTheo dõi thân nhiệt và bú mẹ của trẻ sơ sinh hằng ngày. " * 20,
        encoding="utf-8",
    )

    service = IngestionService()
    store = _RecordingVectorStore()
    service.vector_store = store

    result = await service.ingest_directory(tmp_path)

    assert result.success is True
    assert result.total_files_processed == 2
    assert result.total_chunks_created > 0
    assert len(store.written) == result.total_chunks_created
    # Stage normalisation must happen on the ingest path, not only in the backfill script.
    assert {c.stage for c in store.written} == {"PREGNANCY", "BABY_CARE"}


@pytest.mark.skipif(
    os.getenv("RUN_REAL_INGESTION_TESTS") != "1",
    reason="Writes to the configured database and calls the embedding API. "
           "Set RUN_REAL_INGESTION_TESTS=1 to opt in.",
)
@pytest.mark.asyncio
async def test_batch_ingestion_directory_against_real_database():
    """Opt-in end-to-end ingestion. Never runs by default: it mutates real data."""
    service = IngestionService()
    result = await service.ingest_directory(RAW_DOCS_DIR)
    assert result.success is True
