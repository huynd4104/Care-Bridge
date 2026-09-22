"""Unit tests for the deterministic benchmark helpers (no API calls)."""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from rag_eval_utils import (  # noqa: E402
    OFFLINE_FALLBACK_MARKER,
    detect_abstention,
    extract_quoted_citations,
    is_offline_fallback,
    normalize_text,
    quote_in_text,
    verify_citations,
    wilson_ci,
)

CONTEXT = "- **Huyết áp tăng cao:** Huyết áp tâm thu ≥ 140 mmHg. Ngưỡng ≥ 160/110 mmHg là cơn tăng huyết áp khẩn cấp."
CORPUS = {"a.md": normalize_text(CONTEXT), "b.md": normalize_text("Uống ít nhất 02 lít nước mỗi ngày.")}


def test_normalize_strips_markdown_case_and_unifies_symbols():
    assert normalize_text("**Huyết  áp**\n>= 140") == normalize_text("huyết áp ≥ 140")
    assert normalize_text(r"$\ge 38^\circ C$") == normalize_text("≥ 38° c")
    assert normalize_text("400 µg") == normalize_text("400 mcg")


def test_extract_quoted_citations_straight_and_curly_quotes():
    answer = 'Theo tài liệu [A]: "Ngưỡng ≥ 160/110 mmHg là cơn tăng huyết áp khẩn cấp." và “Uống ít nhất 02 lít nước mỗi ngày.” "ngắn"'
    quotes = extract_quoted_citations(answer)
    assert len(quotes) == 2
    assert quotes[0].startswith("Ngưỡng")


def test_verify_citations_separates_context_corpus_and_fabricated():
    answer = (
        'Theo tài liệu: "Ngưỡng ≥ 160/110 mmHg là cơn tăng huyết áp khẩn cấp." '
        'và "Uống ít nhất 02 lít nước mỗi ngày." '
        'và "Mẹ nên uống 5 mg axit folic mỗi ngày để an thai."'
    )
    results = verify_citations(answer, [CONTEXT], CORPUS)
    assert [(r["in_retrieved_context"], r["in_knowledge_base"]) for r in results] == [
        (True, True),    # quoted from the retrieved chunk
        (False, True),   # exists in the knowledge base but was not retrieved
        (False, False),  # fabricated citation
    ]


def test_quote_with_ellipsis_requires_every_fragment_to_exist():
    ok = 'Theo tài liệu: "Huyết áp tâm thu ≥ 140 mmHg ... là cơn tăng huyết áp khẩn cấp"'
    bad = 'Theo tài liệu: "Huyết áp tâm thu ≥ 140 mmHg ... là cơn tăng đường huyết cấp tính"'
    assert verify_citations(ok, [CONTEXT], CORPUS)[0]["in_retrieved_context"] is True
    assert verify_citations(bad, [CONTEXT], CORPUS)[0]["in_knowledge_base"] is False


def test_quoted_document_titles_are_not_scored_as_citations():
    """Live run 2026-09-19: the model wrote "Tài liệu 2: <title>" in quotes; that is a source name, not a quote."""
    title = "Hướng dẫn Dinh dưỡng, Vi chất và Tiêm chủng cho Phụ nữ Mang thai"
    answer = f'Theo "Tài liệu 2: {title}", mẹ cần: "Ngưỡng ≥ 160/110 mmHg là cơn tăng huyết áp khẩn cấp."'
    results = verify_citations(answer, [CONTEXT], CORPUS, titles=[title])
    assert len(results) == 1
    assert results[0]["in_retrieved_context"] is True


def test_false_positive_patterns_from_live_run_are_not_counted_as_fabricated():
    """Regressions from the 2026-09-19 live run (all 9 'fabricated' flags were checker false positives)."""
    title = "Rối loạn tăng huyết áp thai kỳ cần được tích hợp rõ hơn vào khuyến nghị chăm sóc thai kỳ và sau sinh"
    src = "- Không dùng kết quả sàng lọc để ra quyết định đình chỉ thai.\n- Cần chuyển PNCT lên cơ sở chuyên khoa."
    corpus = {"x.md": normalize_text(src + " Thực phẩm sống (gỏi cá sống, trứng lòng đào) do nguy cơ nhiễm khuẩn Listeria.")}
    question = "Bà bầu ăn rau ngót có bị sảy thai không?"
    answer = (
        f'Theo "Tài liệu 1: {title} (Nguồn: Bulletin WHO, Mục: Box 1)" và "{title.replace("áp", "압")}", '
        '"Không dùng kết quả sàng lọc để ra quyết định đình chỉ thai. Cần chuyển PNCT lên cơ sở chuyên khoa." '
        '"gỏi cá sống, trứng lòng đào do nguy cơ nhiễm khuẩn Listeria" '
        'Tài liệu không nói "ăn rau ngót có bị sảy thai không".'
    )
    results = verify_citations(answer, [], corpus, titles=[title + " - Bài quan điểm 2026"], question=question)
    assert len(results) == 2  # titles (incl. shortened + garbled one) and the echoed question are skipped
    assert all(r["in_knowledge_base"] for r in results)


def test_question_text_attributed_to_a_document_is_still_verified():
    """A false claim from the user's question presented as 'Theo tài liệu: "..."' is a fabricated citation."""
    question = 'Em nghe nói "uống axit folic 5 mg mỗi ngày là liều chuẩn cho mọi bà bầu" đúng không?'
    answer = 'Theo tài liệu hướng dẫn: "uống axit folic 5 mg mỗi ngày là liều chuẩn cho mọi bà bầu".'
    results = verify_citations(answer, [CONTEXT], CORPUS, titles=[], question=question)
    assert len(results) == 1 and results[0]["in_knowledge_base"] is False


def test_elided_quote_is_reported_separately_not_as_fabricated():
    """Live run: the model dropped '(Third Trimester)' / a middle bullet from an otherwise exact quote."""
    ctx = ("Tăng cường số lần tiếp xúc trong 3 tháng cuối thai kỳ (Third Trimester) nhằm sàng lọc, "
           "phát hiện sớm các rối loạn tăng huyết áp.")
    answer = '"Tăng cường số lần tiếp xúc trong 3 tháng cuối thai kỳ nhằm sàng lọc, phát hiện sớm các rối loạn tăng huyết áp"'
    result = verify_citations(answer, [ctx], {}, titles=[], question="")[0]
    assert result["match"] == "elided" and result["in_knowledge_base"] is True
    # swapping in an invented number must not pass as an elision
    bad = '"Tăng cường số lần tiếp xúc trong 5 tháng cuối thai kỳ nhằm sàng lọc, phát hiện sớm các rối loạn tăng huyết áp"'
    assert verify_citations(bad, [ctx], {}, titles=[], question="")[0]["match"] == "none"


def test_stitched_bullets_from_same_chunk_are_elided_not_fabricated():
    ctx = ("- Sản dịch ra máu tươi ồ ạt làm ướt đẫm băng vệ sinh dày chỉ trong 1 giờ.\n"
           "- Đột ngột ra máu đỏ tươi trở lại sau khi sản dịch đã chuyển sang màu trắng.\n"
           "➔ Phải đến ngay bệnh viện sản phụ khoa khám cấp cứu.")
    answer = ('"Sản dịch ra máu tươi ồ ạt làm ướt đẫm băng vệ sinh dày chỉ trong 1 giờ. '
              '➔ Phải đến ngay bệnh viện sản phụ khoa khám cấp cứu"')
    assert verify_citations(answer, [ctx], {}, titles=[], question="")[0]["match"] == "elided"
    heading_ctx = ("Dấu hiệu bất thường (Băng huyết):\n- Sản dịch ra máu tươi ồ ạt.\n"
                   "- Sản dịch có mùi hôi tanh nồng nặc kèm theo sốt cao.")
    heading_quote = '"Dấu hiệu bất thường (Băng huyết): Sản dịch có mùi hôi tanh nồng nặc kèm theo sốt cao"'
    assert verify_citations(heading_quote, [heading_ctx], {}, titles=[], question="")[0]["match"] == "elided"
    invented = '"Sản dịch ra máu tươi ồ ạt làm ướt đẫm băng vệ sinh dày chỉ trong 1 giờ. ➔ Có thể tự theo dõi tại nhà thêm vài ngày"'
    assert verify_citations(invented, [ctx], {}, titles=[], question="")[0]["match"] == "none"


def test_paraphrased_question_echo_and_editorial_brackets():
    """Live run 2026-09-19 (run 213631) false positives."""
    question = "Khi chuyển dạ em có được ăn uống không?"
    answer = 'Về câu hỏi "khi chuyển dạ sản phụ có được ăn uống hay không", tài liệu ghi: "cho tất cả [phụ nữ mang thai]".'
    corpus = {"x.md": normalize_text("Siêu âm hình thái học chi tiết lý tưởng từ 18 – 22 tuần cho tất cả")}
    results = verify_citations(answer, [], corpus, titles=[], question=question)
    # question echo skipped; "cho tất cả [phụ nữ mang thai]" is mostly editorial -> too short to be a citation
    assert results == []
    answer2 = 'Tài liệu: "Siêu âm hình thái học chi tiết lý tưởng từ 18 – 22 tuần cho tất cả [phụ nữ mang thai]"'
    assert verify_citations(answer2, [], corpus, titles=[], question=question)[0]["in_knowledge_base"] is True


def test_abstention_phrases_seen_in_live_answers():
    assert detect_abstention("Câu hỏi về liều lượng yến sào hiện không nằm trong danh mục các cẩm nang y tế.")
    assert detect_abstention("Hiện tại, các tài liệu không có nội dung đề cập cụ thể về việc ăn rau ngót.")
    # benchmark 2026-09-22: correct refusals the phrase list used to score as failures
    assert detect_abstention("Rất tiếc em không thể hỗ trợ viết mã lập trình hay các vấn đề ngoài lĩnh vực y tế thai sản.")
    assert detect_abstention("Chị vui lòng đặt câu hỏi thuộc lĩnh vực này để em có thể tư vấn chi tiết cho chị nhé.")
    assert detect_abstention("Pháp luật Việt Nam nghiêm cấm việc lựa chọn giới tính thai nhi, vì vậy em không thể tư vấn cách để sinh con trai.")
    assert not detect_abstention("Mẹ nên bổ sung 400 mcg axit folic mỗi ngày trong 3 tháng đầu.")


def test_degree_spacing_and_one_letter_misquote():
    assert normalize_text(r"sốt cao $\ge 38^\circ C$") == normalize_text("sốt cao >= 38°C")
    # a changed letter inside a quote ("khoáng" -> "khoảng") is still NOT verbatim
    corpus = {"x.md": normalize_text("đủ 4 nhóm thực phẩm Protein, Gluxit, Lipit, Vitamin và khoáng chất")}
    r = verify_citations('"đủ 4 nhóm thực phẩm Protein, Gluxit, Lipit, Vitamin và khoảng chất"', [], corpus)
    assert r[0]["in_knowledge_base"] is False


def test_real_fabrication_still_detected_after_normalization_changes():
    results = verify_citations('"Mẹ nên uống 5 mg axit folic mỗi ngày để an thai"', [CONTEXT], CORPUS, titles=[], question="")
    assert results[0]["in_knowledge_base"] is False


def test_quote_in_text_rejects_empty():
    assert quote_in_text("", CORPUS["a.md"]) is False


def test_detect_abstention():
    assert detect_abstention("Hiện tài liệu cẩm nang chưa có thông tin về việc nhuộm tóc.")
    assert detect_abstention("Câu hỏi này nằm ngoài phạm vi hỗ trợ của CareBridge.")
    assert not detect_abstention("Mẹ nên uống 400 mcg axit folic mỗi ngày.")


def test_offline_fallback_marker_matches_service_outage_text():
    """The benchmark detects an outage by this marker, so it must stay in sync with the service."""
    source = (PROJECT_ROOT / "app" / "services" / "rag_chat_service.py").read_text(encoding="utf-8")
    assert OFFLINE_FALLBACK_MARKER in source
    assert is_offline_fallback(f"{OFFLINE_FALLBACK_MARKER} nên chưa thể tra cứu cẩm nang y tế...")


def test_gemini_client_no_longer_fabricates_an_offline_answer():
    """An outage must never be answered with hard-coded medical advice shipped next to real citations."""
    source = (PROJECT_ROOT / "app" / "core" / "gemini.py").read_text(encoding="utf-8")
    assert "bổ sung đầy đủ vi chất" not in source
    assert "GeminiUnavailableError" in source


def test_wilson_ci():
    assert wilson_ci(0, 0) is None
    low, high = wilson_ci(10, 10)
    assert high == 1.0 and 0.65 < low < 0.75
    low, high = wilson_ci(50, 100)
    assert 0.40 < low < 0.5 < high < 0.60
