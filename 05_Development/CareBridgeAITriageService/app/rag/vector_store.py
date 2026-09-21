"""Vector store operations using PostgreSQL pgvector with in-memory fallback."""

from __future__ import annotations

import asyncio
import logging
import re
import unicodedata
from typing import Any, Dict, List, Optional
from sqlalchemy import case, delete, func, literal, or_, select, text, union_all
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import RAW_DOCS_DIR
from app.core.database import AsyncSessionLocal
from app.models.db_models import MaternalKnowledgeChunk
from app.models.schemas import (
    ChunkDetailItem,
    DocumentChunkDTO,
    KnowledgeListResponse,
    KnowledgeStatsResponse,
    SourceCitation,
)
from app.rag.embedder import get_embedder

logger = logging.getLogger(__name__)

DENSE_CANDIDATES = 80

# Newborn documents are ingested with stage BABY_CARE, but chat users are only ever PRECONCEPTION /
# PREGNANCY / POSTPARTUM. A mother asking about her newborn is in the POSTPARTUM stage, so that stage
# must also search BABY_CARE; otherwise those documents can never be retrieved.
# PREGNANCY searches it too: mothers routinely prepare for newborn care before giving birth
# ("trẻ sơ sinh vàng da có sao không?"), and pinning those 123 documents to POSTPARTUM made the
# assistant answer "chưa tìm thấy tài liệu" to a perfectly valid question.
_EXTRA_SEARCH_STAGES = {
    "POSTPARTUM": ("BABY_CARE",),
    "PREGNANCY": ("BABY_CARE",),
}


MAX_CHUNKS_PER_DOCUMENT = 2

# Words that carry no retrieval signal. Module level because RagChatService reuses them to decide
# whether a follow-up question is specific enough to search on its own, and the two must not drift.
GENERAL_STOPWORDS = frozenset({
    "là", "và", "của", "cho", "các", "những", "được", "có", "trong",
    "để", "khi", "ở", "gì", "thế", "nào", "ạ", "nhé", "với", "từ",
    "ra", "vào", "thì", "cần", "nên", "hãy", "bị", "do", "về",
    "cách", "theo", "dõi", "tại", "nhà", "làm", "sao", "bao", "nhiêu",
    "rất", "nhiều", "ít", "hết", "cũng", "đều", "đã", "đang", "sẽ",
    "phải", "mà", "này", "đó", "kia", "lên", "xuống", "lại", "qua",
    "sau", "trước", "giữa", "xin", "giúp", "biết", "thấy", "ai", "đâu",
    "mỗi", "một", "hai", "ba", "bốn", "năm", "sáu", "bảy", "tám", "chín", "mười",
    "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "tỉ", "triệu", "nghìn", "k", "ngàn",
})

# Domain filler words that occur in almost every maternal document.
DOMAIN_FILLERS = frozenset({
    "mẹ", "bầu", "thai", "tuần", "tháng", "em", "bé", "con", "mình", "người", "nhà", "hỏi", "chào",
})

# Stopwords whose accent-folded form is also a meaningful word (năm/nằm, đâu/đau, để/đẻ, thế/thể, ra máu...):
# never dropped from a query typed without diacritics.
_FOLDED_STOPWORD_COLLISIONS = {
    "nam", "ba", "tam", "sau", "bay", "do", "co", "ma", "hai", "mot", "chin", "nao", "dau", "the",
    "tai", "tu", "da", "de", "ra", "can", "ve", "doi",
}


def _fold_accents(text: str) -> str:
    """Remove Vietnamese diacritics (đ -> d) for accent-insensitive comparison."""
    decomposed = unicodedata.normalize("NFD", text)
    return "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn").replace("đ", "d").replace("Đ", "D")


def _is_unaccented(text: str) -> bool:
    """True when the text contains letters but none of them carry Vietnamese diacritics."""
    return any(ch.isalpha() for ch in text) and _fold_accents(text) == text


def contains_word(term: str, text_lower: str) -> bool:
    """Whole-word/phrase match for re-ranking (Unicode-aware boundaries), so short terms do not hit inside other words."""
    return re.search(rf"(?<!\w){re.escape(term)}(?!\w)", text_lower) is not None


def searchable_stages(stage: Optional[str]) -> Optional[List[str]]:
    """Stages whose chunks a query at `stage` may retrieve; None means no stage filter."""
    if not stage or stage == "ALL":
        return None
    return [stage, "ALL", *_EXTRA_SEARCH_STAGES.get(stage, ())]


class PgVectorStore:
    def __init__(self) -> None:
        self.embedder = get_embedder()
        # Accent-folded copy of every stored chunk (id, stage, topic, title, content) for queries typed without
        # diacritics; built on first use, dropped whenever the stored chunks change.
        self._folded_index: Optional[List[tuple]] = None
        # In-memory cache fallback for fast local testing
        self._local_cache: List[Dict[str, Any]] = []

    async def add_chunks(
        self,
        chunks: List[DocumentChunkDTO],
        session: Optional[AsyncSession] = None,
    ) -> int:
        """Embed and insert chunks into PostgreSQL pgvector."""
        self._invalidate_folded_index()
        if not chunks:
            return 0

        texts = [c.content for c in chunks]
        embeddings = await self.embedder.embed_documents(texts)

        # Store in local memory cache as well
        for i, (chunk, emb) in enumerate(zip(chunks, embeddings)):
            self._local_cache.append({
                "id": len(self._local_cache) + 1,
                "title": chunk.title,
                "stage": chunk.stage,
                "topic": chunk.topic,
                "source": chunk.source,
                "section": chunk.section,
                "content": chunk.content,
                "chunk_index": chunk.chunk_index,
                "embedding": emb,
            })

        # Insert into Database if session/db is available
        async def _insert_to_db(s: AsyncSession) -> int:
            count = 0
            for chunk, emb in zip(chunks, embeddings):
                db_chunk = MaternalKnowledgeChunk(
                    title=chunk.title,
                    stage=chunk.stage,
                    topic=chunk.topic,
                    source=chunk.source,
                    section=chunk.section,
                    content=chunk.content,
                    chunk_index=chunk.chunk_index,
                    embedding=emb,
                )
                s.add(db_chunk)
                count += 1
            await s.commit()
            self._invalidate_folded_index()  # a query may have rebuilt it from pre-commit rows
            return count

        if session is not None:
            try:
                return await _insert_to_db(session)
            except Exception as e:
                logger.warning(f"Failed to insert chunks to PostgreSQL via provided session: {e}")
                return len(chunks)
        else:
            try:
                async with AsyncSessionLocal() as db:
                    return await _insert_to_db(db)
            except Exception as e:
                logger.warning(f"PostgreSQL not reachable for insert, saved to in-memory store: {e}")
                return len(chunks)

    async def replace_document_chunks(
        self,
        chunks: List[DocumentChunkDTO],
        session: Optional[AsyncSession] = None,
    ) -> int:
        """Idempotent ingestion: replace every stored chunk of the same document title (exact match) in one
        transaction. Re-running ingestion with add_chunks alone duplicated the whole knowledge base."""
        self._invalidate_folded_index()
        if not chunks:
            return 0
        titles = sorted({c.title for c in chunks})
        embeddings = await self.embedder.embed_documents([c.content for c in chunks])

        async def _replace(s: AsyncSession) -> int:
            await s.execute(delete(MaternalKnowledgeChunk).where(MaternalKnowledgeChunk.title.in_(titles)))
            for chunk, emb in zip(chunks, embeddings):
                s.add(MaternalKnowledgeChunk(
                    title=chunk.title, stage=chunk.stage, topic=chunk.topic, source=chunk.source,
                    section=chunk.section, content=chunk.content, chunk_index=chunk.chunk_index, embedding=emb,
                ))
            await s.commit()  # delete + insert commit together
            return len(chunks)

        if session is not None:
            inserted = await _replace(session)
        else:
            async with AsyncSessionLocal() as db:
                inserted = await _replace(db)

        self._invalidate_folded_index()  # again: a query may have rebuilt it from pre-commit rows
        # Mirror into the in-memory fallback only after the database commit succeeded.
        self._local_cache = [c for c in self._local_cache if c["title"] not in titles]
        for chunk, emb in zip(chunks, embeddings):
            self._local_cache.append({
                "id": len(self._local_cache) + 1, "title": chunk.title, "stage": chunk.stage, "topic": chunk.topic,
                "source": chunk.source, "section": chunk.section, "content": chunk.content,
                "chunk_index": chunk.chunk_index, "embedding": emb,
            })
        return inserted

    async def delete_by_title(
        self,
        title: str,
        session: Optional[AsyncSession] = None,
    ) -> int:
        """Delete all chunks belonging to a document title or filename."""
        self._invalidate_folded_index()
        prev_len = len(self._local_cache)
        self._local_cache = [c for c in self._local_cache if title.lower() not in c["title"].lower()]
        deleted_count = prev_len - len(self._local_cache)

        async def _delete_from_db(s: AsyncSession) -> int:
            stmt = delete(MaternalKnowledgeChunk).where(
                MaternalKnowledgeChunk.title.ilike(f"%{title}%")
            )
            result = await s.execute(stmt)
            await s.commit()
            self._invalidate_folded_index()
            return result.rowcount or 0

        if session is not None:
            try:
                db_deleted = await _delete_from_db(session)
                return max(deleted_count, db_deleted)
            except Exception as e:
                logger.warning(f"Database delete notice: {e}")
        else:
            try:
                async with AsyncSessionLocal() as db:
                    db_deleted = await _delete_from_db(db)
                    return max(deleted_count, db_deleted)
            except Exception as e:
                logger.warning(f"Database delete notice: {e}")

        return deleted_count

    async def clear_all(
        self,
        session: Optional[AsyncSession] = None,
    ) -> int:
        """Delete all knowledge chunks from the entire database and memory cache."""
        self._invalidate_folded_index()
        count = len(self._local_cache)
        self._local_cache.clear()

        async def _clear_db(s: AsyncSession) -> int:
            stmt = delete(MaternalKnowledgeChunk)
            result = await s.execute(stmt)
            await s.commit()
            self._invalidate_folded_index()
            return result.rowcount or 0

        if session is not None:
            try:
                db_cleared = await _clear_db(session)
                return max(count, db_cleared)
            except Exception as e:
                logger.warning(f"Database clear notice: {e}")
        else:
            try:
                async with AsyncSessionLocal() as db:
                    db_cleared = await _clear_db(db)
                    return max(count, db_cleared)
            except Exception as e:
                logger.warning(f"Database clear notice: {e}")

        return count

    async def get_existing_titles(self, session: Optional[AsyncSession] = None) -> set[str]:
        """Return set of distinct document titles already stored in pgvector or cache."""
        async def _fetch(s: AsyncSession) -> set[str]:
            stmt = select(MaternalKnowledgeChunk.title).distinct()
            res = await s.execute(stmt)
            return set(res.scalars().all())

        db_titles: set[str] = set()
        if session is not None:
            try:
                db_titles = await _fetch(session)
            except Exception as e:
                logger.debug(f"Could not fetch existing titles from session: {e}")
        else:
            try:
                async with AsyncSessionLocal() as db:
                    db_titles = await _fetch(db)
            except Exception as e:
                logger.debug(f"Could not fetch existing titles from DB: {e}")

        cache_titles = {c["title"] for c in self._local_cache if "title" in c}
        return db_titles | cache_titles

    async def list_chunks(
        self,
        stage: Optional[str] = None,
        topic: Optional[str] = None,
        keyword: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
        session: Optional[AsyncSession] = None,
    ) -> KnowledgeListResponse:
        """List chunks with pagination and filtering."""
        offset = (page - 1) * page_size

        async def _list_from_db(s: AsyncSession) -> Optional[KnowledgeListResponse]:
            # Count query
            count_stmt = select(func.count(MaternalKnowledgeChunk.id))
            if stage and stage != "ALL":
                count_stmt = count_stmt.where(MaternalKnowledgeChunk.stage.in_([stage, "ALL"]))
            if topic:
                count_stmt = count_stmt.where(MaternalKnowledgeChunk.topic == topic)
            if keyword:
                count_stmt = count_stmt.where(
                    MaternalKnowledgeChunk.title.ilike(f"%{keyword}%")
                    | MaternalKnowledgeChunk.content.ilike(f"%{keyword}%")
                )

            total_res = await s.execute(count_stmt)
            total = total_res.scalar() or 0

            # Items query
            stmt = select(MaternalKnowledgeChunk)
            if stage and stage != "ALL":
                stmt = stmt.where(MaternalKnowledgeChunk.stage.in_([stage, "ALL"]))
            if topic:
                stmt = stmt.where(MaternalKnowledgeChunk.topic == topic)
            if keyword:
                stmt = stmt.where(
                    MaternalKnowledgeChunk.title.ilike(f"%{keyword}%")
                    | MaternalKnowledgeChunk.content.ilike(f"%{keyword}%")
                )

            stmt = stmt.order_by(MaternalKnowledgeChunk.id.desc()).offset(offset).limit(page_size)
            result = await s.execute(stmt)
            chunks = result.scalars().all()

            items = [
                ChunkDetailItem(
                    id=c.id,
                    title=c.title,
                    stage=c.stage,
                    topic=c.topic,
                    source=c.source,
                    section=c.section,
                    snippet=c.content[:200] + "..." if len(c.content) > 200 else c.content,
                    content_length=len(c.content),
                    chunk_index=c.chunk_index,
                )
                for c in chunks
            ]
            return KnowledgeListResponse(total=total, page=page, page_size=page_size, items=items)

        if session is not None:
            try:
                db_res = await _list_from_db(session)
                if db_res:
                    return db_res
            except Exception as e:
                logger.debug(f"DB list notice: {e}")
        else:
            try:
                async with AsyncSessionLocal() as db:
                    db_res = await _list_from_db(db)
                    if db_res:
                        return db_res
            except Exception as e:
                logger.debug(f"DB list notice: {e}")

        # Fallback in-memory list
        filtered = self._local_cache
        if stage and stage != "ALL":
            filtered = [c for c in filtered if c["stage"] in (stage, "ALL")]
        if topic:
            filtered = [c for c in filtered if c["topic"] == topic]
        if keyword:
            k = keyword.lower()
            filtered = [c for c in filtered if k in c["title"].lower() or k in c["content"].lower()]

        total = len(filtered)
        paginated = filtered[offset : offset + page_size]
        items = [
            ChunkDetailItem(
                id=c.get("id", idx + 1),
                title=c["title"],
                stage=c["stage"],
                topic=c["topic"],
                source=c["source"],
                section=c.get("section"),
                snippet=c["content"][:200] + "..." if len(c["content"]) > 200 else c["content"],
                content_length=len(c["content"]),
                chunk_index=c.get("chunk_index", 0),
            )
            for idx, c in enumerate(paginated)
        ]
        return KnowledgeListResponse(total=total, page=page, page_size=page_size, items=items)

    async def get_stats(self, session: Optional[AsyncSession] = None) -> KnowledgeStatsResponse:
        """Get statistics about knowledge chunks and sources."""
        files = [f.name for f in RAW_DOCS_DIR.glob("*") if f.is_file() and not f.name.startswith(".")]

        stage_dist: Dict[str, int] = {}
        topic_dist: Dict[str, int] = {}
        total_chunks = len(self._local_cache)
        doc_titles = set(c["title"] for c in self._local_cache)

        for c in self._local_cache:
            stage_dist[c["stage"]] = stage_dist.get(c["stage"], 0) + 1
            topic_dist[c["topic"]] = topic_dist.get(c["topic"], 0) + 1

        return KnowledgeStatsResponse(
            total_chunks=total_chunks,
            total_documents=len(doc_titles) or len(files),
            stage_distribution=stage_dist,
            topic_distribution=topic_dist,
            files_in_disk=files,
        )

    async def similarity_search(
        self,
        query: str,
        stage: Optional[str] = None,
        topic: Optional[str] = None,
        top_k: int = 4,
        session: Optional[AsyncSession] = None,
    ) -> List[Dict[str, Any]]:
        """Find the top-K most similar knowledge chunks using Hybrid Search (Dense Vector + Sparse Keyword Re-ranking)."""
        # A query typed entirely without diacritics embeds to near-random vectors (similarity ~0.14) and its
        # keywords never match the accented corpus with ILIKE, so it retrieved nothing and the chat refused.
        # Such queries take their keyword candidates from an accent-folded in-memory index instead
        # (folding inside SQL with translate() took ~20 s per query on the hosted database).
        typed_unaccented = _is_unaccented(query)

        general_stopwords = set(GENERAL_STOPWORDS)
        domain_fillers = set(DOMAIN_FILLERS)

        if typed_unaccented:
            # "moi ngay uong bao nhieu" must drop its fillers too, or they take the few keyword slots sent to
            # search. Folded forms that are also a clinical word ("năm"/"nằm", "đâu"/"đau") are kept.
            general_stopwords |= {_fold_accents(w) for w in general_stopwords} - _FOLDED_STOPWORD_COLLISIONS
            domain_fillers |= {_fold_accents(w) for w in domain_fillers} - _FOLDED_STOPWORD_COLLISIONS

        clean_words = [
            w for w in re.sub(r"[^\w\s]", " ", query.lower()).split()
            if w not in general_stopwords and (len(w) > 1 or w.isdigit())
        ]
        
        # Specific clinical symptoms / terms (excluding generic filler words)
        clinical_words = [w for w in clean_words if w not in domain_fillers]

        # Extract 2-gram and 3-gram meaningful phrases dynamically from any query
        raw_words = re.sub(r"[^\w\s]", " ", query.lower()).split()
        phrases_3 = []
        for i in range(len(raw_words) - 2):
            w1, w2, w3 = raw_words[i], raw_words[i+1], raw_words[i+2]
            p = f"{w1} {w2} {w3}"
            if len(p) >= 7 and any(w in clinical_words for w in (w1, w2, w3)):
                phrases_3.append(p)

        phrases_2 = []
        for i in range(len(raw_words) - 1):
            w1, w2 = raw_words[i], raw_words[i+1]
            p = f"{w1} {w2}"
            if len(p) >= 4 and any(w in clinical_words for w in (w1, w2)):
                phrases_2.append(p)

        key_phrases = phrases_3 + phrases_2

        # Only the first few terms go to SQL. Taking them in sentence order sent "em mang thai", "mang thai 32"
        # and dropped the symptoms at the end ("đau đầu dữ dội", "nhìn mờ"). Prefer terms with the most
        # clinical (non-numeric) words; the stable sort keeps sentence order among equals.
        clinical_set = {w for w in clinical_words if not w.isdigit()}

        def _informativeness(phrase: str) -> int:
            return -sum(1 for w in phrase.split() if w in clinical_set)

        phrases_2_sql = sorted(phrases_2, key=_informativeness)[:6]
        phrases_3_sql = sorted(phrases_3, key=_informativeness)[:6]

        allowed_stages = searchable_stages(stage)

        def _filtered(stmt):
            if allowed_stages is not None:
                stmt = stmt.where(MaternalKnowledgeChunk.stage.in_(allowed_stages))
            if topic:
                stmt = stmt.where(MaternalKnowledgeChunk.topic == topic)
            return stmt

        def _ranked_match_query(column, terms: List[str], limit: int):
            # Rows matching the most terms first (then id for determinism). Without ORDER BY, LIMIT returned
            # arbitrary rows, so retrieval changed from run to run and relevant chunks were often cut off.
            # Ties go to shorter chunks: long chunks match more terms by sheer size, not by focus.
            # Plain ILIKE keeps candidate generation fast; precision comes from whole-word re-ranking below.
            conditions = [column.ilike(f"%{t}%") for t in terms]
            match_count = sum((case((cond, 1), else_=0) for cond in conditions), literal(0))
            stmt = select(MaternalKnowledgeChunk).where(or_(*conditions))
            return _filtered(stmt).order_by(match_count.desc(), func.length(MaternalKnowledgeChunk.content).asc(), MaternalKnowledgeChunk.id.asc()).limit(limit)

        # Keyword candidate queries do not need the query embedding: start them now on a separate pooled
        # connection so their round trip overlaps with the embedding call.
        search_keywords = clinical_words or clean_words
        keyword_stmts = []
        if phrases_2:
            keyword_stmts.append(_ranked_match_query(MaternalKnowledgeChunk.title, phrases_2_sql, 30))
        if phrases_3:
            keyword_stmts.append(_ranked_match_query(MaternalKnowledgeChunk.content, phrases_3_sql, 40))
        if search_keywords:
            keyword_stmts.append(_ranked_match_query(
                MaternalKnowledgeChunk.content, sorted(search_keywords, key=str.isdigit)[:6], 40))

        folded_specs = []  # same three candidate queries, evaluated on folded text: (use_title, terms, limit)
        if phrases_2:
            folded_specs.append((True, phrases_2_sql, 30))
        if phrases_3:
            folded_specs.append((False, phrases_3_sql, 40))
        if search_keywords:
            folded_specs.append((False, sorted(search_keywords, key=str.isdigit)[:6], 40))

        async def _run_keyword_queries() -> List[MaternalKnowledgeChunk]:
            if typed_unaccented:
                ids = await self._folded_keyword_ids(folded_specs, allowed_stages, topic)
                if not ids:
                    return []
                async with AsyncSessionLocal() as ks:
                    stmt = select(MaternalKnowledgeChunk).where(MaternalKnowledgeChunk.id.in_(ids))
                    return list((await ks.execute(stmt)).scalars())
            # One round trip and one extra pooled connection: UNION ALL of each ranked query's ids.
            if not keyword_stmts:
                return []
            id_selects = [select(q.with_only_columns(MaternalKnowledgeChunk.id).subquery().c.id) for q in keyword_stmts]
            stmt = select(MaternalKnowledgeChunk).where(MaternalKnowledgeChunk.id.in_(union_all(*id_selects)))
            async with AsyncSessionLocal() as ks:
                return list((await ks.execute(stmt)).scalars())

        keyword_future = asyncio.gather(_run_keyword_queries(), return_exceptions=True)
        try:
            query_vector = await self.embedder.embed_query(query)
        finally:
            keyword_results = await keyword_future

        async def _search_db(s: AsyncSession) -> List[Dict[str, Any]]:
            # With a WHERE filter, an HNSW scan only yields ~hnsw.ef_search rows (default 40) before filtering,
            # so LIMIT DENSE_CANDIDATES was silently capped. Raise it for this transaction (pgvector guidance
            # for filtered search). Isolated in a savepoint so a database without the setting is unaffected.
            try:
                async with s.begin_nested():
                    await s.execute(
                        text("SELECT set_config('hnsw.ef_search', :ef, true)"),
                        {"ef": str(int(DENSE_CANDIDATES))},
                    )
            except Exception as e:  # e.g. not PostgreSQL / pgvector without HNSW
                logger.debug(f"hnsw.ef_search not applied: {e}")

            # 1. Query Top Dense Vector candidates
            stmt_vec = select(
                MaternalKnowledgeChunk,
                MaternalKnowledgeChunk.embedding.cosine_distance(query_vector).label("distance"),
            )
            # Wider candidate pool: duplicated ingestion can fill a small pool with copies of the same chunk.
            stmt_vec = _filtered(stmt_vec).order_by("distance", MaternalKnowledgeChunk.id.asc()).limit(DENSE_CANDIDATES)
            res_vec = await s.execute(stmt_vec)

            candidates: Dict[int, tuple[MaternalKnowledgeChunk, float]] = {}
            for chunk, dist in res_vec.all():
                vec_sim = 1.0 - float(dist) if dist is not None else 0.0
                candidates[chunk.id] = (chunk, vec_sim)

            # 2-4. Title / 3-gram / keyword candidates (fetched concurrently above)
            for result in keyword_results:
                if isinstance(result, Exception):
                    logger.warning(f"Keyword candidate query failed: {result}")
                    continue
                for chunk in result:
                    if chunk.id not in candidates:
                        candidates[chunk.id] = (chunk, 0.0)

            # 5. Compute Hybrid Re-ranking Score
            target_words = clinical_words or clean_words
            # A query typed without Vietnamese diacritics can never match accented text literally, so
            # compare it against accent-folded content instead (accented queries keep exact matching).
            fold = typed_unaccented
            scored = []
            for chunk_id, (chunk, vec_sim) in candidates.items():
                content_lower = _fold_accents(chunk.content.lower()) if fold else chunk.content.lower()
                title_lower = _fold_accents(chunk.title.lower()) if fold else chunk.title.lower()
                
                kw_hits = sum(1 for w in target_words if contains_word(w, content_lower) or contains_word(w, title_lower))
                kw_ratio = kw_hits / max(len(target_words), 1)

                title_boost = 0.0
                for p in key_phrases:
                    if contains_word(p, title_lower):
                        title_boost += 0.40

                content_phrase_boost = 0.0
                for p in key_phrases:
                    if contains_word(p, content_lower):
                        content_phrase_boost += 0.30

                has_kw_match = kw_hits >= 1
                has_phrase = title_boost > 0.0 or content_phrase_boost > 0.0

                # Strict grounding gate: if completely unrelated keywords/phrases and low vector similarity -> 0.0
                if not has_kw_match and not has_phrase:
                    if vec_sim < 0.58:
                        hybrid_score = 0.0
                    else:
                        hybrid_score = vec_sim * 0.40
                else:
                    hybrid_score = (max(vec_sim, 0.0) * 0.40) + (kw_ratio * 0.35) + title_boost + content_phrase_boost
                
                scored.append((chunk, hybrid_score))

            # Stable order: score desc, then id asc, so equal scores do not reorder between runs.
            scored.sort(key=lambda x: (-x[1], x[0].id))

            results = []
            seen_sections = set()
            seen_contents = set()
            per_title: Dict[str, int] = {}
            for chunk, h_score in scored:
                sec_key = f"{chunk.title}_{chunk.section}"
                content_key = (chunk.content or "").strip()
                if sec_key in seen_sections or content_key in seen_contents:
                    continue
                # Source diversity: a title match boosts every chunk of that document, which let a single
                # document fill all top_k slots and push out the chunk that actually answers the question.
                if per_title.get(chunk.title, 0) >= MAX_CHUNKS_PER_DOCUMENT:
                    continue
                per_title[chunk.title] = per_title.get(chunk.title, 0) + 1
                seen_sections.add(sec_key)
                seen_contents.add(content_key)

                results.append({
                    "id": chunk.id,
                    "title": chunk.title,
                    "stage": chunk.stage,
                    "topic": chunk.topic,
                    "source": chunk.source,
                    "section": chunk.section,
                    "content": chunk.content,
                    "similarity": round(h_score, 4),
                })
                if len(results) >= top_k:
                    break

            return results

        if session is not None:
            try:
                db_results = await _search_db(session)
                if db_results:
                    return db_results
            except Exception as e:
                logger.warning(f"pgvector query error on provided session: {e}")
        else:
            try:
                async with AsyncSessionLocal() as db:
                    db_results = await _search_db(db)
                    if db_results:
                        return db_results
            except Exception as e:
                logger.warning(f"PostgreSQL pgvector query unavailable ({e}), using in-memory cache")

        # Fallback in-memory Cosine Similarity
        return self._in_memory_search(query_vector, stage, top_k)

    async def warm_folded_index(self) -> None:
        """Build the accent-folded keyword index ahead of the first unaccented query (~16k chunks: a few
        seconds to load, then ~0.1 s per query)."""
        if self._folded_index is not None:
            return
        async with AsyncSessionLocal() as s:
            rows = (await s.execute(select(
                MaternalKnowledgeChunk.id, MaternalKnowledgeChunk.stage, MaternalKnowledgeChunk.topic,
                MaternalKnowledgeChunk.title, MaternalKnowledgeChunk.content,
            ))).all()
        # Concurrent first calls may both build; the result is identical, so no lock is needed.
        self._folded_index = [
            (cid, st, tp, _fold_accents((ti or "").lower()), _fold_accents((c or "").lower()))
            for cid, st, tp, ti, c in rows
        ]
        logger.info("Accent-folded keyword index built: %d chunks", len(self._folded_index))

    def _invalidate_folded_index(self) -> None:
        self._folded_index = None

    async def _folded_keyword_ids(self, specs, allowed_stages: Optional[List[str]], topic: Optional[str]) -> List[int]:
        """Same ranking as the SQL keyword candidates (most matched terms, then shorter chunk, then id), but on
        accent-folded text. `specs` holds (match_title, terms, limit) per candidate query."""
        if not specs:
            return []
        try:
            await self.warm_folded_index()
        except Exception as e:
            logger.warning(f"Accent-folded keyword index unavailable: {e}")
            return []
        rows = [
            r for r in self._folded_index
            if (allowed_stages is None or r[1] in allowed_stages) and (not topic or r[2] == topic)
        ]
        ids: List[int] = []
        for match_title, terms, limit in specs:
            folded_terms = [_fold_accents(t) for t in terms]
            ranked = []
            for cid, _, _, title, content in rows:
                hits = sum(1 for t in folded_terms if t in (title if match_title else content))
                if hits:
                    ranked.append((-hits, len(content), cid))
            ranked.sort()
            ids.extend(cid for _, _, cid in ranked[:limit])
        return list(dict.fromkeys(ids))

    def _in_memory_search(
        self,
        query_vector: List[float],
        stage: Optional[str] = None,
        top_k: int = 4,
    ) -> List[Dict[str, Any]]:
        if not self._local_cache:
            return []

        allowed_stages = searchable_stages(stage)
        scored = []
        seen_contents = set()
        for item in self._local_cache:
            if allowed_stages is not None and item["stage"] not in allowed_stages:
                continue
            if item["content"] in seen_contents:
                continue
            seen_contents.add(item["content"])

            doc_vector = item.get("embedding") or []
            dot = sum(a * b for a, b in zip(query_vector, doc_vector))
            norm_q = sum(a * a for a in query_vector) ** 0.5 or 1.0
            norm_d = sum(b * b for b in doc_vector) ** 0.5 or 1.0
            sim = dot / (norm_q * norm_d)
            scored.append((item, sim))

        scored.sort(key=lambda x: -x[1])
        return [
            {
                "title": doc["title"],
                "stage": doc["stage"],
                "topic": doc["topic"],
                "source": doc["source"],
                "section": doc.get("section"),
                "content": doc["content"],
                "similarity": sim,
            }
            for doc, sim in scored[:top_k]
        ]


vector_store = PgVectorStore()


def get_vector_store() -> PgVectorStore:
    return vector_store
