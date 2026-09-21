"""Tests for AI Nurse Assistant RAG Chat Service."""

import json
import os
from pathlib import Path

import pytest
from app.models.schemas import (
    ChatMessage,
    MaternalStage,
    RagChatRequest,
)
from app.services.rag_chat_service import RagChatService

GOLDEN_DATASET = Path(__file__).resolve().parent.parent / "data" / "golden_evaluation_dataset.json"
DANGER_CASES = [
    c for c in json.loads(GOLDEN_DATASET.read_text(encoding="utf-8"))
    if c["expected_danger_flag"] is True
]
# Each dataset case costs one Gemini call; opt in explicitly to protect the free-tier quota.
live_dataset = pytest.mark.skipif(
    os.getenv("RUN_LIVE_AI_TESTS") != "1",
    reason="Set RUN_LIVE_AI_TESTS=1 to run golden-dataset cases against live Gemini + pgvector",
)


@live_dataset
@pytest.mark.asyncio
@pytest.mark.parametrize("case", DANGER_CASES, ids=[c["id"] for c in DANGER_CASES])
async def test_golden_danger_case_is_flagged_with_disclaimer(case):
    service = RagChatService()
    request = RagChatRequest(
        message=case["question"],
        stage=MaternalStage(case["stage"]),
        gestational_age_weeks=case["gestational_age_weeks"],
        user_role=case["user_role"],
    )
    result = await service.chat(request)
    assert result.disclaimer and result.disclaimer.strip()
    assert result.has_critical_warning is True, result.answer[:300]


@pytest.mark.asyncio
async def test_rag_chat_general_question():
    service = RagChatService()
    request = RagChatRequest(
        message="Mang thai 3 tháng đầu nên bổ sung sắt và axit folic như thế nào cho đúng cách?",
        stage=MaternalStage.PREGNANCY,
        gestational_age_weeks=10,
    )
    result = await service.chat(request)
    assert result.answer is not None
    assert len(result.answer) > 0
    assert result.has_critical_warning is False
    assert len(result.suggested_followups) > 0
    assert result.disclaimer is not None


@pytest.mark.asyncio
async def test_rag_chat_detects_emergency_intent():
    service = RagChatService()
    request = RagChatRequest(
        message="Em bị ra máu âm đạo kèm đau bụng quặn dữ dội thì phải làm sao?",
        stage=MaternalStage.PREGNANCY,
        gestational_age_weeks=28,
    )
    result = await service.chat(request)
    assert result.has_critical_warning is True
    assert any("115" in fu or "Bệnh viện" in fu for fu in result.suggested_followups)


@pytest.mark.asyncio
async def test_rag_chat_multi_turn_conversation():
    service = RagChatService()
    # Turn 2: User asks follow-up with implicit reference ("Nó có nguy hiểm không?")
    request = RagChatRequest(
        message="Nó có nguy hiểm đến em bé không ạ?",
        stage=MaternalStage.PREGNANCY,
        gestational_age_weeks=32,
        conversation_history=[
            ChatMessage(role="user", content="Em đang mang thai 32 tuần, hôm nay thấy bị đau đầu và phù hai chân"),
            ChatMessage(role="assistant", content="Chào mẹ, đau đầu và phù chân ở tuần 32 là dấu hiệu cần được theo dõi kỹ vì có thể liên quan đến tăng huyết áp thai kỳ."),
        ],
    )
    result = await service.chat(request)
    assert result.answer is not None
    assert len(result.answer) > 0
    # Should retrieve preeclampsia or blood pressure related sources thanks to multi-turn query expansion
    assert len(result.sources) > 0


@pytest.mark.asyncio
async def test_rag_chat_family_role():
    service = RagChatService()
    request = RagChatRequest(
        message="Vợ tôi đang mang thai 3 tháng đầu hay bị ốm nghén, tôi nên nấu những món gì bồi bổ và chăm sóc vợ thế nào?",
        stage=MaternalStage.PREGNANCY,
        user_role="FAMILY",
    )
    result = await service.chat(request)
    assert result.answer is not None
    assert len(result.answer) > 0
    assert result.has_critical_warning is False
    assert len(result.suggested_followups) > 0


@pytest.mark.asyncio
async def test_rag_chat_mother_with_survey_profile():
    service = RagChatService()
    request = RagChatRequest(
        message="Em nên ăn uống và vận động như thế nào trong tam cá nguyệt này?",
        stage=MaternalStage.PREGNANCY,
        gestational_age_weeks=24,
        user_role="MOTHER",
        survey_profile={
            "conditions": ["Tiền sử tiền sản giật nhẹ lần mang thai trước"],
            "allergies": ["Hải sản"],
        },
    )
    result = await service.chat(request)
    assert result.answer is not None
    assert len(result.answer) > 0
    assert result.has_critical_warning is False


def test_clean_latex_and_math_artifacts():
    service = RagChatService()
    raw = r"Huyết áp $\ge 140/90$ mmHg, sốt $\ge 38.5^\circ C$, đường huyết $\le 5.1$ mmol/L, $\approx 10$ ngày, $\pm 2$ tuần, $140/90$."
    cleaned = service._clean_latex_and_math_artifacts(raw)
    assert r"$\ge" not in cleaned
    assert r"\ge" not in cleaned
    assert r"$\le" not in cleaned
    assert r"\le" not in cleaned
    assert r"^\circ" not in cleaned
    assert "≥ 140/90" in cleaned
    assert "≥ 38.5°C" in cleaned
    assert "≤ 5.1" in cleaned
    assert "≈ 10" in cleaned
    assert "± 2" in cleaned


def test_strip_boilerplate_greeting():
    service = RagChatService()

    # Case 1: Standard boilerplate with "Chào chị, em là CareBridge AI Nurse Assistant..."
    raw_1 = (
        "Chào chị, em là CareBridge AI Nurse Assistant - Trợ lý Điều dưỡng Y tế ảo chuyên sâu về Chăm sóc Sức khỏe Mẹ bầu và Trẻ sơ sinh. "
        "Chúc mừng chị đang ở tuần thứ 10 của thai kỳ!\n\n"
        "[CRITICAL_WARNING]: NO\n"
        "[NEED_EXPERT_CONSULTATION]: NO\n"
        "[GỢI Ý CÂU HỎI]:\n- Câu hỏi 1?"
    )
    ans_1, crit_1, need_1, fu_1 = service._extract_llm_flags_and_followups(raw_1)
    assert "CareBridge AI Nurse Assistant" not in ans_1
    assert "Trợ lý Điều dưỡng Y tế ảo" not in ans_1
    assert "Chào chị" in ans_1
    assert "Chúc mừng chị đang ở tuần thứ 10" in ans_1
    assert crit_1 is False
    assert need_1 is False
    assert len(fu_1) == 1

    # Case 2: Boilerplate with "Chào mẹ bầu, tôi là CareBridge AI Nurse Assistant..."
    raw_2 = (
        "Chào mẹ bầu, tôi là CareBridge AI Nurse Assistant — Trợ lý Điều dưỡng Y tế ảo chuyên sâu về Chăm sóc Sức khỏe Mẹ bầu và Trẻ sơ sinh.\n\n"
        "Về việc bổ sung axit folic trước khi mang thai, mẹ nên lưu ý...\n\n"
        "[CRITICAL_WARNING]: NO\n"
        "[NEED_EXPERT_CONSULTATION]: NO"
    )
    ans_2, crit_2, need_2, fu_2 = service._extract_llm_flags_and_followups(raw_2)
    assert "CareBridge AI Nurse Assistant" not in ans_2
    assert "Chào mẹ bầu" in ans_2
    assert "Về việc bổ sung axit folic" in ans_2

    # Case 3: Already natural greeting "Chào mẹ, để bổ sung axit folic..."
    raw_3 = "Chào mẹ, để bổ sung axit folic đúng cách trước khi mang thai, mẹ cần lưu ý:"
    ans_3, _, _, _ = service._extract_llm_flags_and_followups(raw_3)
    assert ans_3 == "Chào mẹ, để bổ sung axit folic đúng cách trước khi mang thai, mẹ cần lưu ý:"


def test_build_rag_chat_prompt_instructions():
    from app.rag.prompts import build_rag_chat_prompt
    prompt = build_rag_chat_prompt(
        user_message="Bổ sung axit folic & vi chất thế nào trước khi mang thai?",
        context_chunks=[{"title": "Cẩm nang dinh dưỡng", "source": "Bộ Y Tế", "content": "Liều khuyến nghị 400-600 mcg."}],
        stage="PRECONCEPTION",
    )
    # Check that strict grounding and anti-hallucination instructions are present
    assert "PARAPHRASE TRUNG THỰC" in prompt
    assert "TUYỆT ĐỐI KHÔNG lặp lại câu chào giới thiệu bản thân" in prompt
    assert "BẮT BUỘC GHI NO" in prompt


