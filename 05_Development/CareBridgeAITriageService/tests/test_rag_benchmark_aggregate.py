"""Offline tests for benchmark aggregation/reporting: no fabricated scores, honest denominators."""

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

import evaluate_rag_benchmark as bench  # noqa: E402

CASES = [
    {"id": "D1", "case_type": "DANGER", "category": "Cấp cứu", "question": "q1", "expected_danger_flag": True,
     "expected_behavior": "EMERGENCY_REFER", "ground_truth": "gt", "evidence_quotes": []},
    {"id": "F1", "case_type": "FACTUAL", "category": "Dinh dưỡng", "question": "q2", "expected_danger_flag": False,
     "expected_behavior": "ANSWER", "ground_truth": "gt", "evidence_quotes": []},
    {"id": "N1", "case_type": "NOT_IN_KB", "category": "Ngoài tài liệu", "question": "q3", "expected_danger_flag": False,
     "expected_behavior": "ABSTAIN_OR_REFER", "ground_truth": "gt", "evidence_quotes": []},
]


def _judge(faith, corr=0.8, error=None):
    return {"claims_total": 4, "claims_unsupported": [], "faithfulness": faith, "answer_correctness": corr,
            "answer_relevancy": 0.9, "context_precision": 0.9, "contradicts_ground_truth": False,
            "unsafe_advice": False, "expected_behavior_met": True, "rationale": "", "judge_error": error}


def _run(case_id, repeat, danger, faith=1.0, abstained=False, fabricated=0, quotes=1, judge_error=None, gen_error=None):
    base = {"case_id": case_id, "repeat_idx": repeat, "generation_error": gen_error, "latency_seconds": 2.0,
            "model_used": "gemini-flash-lite-latest"}
    if gen_error:
        return base
    judge = _judge(None if judge_error else faith, None if judge_error else 0.8, judge_error)
    if judge_error:
        judge.update({k: None for k in ("claims_total", "claims_unsupported", "answer_relevancy", "context_precision",
                                        "contradicts_ground_truth", "unsafe_advice", "expected_behavior_met")})
    return {**base, "answer": f"ans {case_id} {repeat}", "has_critical_warning": danger, "need_expert_consultation": danger,
            "disclaimer_present": True, "danger_match": None, "grounding_gate_blocked": False, "abstained": abstained,
            "retrieved_chunk_count": 2, "retrieved_titles": ["T"], "retrieved_contexts": ["c"],
            "expected_source_retrieved": True, "citations": [], "citations_total": quotes,
            "citations_in_context": quotes - fabricated, "citations_fabricated": fabricated, "judge": judge}


def test_judge_errors_are_excluded_not_scored():
    records = [_run("F1", 1, False, faith=0.5), _run("F1", 2, False, judge_error="JSONDecodeError")]
    m = bench.aggregate(CASES, records, "judge-x")
    assert m["judge_error_count"] == 1
    assert m["judged_runs"] == 1
    assert m["mean_faithfulness"] == 0.5  # the failed judgement must not be replaced by a default score


def test_zero_faithfulness_counts_as_hallucination():
    m = bench.aggregate(CASES, [_run("F1", 1, False, faith=0.0), _run("F1", 2, False, faith=1.0)], "judge-x")
    assert m["response_level_hallucination"]["k"] == 1
    assert m["severe_hallucination"]["k"] == 1


def test_danger_false_negatives_and_consistency():
    records = [_run("D1", 1, True), _run("D1", 2, False), _run("D1", 3, True)]
    m = bench.aggregate(CASES, records, None)
    assert m["danger_recall"]["k"] == 2 and m["danger_recall"]["n"] == 3
    assert [fn["repeat_idx"] for fn in m["danger_false_negatives"]] == [2]
    assert abs(m["consistency"]["D1"]["danger_flag_agreement"] - 2 / 3) < 1e-9
    assert m["consistency_summary"]["cases_with_unstable_danger_flag"] == ["D1"]


def test_generation_errors_are_reported_separately():
    records = [_run("F1", 1, False), _run("F1", 2, False, gen_error="quota")]
    m = bench.aggregate(CASES, records, None)
    assert m["runs_ok"] == 1
    assert m["generation_error_rate"]["k"] == 1 and m["generation_error_rate"]["n"] == 2


def test_fabricated_citations_and_not_in_kb_abstention():
    records = [_run("F1", 1, False, quotes=4, fabricated=1), _run("N1", 1, False, abstained=True, quotes=0)]
    m = bench.aggregate(CASES, records, None)
    assert m["citation_fabrication_rate"]["fabricated"] == 1
    assert m["citation_fabrication_rate"]["total_quotes"] == 4
    assert m["not_in_kb_abstention"]["rate"] == 1.0


def test_not_in_kb_abstention_prefers_judge_over_phrase_heuristic():
    """'Tài liệu không đề cập ... tuy nhiên mẹ nên ...' matches an abstention phrase but still invents advice."""
    leaky = _run("N1", 1, False, abstained=True, quotes=0)
    leaky["judge"]["expected_behavior_met"] = False
    m = bench.aggregate(CASES, [leaky], "judge-x")
    assert m["not_in_kb_abstention"]["rate"] == 0.0


def test_external_judgement_derives_faithfulness_and_rejects_bad_input():
    j = bench.parse_external_judgement(
        {"claims_total": 4, "claims_unsupported": ["x"], "answer_correctness": 0.5, "answer_relevancy": 1,
         "context_precision": 0.25, "contradicts_ground_truth": False, "unsafe_advice": False,
         "expected_behavior_met": True, "rationale": "r", "faithfulness": 1.0},  # a given faithfulness is ignored
        "claude",
    )
    assert j["faithfulness"] == 0.75 and j["judge_model"] == "claude"
    import pytest
    with pytest.raises(ValueError):
        bench.parse_external_judgement({**j, "claims_total": 0, "claims_unsupported": ["a"]}, "claude")
    with pytest.raises(ValueError):
        bench.parse_external_judgement({**j, "answer_correctness": 1.5}, "claude")


def test_import_keeps_previous_judge_as_secondary_and_reports_agreement(tmp_path):
    raw = tmp_path / "raw_runs.jsonl"
    rec = _run("F1", 1, False, faith=1.0)
    rec["judge"]["judge_model"] = "gemini-3.5-flash"
    raw.write_text(json.dumps(rec, ensure_ascii=False) + "\n", encoding="utf-8")
    judgements = tmp_path / "j.jsonl"
    wrong = tmp_path / "wrong.jsonl"
    wrong.write_text(json.dumps({"case_id": "F1", "repeat_idx": 1, "answer_sha1": "000000000000"}) + "\n", encoding="utf-8")
    import pytest
    with pytest.raises(SystemExit):  # judgement made for a different answer must be rejected
        bench.import_judgements(raw, wrong, "claude")
    judgements.write_text(json.dumps({
        "case_id": "F1", "repeat_idx": 1, "answer_sha1": bench.answer_sha1(rec["answer"]),
        "claims_total": 2, "claims_unsupported": ["bịa"],
        "answer_correctness": 0.8, "answer_relevancy": 0.9, "context_precision": 0.9,
        "contradicts_ground_truth": False, "unsafe_advice": False, "expected_behavior_met": True, "rationale": "r",
    }, ensure_ascii=False) + "\n", encoding="utf-8")
    assert bench.import_judgements(raw, judgements, "claude") == 1
    records = bench.latest_records(bench.load_records(raw))
    assert records[0]["judge"]["judge_model"] == "claude"
    assert records[0]["judge_secondary"]["judge_model"] == "gemini-3.5-flash"
    m = bench.aggregate(CASES, records, None)
    assert m["mean_faithfulness"] == 0.5
    assert m["inter_judge"]["hallucination_flag"] == {"agree": 0, "n": 1}


def test_report_is_generated_from_numbers(tmp_path):
    records = [_run("D1", 1, False), _run("F1", 1, False, faith=0.6)]
    m = bench.aggregate(CASES, records, "judge-x")
    manifest = {"started_at": "t", "git_commit": "abc", "generator_model": "g", "judge_model": "judge-x",
                "dataset": "d.json", "repeats": 1, "kb_chunk_count": 10}
    bench.write_reports(tmp_path, CASES, records, m, manifest)
    report = (tmp_path / "RAG_BENCHMARK_REPORT.md").read_text(encoding="utf-8")
    assert "KHÔNG ĐẠT" in report  # danger recall 0% must be reported as a failure
    assert "Tuyệt đối" not in report and "100% dấu hiệu" not in report
    assert (tmp_path / "manual_review_sheet.csv").exists()
    assert (tmp_path / "per_run.csv").exists()
