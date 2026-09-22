"""Deterministic (LLM-free) helpers for the CareBridge RAG benchmark.

Everything here is free to run: no API calls. Used by:
- scripts/evaluate_rag_benchmark.py (citation verification, abstention detection, CI)
- tests/test_golden_dataset.py (every evidence quote must exist verbatim in its source file)
"""

from __future__ import annotations

import difflib
import math
import re
import unicodedata
from pathlib import Path
from typing import Dict, Iterable, List, Optional

RAW_DOCUMENTS_DIR = Path(__file__).resolve().parent.parent / "data" / "raw_documents"

# Minimum length of a quoted span in an AI answer before we treat it as a citation claim.
MIN_CITATION_CHARS = 20

# Text RagChatService returns when no generation model was available (app/services/rag_chat_service.py
# :: SERVICE_UNAVAILABLE_ANSWER). GeminiClient.generate_response used to answer an outage with a
# hard-coded paragraph of medical advice; it now raises GeminiUnavailableError and the service degrades
# to this content-free message, so the benchmark detects an outage by this marker instead.
OFFLINE_FALLBACK_MARKER = "Hệ thống AI Nurse đang tạm thời gián đoạn kết nối"

# Phrases showing the assistant declined / said the documents do not cover the question.
ABSTENTION_PHRASES = (
    "không có thông tin",
    "chưa có thông tin",
    "không tìm thấy",
    "chưa tìm thấy",
    "không đề cập",
    "chưa đề cập",
    "không được đề cập",
    "không có dữ liệu",
    "không có trong tài liệu",
    "không nằm trong tài liệu",
    "tài liệu không có",
    "tài liệu chưa có",
    "cẩm nang không có",
    "cẩm nang chưa có",
    "ngoài phạm vi",
    "không giải đáp các chủ đề ngoài",
    "chuyên biệt về chăm sóc sức khỏe",
    # observed honest abstentions the list above missed (live run 2026-09-19)
    "không nằm trong",
    "không có nội dung",
    "chưa có nội dung",
    "không chứa",
    "không có hướng dẫn",
    "chưa có hướng dẫn",
    "không có dữ liệu",
    "chưa có dữ liệu",
    "không thể cung cấp thông tin",
    # refusals worded by the 2026-09-22 prompt (Trường hợp 6/meta/out-of-scope) that the list above missed
    "ngoài lĩnh vực",
    "không thể hỗ trợ",
    "không thể tư vấn",
    "câu hỏi thuộc lĩnh vực này",
    "vui lòng đặt câu hỏi thuộc lĩnh vực",
    "vui lòng đặt các câu hỏi liên quan đến lĩnh vực",
    "không thể tự ý",
)

_SYMBOL_MAP = {
    ">=": "≥",
    "<=": "≤",
    "–": "-",  # en dash
    "—": "-",  # em dash
    "−": "-",  # minus sign
    "“": '"',
    "”": '"',
    "‘": "'",
    "’": "'",
    " ": " ",
    "µg": "mcg",
    "μg": "mcg",
}
_LATEX_MAP = {
    r"\ge": "≥",
    r"\geq": "≥",
    r"\le": "≤",
    r"\leq": "≤",
    r"^\circ": "°",
    r"\circ": "°",
    r"\approx": "≈",
    r"\pm": "±",
}


def normalize_text(text: str) -> str:
    """Normalize for verbatim matching: NFC, strip markdown emphasis, unify symbols, casefold, collapse spaces."""
    if not text:
        return ""
    s = unicodedata.normalize("NFC", text)
    for latex, sym in sorted(_LATEX_MAP.items(), key=lambda kv: -len(kv[0])):
        s = s.replace(latex, sym)
    s = s.replace("$", "")
    for src, dst in _SYMBOL_MAP.items():
        s = s.replace(src, dst)
    s = s.replace("**", "").replace("*", "").replace("`", "")
    # Bullets and brackets are layout, not wording: a quote that merges two list items or drops a
    # closing parenthesis is still verbatim content.
    s = re.sub(r"(^|\s)[-•+]\s+", " ", s)
    s = re.sub(r"[()\[\]]", " ", s)
    s = s.casefold()
    s = re.sub(r"\s+", " ", s)
    # LaTeX "38^\circ C" renders as "38° C"; models write "38°C". Same value, different spacing.
    s = re.sub(r"°\s+(?=[a-z])", "°", s)
    return s.strip()


def load_corpus(directory: Path = RAW_DOCUMENTS_DIR) -> Dict[str, str]:
    """Return {file name: normalized text} for every markdown document in the knowledge base."""
    return {
        p.name: normalize_text(p.read_text(encoding="utf-8"))
        for p in sorted(directory.glob("*.md"))
    }


def quote_in_text(quote: str, normalized_haystack: str) -> bool:
    needle = normalize_text(quote)
    return bool(needle) and needle in normalized_haystack


_QUOTE_PATTERNS = (
    re.compile(r'"([^"\n]{%d,}?)"' % MIN_CITATION_CHARS),
    re.compile(r"“([^”\n]{%d,}?)”" % MIN_CITATION_CHARS),
    re.compile(r"«([^»\n]{%d,}?)»" % MIN_CITATION_CHARS),
)


def extract_quoted_citations(answer: str) -> List[str]:
    """Extract spans the model presented as direct quotes (prompt asks for: Theo tài liệu [X]: "...")."""
    found: List[str] = []
    for pattern in _QUOTE_PATTERNS:
        for m in pattern.finditer(answer or ""):
            span = m.group(1).strip().strip(".…").strip()
            span = re.sub(r"^\.{3}|\.{3}$", "", span).strip()
            if len(span) >= MIN_CITATION_CHARS and span not in found:
                found.append(span)
    return found


def _quote_segments(quote: str) -> List[str]:
    """Models often elide text with '...' inside a quote; each fragment must still be verbatim."""
    parts = [p.strip() for p in re.split(r"\.{3}|…", quote)]
    return [p for p in parts if len(p) >= 8] or [quote]


def verify_citation(quote: str, normalized_sources: Iterable[str]) -> bool:
    sources = list(normalized_sources)
    return all(any(quote_in_text(seg, src) for src in sources) for seg in _quote_segments(quote))


_DOC_LABEL_PREFIX = re.compile(r"^(tài liệu|tai lieu|document)\s*\d*\s*[:\-–]\s*", re.IGNORECASE)
_SOURCE_SUFFIX = re.compile(r"\s*\((nguồn|mục|source)\s*:.*\)\s*$", re.IGNORECASE)


def is_document_title(quote: str, titles: Iterable[str]) -> bool:
    """The prompt labels chunks '--- TÀI LIỆU 1: <title> (Nguồn: ..., Mục: ...) ---', so models often put a
    document NAME in quotes. A quoted title is a source reference, not a content citation. Near-exact
    matches (ratio >= 0.9) are accepted because models occasionally garble one character of a long title."""
    core = _SOURCE_SUFFIX.sub("", _DOC_LABEL_PREFIX.sub("", quote.strip()))
    stripped = normalize_text(core)
    if not stripped:
        return False
    for title in titles:
        norm_title = normalize_text(title or "")
        if not norm_title:
            continue
        if stripped == norm_title:
            return True
        if len(stripped) >= 20:
            # Models often quote a shortened title (e.g. without " - Bài quan điểm 2026"): compare with the
            # title prefix of the same length.
            head = norm_title[: len(stripped)]
            if difflib.SequenceMatcher(None, stripped, head).ratio() >= 0.9:
                return True
    return False


_ATTRIBUTION = re.compile(r"(theo|tài liệu|trích|cẩm nang ghi|nguồn)[^\"“”]{0,40}$", re.IGNORECASE)


def _echoes_question(quote: str, normalized_question: str) -> bool:
    """The quote repeats the question verbatim, or paraphrases it (>= 60% of its words come from the question)."""
    nq = normalize_text(quote)
    if nq in normalized_question:
        return True
    q_words = re.findall(r"\w+", nq)
    question_words = set(re.findall(r"\w+", normalized_question))
    return len(q_words) >= 4 and sum(w in question_words for w in q_words) / len(q_words) >= 0.6


def _is_attributed(answer: str, quote: str) -> bool:
    """True when the text right before the quote attributes it to a document ('Theo tài liệu X: "..."')."""
    idx = answer.find(quote)
    if idx < 0:
        return True  # cannot locate it: be conservative and verify it as a citation
    before = answer[max(0, idx - 60): idx].rstrip(" \"“")
    if re.search(r"\b(không|chưa)\b", before, re.IGNORECASE):
        return False  # 'tài liệu không đề cập "..."' is a negation, not an attribution
    return bool(_ATTRIBUTION.search(before))


def verify_citations(
    answer: str,
    context_texts: List[str],
    corpus: Dict[str, str],
    titles: Iterable[str] = (),
    question: str = "",
) -> List[Dict[str, object]]:
    """For each quoted span: is it verbatim in the retrieved context? anywhere in the knowledge base?

    Skipped (not citation claims): quoted document titles and spans that repeat the user's own question."""
    normalized_contexts = [normalize_text(c) for c in context_texts]
    normalized_question = normalize_text(question)
    titles = list(titles)
    results = []
    for quote in extract_quoted_citations(answer):
        if is_document_title(quote, titles):
            continue
        if normalized_question and _echoes_question(quote, normalized_question) and not _is_attributed(answer, quote):
            continue  # the model is repeating (or paraphrasing) the user's question, not citing a document
        # "[...]" inside a quote is an editorial insertion by the model (standard quoting convention), not a
        # claim that those words are in the document; check the rest verbatim.
        quote = re.sub(r"\s*\[[^\]]*\]\s*", " ", quote).strip()
        if len(quote) < MIN_CITATION_CHARS:
            continue  # mostly editorial text; not a citation claim
        in_context = verify_citation(quote, normalized_contexts)
        in_corpus = in_context or verify_citation(quote, corpus.values())
        elided = False
        if not in_corpus:
            # Words appear in order in a retrieved chunk but the model left out a phrase or a bullet in between:
            # content is from the document, yet the quote is not verbatim. Reported separately, not as fabricated.
            elided = any(is_elided_quote(quote, ctx) for ctx in normalized_contexts)
        results.append({
            "quote": quote,
            "in_retrieved_context": in_context,
            "in_knowledge_base": in_corpus or elided,
            "match": "exact" if in_corpus else ("elided" if elided else "none"),
        })
    return results


def is_elided_quote(quote: str, normalized_source: str, max_gap: int = 12, min_words: int = 6) -> bool:
    """True if the quote's words occur in the same order in the source, skipping at most `max_gap` source
    words between consecutive quote words (i.e. the model omitted parts but invented nothing)."""
    q_words = re.findall(r"\w+", normalize_text(quote))
    s_words = re.findall(r"\w+", normalized_source)
    if len(q_words) < min_words or not s_words:
        return False
    # Stitched quote: separate sentences/bullets of the same chunk joined together, each one verbatim.
    sentences = [s for s in re.split(r"[.;:➔→]+", normalize_text(quote)) if len(re.findall(r"\w+", s)) >= 4]
    if len(sentences) >= 2 and all(s.strip() in normalized_source for s in sentences):
        return True
    for start in (i for i, w in enumerate(s_words) if w == q_words[0]):
        pos, ok = start, True
        for word in q_words[1:]:
            window = s_words[pos + 1: pos + 2 + max_gap]
            if word not in window:
                ok = False
                break
            pos = pos + 1 + window.index(word)
        if ok:
            return True
    return False


def detect_abstention(answer: str) -> bool:
    lowered = normalize_text(answer)
    return any(phrase in lowered for phrase in ABSTENTION_PHRASES)


def is_offline_fallback(answer: str) -> bool:
    return OFFLINE_FALLBACK_MARKER in (answer or "")


def wilson_ci(successes: int, n: int, z: float = 1.96) -> Optional[tuple]:
    """95% Wilson score interval for a proportion; None when n == 0."""
    if n <= 0:
        return None
    p = successes / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))


def mean(values: Iterable[Optional[float]]) -> Optional[float]:
    vals = [v for v in values if v is not None]
    return sum(vals) / len(vals) if vals else None


def stdev(values: Iterable[Optional[float]]) -> Optional[float]:
    vals = [v for v in values if v is not None]
    if len(vals) < 2:
        return None
    m = sum(vals) / len(vals)
    return math.sqrt(sum((v - m) ** 2 for v in vals) / (len(vals) - 1))
