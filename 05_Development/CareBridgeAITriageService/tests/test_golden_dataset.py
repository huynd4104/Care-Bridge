"""Offline checks that the golden evaluation dataset is itself free of hallucinated ground truth.

Every evidence quote must exist (after normalization) in the cited file under data/raw_documents,
so a benchmark "correct answer" can always be traced back to the knowledge base. Free: no API calls.
"""

import json
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from rag_eval_utils import load_corpus, normalize_text, quote_in_text  # noqa: E402

DATASET = PROJECT_ROOT / "data" / "golden_evaluation_dataset.json"
CASES = json.loads(DATASET.read_text(encoding="utf-8"))
CORPUS = load_corpus()

CASE_TYPES = {"FACTUAL", "DANGER", "MULTI_HOP", "NOT_IN_KB", "OUT_OF_SCOPE", "FALSE_PREMISE",
              "PARAPHRASE", "NO_DIACRITICS", "FAMILY_ROLE"}
BEHAVIORS = {"ANSWER", "EMERGENCY_REFER", "CORRECT_PREMISE", "ABSTAIN_OR_REFER", "REFUSE_OUT_OF_SCOPE"}
STAGES = {"PRECONCEPTION", "PREGNANCY", "POSTPARTUM", "ALL"}
NO_EVIDENCE_TYPES = {"NOT_IN_KB", "OUT_OF_SCOPE"}


def test_dataset_size_and_unique_ids():
    ids = [c["id"] for c in CASES]
    assert len(CASES) >= 100
    assert len(ids) == len(set(ids))


@pytest.mark.parametrize("case", CASES, ids=[c["id"] for c in CASES])
def test_case_schema(case):
    assert case["case_type"] in CASE_TYPES
    assert case["expected_behavior"] in BEHAVIORS
    assert case["stage"] in STAGES
    assert case["user_role"] in {"MOTHER", "FAMILY"}
    assert case["expected_danger_flag"] in (True, False, None)
    assert case["question"].strip()
    assert case["ground_truth"].strip()
    if case["expected_danger_flag"] is True:
        assert case["expected_behavior"] == "EMERGENCY_REFER"
    if case["case_type"] in NO_EVIDENCE_TYPES:
        assert case["evidence_quotes"] == []
    else:
        assert case["evidence_quotes"], "answerable cases must cite at least one verbatim quote"
        # The case-level pointer must not go stale when evidence is remapped (it did after the 2026-09-22 prune).
        assert case["source_file"] in {e["source_file"] for e in case["evidence_quotes"]}


@pytest.mark.parametrize(
    "case_id,source_file,quote",
    [(c["id"], e["source_file"], e["quote"]) for c in CASES for e in c["evidence_quotes"]],
)
def test_evidence_quote_exists_verbatim_in_source(case_id, source_file, quote):
    assert source_file in CORPUS, f"{case_id}: source file {source_file} not found in raw_documents"
    assert quote_in_text(quote, CORPUS[source_file]), f"{case_id}: quote not found in {source_file}: {quote[:80]}"


@pytest.mark.parametrize("case", [c for c in CASES if c["case_type"] == "NOT_IN_KB"], ids=lambda c: c["id"])
def test_not_in_kb_topics_really_absent_from_knowledge_base(case):
    assert case["absent_terms"]
    for term in case["absent_terms"]:
        hits = [name for name, text in CORPUS.items() if normalize_text(term) in text]
        assert not hits, f"{case['id']}: '{term}' appears in {hits[:3]}, so the case is not NOT_IN_KB"


def test_paraphrase_links_point_to_existing_cases():
    ids = {c["id"] for c in CASES}
    for c in CASES:
        if c.get("paraphrase_of"):
            assert c["paraphrase_of"] in ids, c["id"]


def test_validator_rejects_fabricated_ground_truth():
    """Regression: the old TC-NEWBORN-01 claimed '60-90 phút' skin-to-skin, which the WHO 2009 guide does not say.

    The original file (01_cham_soc_so_sinh_den_het_tuan_dau_doi_who_2009.md) was removed from the corpus on
    2026-09-22; the same WHO 2009 guide is present as WHO_cham_soc_so_sinh_den_7_ngay_2009.md.
    """
    who_2009 = CORPUS["WHO_cham_soc_so_sinh_den_7_ngay_2009.md"]
    assert not quote_in_text("da kề da ít nhất 60 đến 90 phút", who_2009)
    assert quote_in_text("Đặt trẻ nằm sấp da kề da trên bụng/ngực mẹ, phủ lưng bằng chăn và đội mũ.", who_2009)
