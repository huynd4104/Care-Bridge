"""Offline tests for retrieval helpers and idempotent ingestion (no database, no API)."""

import pytest

from app.models.schemas import DocumentChunkDTO
from app.rag.vector_store import (
    PgVectorStore,
    _fold_accents,
    _is_unaccented,
    contains_word,
    searchable_stages,
)


def test_postpartum_stage_can_reach_newborn_documents():
    assert "BABY_CARE" in searchable_stages("POSTPARTUM")
    assert searchable_stages("ALL") is None and searchable_stages(None) is None


def test_pregnancy_stage_can_reach_newborn_documents():
    """Mothers prepare for newborn care before birth; pinning BABY_CARE to POSTPARTUM hid 123 documents."""
    stages = searchable_stages("PREGNANCY")
    assert stages is not None
    assert set(stages) == {"PREGNANCY", "ALL", "BABY_CARE"}


def test_contains_word_uses_whole_words():
    assert contains_word("ối", "rỉ ối và vỡ ối sớm")
    assert not contains_word("ối", "buổi tối mệt")          # substring inside another word
    assert not contains_word("do", "liều dose cao")
    assert contains_word("huyết áp", "đo huyết áp tại nhà")


def test_unaccented_detection_and_folding():
    assert _is_unaccented("bau 32 tuan do huyet ap 150/100")
    assert not _is_unaccented("bầu 32 tuần đo huyết áp")
    assert _fold_accents("đau đầu dữ dội") == "dau dau du doi"
    assert contains_word("huyet ap", _fold_accents("đo huyết áp tại nhà"))


class _FakeEmbedder:
    async def embed_documents(self, texts):
        return [[0.0] * 3 for _ in texts]


def _chunk(title, content, idx=0):
    return DocumentChunkDTO(title=title, stage="ALL", topic="GENERAL", source="s", section=None,
                            content=content, chunk_index=idx)


class _FakeSession:
    """Minimal async session that applies delete-by-title / add / commit to an in-memory table."""

    def __init__(self, fail_commit=False):
        self.rows, self._pending, self.fail_commit = [], [], fail_commit

    async def execute(self, stmt):
        titles = set(stmt.whereclause.right.value)  # title IN (...)
        self._pending.append(("delete", titles))

    def add(self, obj):
        self._pending.append(("add", obj))

    async def commit(self):
        if self.fail_commit:
            self._pending.clear()
            raise ConnectionError("commit failed")
        for op, arg in self._pending:
            if op == "delete":
                self.rows = [r for r in self.rows if r.title not in arg]
            else:
                self.rows.append(arg)
        self._pending.clear()


def _store():
    store = PgVectorStore()
    store.embedder = _FakeEmbedder()
    return store


@pytest.mark.asyncio
async def test_reingesting_a_document_replaces_instead_of_duplicating():
    """Root cause of 13,399 duplicate chunks: ingestion appended without removing the previous copy."""
    store, db = _store(), _FakeSession()
    doc = [_chunk("Cẩm nang A", "nội dung 1", 0), _chunk("Cẩm nang A", "nội dung 2", 1)]
    other = [_chunk("Cẩm nang A - Phụ lục", "phụ lục", 0)]
    for batch in (doc, other, doc):
        await store.replace_document_chunks(batch, session=db)
    titles = [r.title for r in db.rows]
    assert titles.count("Cẩm nang A") == 2           # replaced, not appended twice
    assert titles.count("Cẩm nang A - Phụ lục") == 1   # exact-title match leaves similarly named docs alone
    assert [c["title"] for c in store._local_cache].count("Cẩm nang A") == 2


@pytest.mark.asyncio
async def test_failed_commit_leaves_memory_cache_untouched():
    store = _store()
    with pytest.raises(ConnectionError):
        await store.replace_document_chunks([_chunk("Cẩm nang B", "x", 0)], session=_FakeSession(fail_commit=True))
    assert store._local_cache == []


@pytest.mark.asyncio
async def test_unaccented_query_terms_match_accented_chunks_via_folded_index():
    """TC-VAR-02 / TC-VAR-09 (run 2026-09-19): typed without diacritics, SQL ILIKE found nothing -> refusal."""
    store = _store()
    store._folded_index = [
        (1, "PREGNANCY", "NUTRITION", "dinh duong", _fold_accents("uống sắt 30-60 mg và axit folic mỗi ngày")),
        (2, "PREGNANCY", "NUTRITION", "dinh duong", _fold_accents("sắt nguyên tố cho bà bầu, bài rất dài " * 5)),
        (3, "BABY_CARE", "NEWBORN", "so sinh", _fold_accents("uống sắt và axit folic")),
        (4, "PREGNANCY", "LIFESTYLE", "loi song", _fold_accents("nằm nghiêng trái khi ngủ")),
    ]
    ids = await store._folded_keyword_ids([(False, ["sat", "axit folic"], 40)], ["PREGNANCY", "ALL"], None)
    assert ids == [1, 2]  # both terms beat one term; other stage excluded; unrelated chunk not returned


@pytest.mark.asyncio
async def test_folded_index_is_dropped_when_chunks_change():
    store, db = _store(), _FakeSession()
    store._folded_index = [(1, "ALL", "GENERAL", "a", "b")]
    await store.replace_document_chunks([_chunk("Cẩm nang C", "x", 0)], session=db)
    assert store._folded_index is None


class _RecordingSession:
    """Captures the keyword terms search sends; returns no rows."""

    async def execute(self, stmt):
        class _R:
            def all(self):
                return []
        return _R()

    def begin_nested(self):
        class _Ctx:
            async def __aenter__(self): return self
            async def __aexit__(self, *a): return False
        return _Ctx()


@pytest.mark.asyncio
async def test_unaccented_fillers_do_not_take_keyword_slots(monkeypatch):
    store = _store()
    store.embedder.embed_query = lambda q: _async([0.0] * 3)
    seen = {}

    async def fake_ids(specs, stages, topic):
        seen["specs"] = specs
        return []
    monkeypatch.setattr(store, "_folded_keyword_ids", fake_ids)
    await store.similarity_search("ba bau moi ngay uong bao nhieu sat va axit folic", session=_RecordingSession())
    keywords = seen["specs"][-1][1]
    assert {"sat", "axit", "folic", "uong"} <= set(keywords)
    assert not {"moi", "nhieu", "bau"} & set(keywords)  # same fillers the accented query drops
    # a folded stopword that is also a clinical word is kept ("nằm" vs "năm")
    await store.similarity_search("bau 30 tuan nen nam ngu tu the nao", session=_RecordingSession())
    assert "nam" in seen["specs"][-1][1]


async def _async(value):
    return value
