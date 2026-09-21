"""Canonical maternal `stage` vocabulary shared by ingestion (write side) and retrieval (read side).

Retrieval filters chunks by `stage`, so a chunk stored under any value outside RETRIEVABLE_STAGES can
never be returned by a search - it is silently invisible to the assistant. Document frontmatter is
hand-written and had drifted far from the enum: a scan of data/raw_documents found 193 of 936 files
carrying values such as "GENERAL", "PREGNANCY,POSTPARTUM" or free-text Vietnamese
("THAI KỲ; SAU SINH; SỨC KHỎE TÂM THẦN CHU SINH"). Every one of those documents was unreachable.

normalize_stage() maps whatever a document declares onto the canonical set, falling back to "ALL"
(searchable from every stage) rather than dropping the document out of reach.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Optional

STAGE_PRECONCEPTION = "PRECONCEPTION"
STAGE_PREGNANCY = "PREGNANCY"
STAGE_POSTPARTUM = "POSTPARTUM"
STAGE_BABY_CARE = "BABY_CARE"
STAGE_ALL = "ALL"

# The only values a stored chunk may carry if it is to be retrievable.
RETRIEVABLE_STAGES = frozenset(
    {STAGE_PRECONCEPTION, STAGE_PREGNANCY, STAGE_POSTPARTUM, STAGE_BABY_CARE, STAGE_ALL}
)

# Accent-folded keyword -> canonical stage. Order matters: the first match on the folded text wins.
# Newborn wording is checked before the postpartum wording it co-occurs with, and PRECONCEPTION before
# PREGNANCY because "trước khi mang thai" contains "mang thai" and would otherwise be read as pregnancy.
_KEYWORD_STAGES: tuple[tuple[str, str], ...] = (
    # Family planning / contraception is in scope at every stage. This mirrors the rule already used by
    # DocumentChunker.infer_stage_and_topic(), which classifies the same vocabulary as stage "ALL",
    # topic "FAMILY_PLANNING" - it is the project's own existing judgement, not a new one.
    (r"family planning|contracepti\w*|ke hoach hoa gia dinh|tranh thai|pha thai|triet san", STAGE_ALL),
    (r"\bbaby[_ ]?care\b|\bnewborn\b|\binfant\b|\bchild\b|so sinh|tre so sinh|tre nho|tre em", STAGE_BABY_CARE),
    (r"\bpreconception\b|truoc mang thai|truoc khi mang thai|tien hon nhan|chuan bi mang thai|"
     r"truoc va trong thai ky", STAGE_PRECONCEPTION),
    (r"\bpostpartum\b|\bbirth\b|sau sinh|hau san|san dich|o cu|chuyen da|sau khi sinh", STAGE_POSTPARTUM),
    (r"\bpregnan\w*|\bprenatal\b|thai ky|mang thai|truoc sinh|ba bau|me bau|tien san", STAGE_PREGNANCY),
)


def _fold(text: str) -> str:
    """Lowercase, strip Vietnamese diacritics (đ -> d), collapse separators to single spaces.

    Underscores count as separators so the ASCII transliterations real frontmatter uses
    ("THAI_KY; CHUYEN_DA; SAU_SINH") fold to the same form as their accented spelling.
    """
    s = unicodedata.normalize("NFD", (text or "").lower())
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")
    s = s.replace("đ", "d")
    return re.sub(r"[\s_]+", " ", s).strip()


def classify_stage(raw: object) -> tuple[str, bool]:
    """Map a declared stage onto the canonical vocabulary, and say whether it was actually recognised.

    Returns (canonical_stage, recognised). `recognised` is False when nothing in the value matched the
    maternal vocabulary and the result is only the "ALL" fallback. Callers that rewrite existing data
    use that flag to stay conservative: forcing genuinely off-domain material ("OLDER_ADULTS",
    "MENOPAUSE", "GENERAL") into "ALL" would make it compete in every maternal retrieval, trading a
    coverage win for a precision loss.

    Accepts the shapes real frontmatter uses: a plain string, a list, a comma/semicolon separated
    string, free-text Vietnamese, or nothing at all. Multi-value declarations collapse to "ALL" so the
    document stays reachable from every stage rather than being pinned to an arbitrary first entry.
    """
    if raw is None:
        return STAGE_ALL, False

    if isinstance(raw, (list, tuple, set)):
        parts = [str(p).strip() for p in raw if str(p).strip()]
    else:
        parts = [p.strip() for p in re.split(r"[;,/|]", str(raw)) if p.strip()]

    if not parts:
        return STAGE_ALL, False

    canonical: list[str] = []
    for part in parts:
        upper = part.upper()
        if upper in RETRIEVABLE_STAGES:
            canonical.append(upper)
            continue
        folded = _fold(part)
        for pattern, stage in _KEYWORD_STAGES:
            if re.search(pattern, folded):
                canonical.append(stage)
                break

    if not canonical:
        return STAGE_ALL, False

    deduped = list(dict.fromkeys(canonical))
    if len(deduped) == 1:
        return deduped[0], True
    # Spans several stages ("PREGNANCY,POSTPARTUM") - reachable from all of them.
    return STAGE_ALL, True


def normalize_stage(raw: object) -> str:
    """Canonical stage for a document, falling back to "ALL" for unrecognised vocabulary.

    Used on the ingest path, where a document being silently unreachable is the worse failure.
    """
    stage, _recognised = classify_stage(raw)
    return stage


def is_retrievable_stage(stage: Optional[str]) -> bool:
    """True when a stored chunk carrying this stage can actually be returned by a search."""
    return bool(stage) and str(stage).upper() in RETRIEVABLE_STAGES
