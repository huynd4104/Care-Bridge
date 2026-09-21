"""AI Nurse Assistant RAG Chat Service (Step 10 in Workflow)."""

from __future__ import annotations

import logging
from typing import List
from app.core.database import AsyncSession

from app.config import MEDICAL_DISCLAIMER
from app.constants.vital_thresholds import (
    BP_STAGE1_DIASTOLIC,
    BP_STAGE1_SYSTOLIC,
    EPDS_MILD_RISK_DEPRESSION_THRESHOLD,
    FETAL_MIN_KICKS_2H_THRESHOLD,
    GLUCOSE_POST_MEAL_1H_WARNING_THRESHOLD,
    TEMP_CRITICAL_FEVER_PREGNANCY,
)
from app.core.gemini import get_gemini_client
from app.models.schemas import (
    HealthMetricsLogRequest,
    RagChatRequest,
    RagChatResponse,
    SourceCitation,
)
from app.rag.prompts import (
    NURSE_ASSISTANT_SYSTEM_PROMPT,
    build_rag_chat_prompt,
)
from app.rag.vector_store import get_vector_store
from app.services.chat_red_flags import RED_FLAG_SELF_HARM, contains_urgent_referral, detect_red_flags

logger = logging.getLogger(__name__)

# Shown when retrieval finds no document but the message describes a danger sign. Only generic safety
# referral (no clinical claims), since there is no document to ground medical advice on.
GATE_EMERGENCY_ANSWER = (
    "Những gì bạn mô tả có thể là dấu hiệu cần được xử trí y tế khẩn cấp. "
    "Hệ thống chưa tìm thấy cẩm nang đối soát phù hợp để hướng dẫn chi tiết, vì vậy để đảm bảo an toàn, "
    "hãy gọi cấp cứu 115 hoặc đến ngay cơ sở y tế/bệnh viện sản - nhi gần nhất, không chờ đợi hay tự xử trí tại nhà."
)
GATE_SELF_HARM_ANSWER = (
    "Cảm ơn bạn đã chia sẻ, những suy nghĩ này rất quan trọng và bạn không phải đối mặt một mình. "
    "Ý nghĩ làm hại bản thân cần được hỗ trợ ngay: hãy báo ngay cho người thân để có người ở bên cạnh bạn, "
    "và gọi cấp cứu 115 hoặc đến cơ sở y tế gần nhất nếu bạn thấy không an toàn. "
    "Hãy liên hệ bác sĩ hoặc chuyên gia sức khỏe tâm thần ngay trong hôm nay."
)
# Prepended to a critical LLM answer (flagged by the LLM or by the red-flag screen) whose text has no urgent referral.
FLOOR_EMERGENCY_PREFIX = (
    "⚠️ Lưu ý an toàn: những gì bạn mô tả có thể là dấu hiệu cần được xử trí y tế khẩn cấp. "
    "Hãy gọi cấp cứu 115 hoặc đến ngay cơ sở y tế gần nhất, không chờ đợi hay tự xử trí tại nhà."
)
FLOOR_SELF_HARM_PREFIX = (
    "⚠️ Lưu ý an toàn: ý nghĩ làm hại bản thân cần được hỗ trợ ngay. Hãy báo người thân để có người ở bên cạnh bạn, "
    "gọi 115 hoặc đến cơ sở y tế gần nhất nếu thấy không an toàn, và liên hệ bác sĩ/chuyên gia sức khỏe tâm thần ngay hôm nay."
)


class RagChatService:
    def __init__(self) -> None:
        self.gemini = get_gemini_client()
        self.vector_store = get_vector_store()

    async def chat(
        self,
        request: RagChatRequest,
        session: AsyncSession | None = None,
    ) -> RagChatResponse:
        """Process user message, retrieve relevant medical chunks, and generate grounded answer via Gemini Flash."""
        # 1. Semantic Search across Maternal Knowledge pgvector
        search_query = request.message.strip()

        # 2. Semantic Search across Maternal Knowledge pgvector
        stage_filter = request.stage.value if request.stage else "PREGNANCY"
        retrieved_chunks = await self.vector_store.similarity_search(
            query=search_query,
            stage=stage_filter,
            top_k=4,
            session=session,
        )

        # 3. Format Clinical Context & Survey Profile based on User Role
        user_role = (request.user_role or "MOTHER").upper()
        is_family = user_role == "FAMILY"

        gestational_age_weeks = None if is_family else request.gestational_age_weeks
        recent_metrics_summary = None
        survey_profile_summary = None

        if not is_family:
            if request.recent_metrics:
                m = request.recent_metrics
                parts = []
                if m.systolic_bp and m.diastolic_bp:
                    parts.append(f"Huyết áp {m.systolic_bp}/{m.diastolic_bp} mmHg")
                if m.temperature:
                    parts.append(f"Thân nhiệt {m.temperature}°C")
                if m.blood_glucose:
                    parts.append(f"Đường huyết {m.blood_glucose} mmol/L")
                if m.fetal_movements_count is not None:
                    parts.append(f"Cử động thai {m.fetal_movements_count} lần")
                if m.symptoms:
                    parts.append(f"Triệu chứng: {', '.join(m.symptoms)}")
                recent_metrics_summary = ", ".join(parts)

            if request.survey_profile:
                survey_profile_summary = self._format_survey_profile(request.survey_profile)

        # 4. Filter relevant chunks (threshold >= 0.20)
        valid_chunks = [
            c for c in retrieved_chunks
            if c.get("similarity") is not None and c.get("similarity", 0.0) >= 0.20
        ]

        # Strict RAG Grounding Gate: If no relevant knowledge chunks retrieved, BLOCK ungrounded LLM generation
        if not valid_chunks:
            logger.warning("No relevant grounded RAG context chunks found in database; blocking ungrounded LLM generation.")
            # Safety floor: a failed retrieval must not hide an emergency behind a generic refusal.
            red_flags = detect_red_flags(request.message)
            if red_flags:
                logger.warning("Grounding gate: red flags %s detected; returning emergency referral.",
                               [f.category for f in red_flags])
                is_self_harm = any(f.category == RED_FLAG_SELF_HARM for f in red_flags)
                return RagChatResponse(
                    answer=GATE_SELF_HARM_ANSWER if is_self_harm else GATE_EMERGENCY_ANSWER,
                    has_critical_warning=True,
                    need_expert_consultation=True,
                    suggested_followups=self._generate_fallback_followups(is_emergency=True, is_family=is_family),
                    sources=[],
                    disclaimer=MEDICAL_DISCLAIMER,
                )
            fallback_followups = self._generate_fallback_followups(is_emergency=False, is_family=is_family)
            return RagChatResponse(
                answer=(
                    "Hệ thống CareBridge AI Nurse hiện chưa tìm thấy tài liệu cẩm nang y tế chính thống phù hợp với nội dung câu hỏi này trong cơ sở dữ liệu. "
                    "Để đảm bảo an toàn tuyệt đối, AI không tự ý đưa ra lời khuyên y khoa khi chưa có cẩm nang đối soát từ Bộ Y Tế / WHO. "
                    "Mẹ/Gia đình vui lòng tham khảo trực tiếp ý kiến Bác sĩ chuyên khoa hoặc đặt lại câu hỏi cụ thể hơn về sức khỏe thai sản nhé!"
                ),
                has_critical_warning=False,
                need_expert_consultation=True,
                suggested_followups=fallback_followups,
                sources=[],
                disclaimer=MEDICAL_DISCLAIMER,
            )

        history_dicts = [
            {"role": msg.role, "content": msg.content}
            for msg in request.conversation_history
        ] if request.conversation_history else None

        prompt = build_rag_chat_prompt(
            user_message=request.message,
            context_chunks=valid_chunks,
            stage=stage_filter,
            gestational_age_weeks=gestational_age_weeks,
            user_role=user_role,
            survey_profile_summary=survey_profile_summary,
            recent_metrics_summary=recent_metrics_summary,
            conversation_history=history_dicts,
        )

        # 5. Call Gemini Flash Generator (Semantic reasoning & strict grounding)
        raw_answer = await self.gemini.generate_response(
            prompt=prompt,
            system_instruction=NURSE_ASSISTANT_SYSTEM_PROMPT,
        )

        # 6. Extract Dynamic Follow-up Suggestions & AI Clinical Decision Flags
        answer_text, has_critical_warning, need_expert_llm, dynamic_followups = self._extract_llm_flags_and_followups(raw_answer)

        # Clean any LaTeX math artifacts from output
        answer_text = self._clean_latex_and_math_artifacts(answer_text)
        dynamic_followups = [self._clean_latex_and_math_artifacts(f) for f in dynamic_followups]

        # Safety floor: the LLM decides the critical flag from whatever chunks were retrieved; when those
        # chunks are off-topic it can answer "no information" with [CRITICAL_WARNING]: NO for a real emergency.
        # A critical flag is not enough either: in a live run the LLM flagged a febrile newborn as critical but its
        # answer only quoted an off-topic chunk and never told the parent to seek care. Whenever the message is an
        # emergency, the answer text itself must carry the referral.
        red_flags = detect_red_flags(request.message)
        if red_flags and not has_critical_warning:
            logger.warning("Red flags %s detected but LLM returned no critical warning; forcing emergency.",
                           [f.category for f in red_flags])
            has_critical_warning = True
        if has_critical_warning and not contains_urgent_referral(answer_text):
            logger.warning("Critical answer without an urgent referral; prepending safety floor.")
            is_self_harm = any(f.category == RED_FLAG_SELF_HARM for f in red_flags)
            prefix = FLOOR_SELF_HARM_PREFIX if is_self_harm else FLOOR_EMERGENCY_PREFIX
            answer_text = f"{prefix}\n\n{answer_text}"

        if has_critical_warning:
            if is_family:
                emergency_chips = ["Gọi cấp cứu 115 cho mẹ ngay?", "Bệnh viện phụ sản gần nhất?"]
            else:
                emergency_chips = ["Gọi cấp cứu 115 ngay?", "Bệnh viện phụ sản gần nhất?"]
            dynamic_followups = (emergency_chips + [f for f in dynamic_followups if f not in emergency_chips])[:3]
        elif not dynamic_followups:
            dynamic_followups = self._generate_fallback_followups(has_critical_warning, is_family=is_family)

        # Check if the AI answered with an out-of-scope refusal
        is_refusal = any(
            phrase in answer_text.lower()
            for phrase in [
                "ngoài phạm vi",
                "không giải đáp các chủ đề ngoài",
                "chuyên biệt về chăm sóc sức khỏe",
                "chưa tìm thấy tài liệu cẩm nang y tế chính thống",
            ]
        )

        # 7. Format Source Citations (Relevance Filter + Smart Deduplication)
        citations: List[SourceCitation] = []
        if not is_refusal:
            seen_keys = set()
            seen_titles_with_specific_sections = set()

            # First pass: identify titles that already have specific detailed sub-sections
            for doc in valid_chunks:
                title = doc.get("title", "Cẩm nang").strip()
                section = doc.get("section")
                if section and section.strip() and section.strip().lower() != title.lower():
                    seen_titles_with_specific_sections.add(title.lower())

            for doc in valid_chunks:
                title = doc.get("title", "Cẩm nang").strip()
                section = doc.get("section")
                if section:
                    section = section.strip()

                # If section is identical to title, avoid repeating "(Title)"
                if section and section.lower() == title.lower():
                    # If we already cite specific sections of this document, skip the generic root title chunk
                    if title.lower() in seen_titles_with_specific_sections:
                        continue
                    section = None

                key = f"{title.lower()}_{section.lower() if section else ''}"
                if key in seen_keys:
                    continue
                seen_keys.add(key)

                citations.append(
                    SourceCitation(
                        title=title,
                        source=doc.get("source", "Bộ Y Tế"),
                        section=section,
                        snippet=self._clean_latex_and_math_artifacts(doc.get("content", "")[:250]) + "...",
                        similarity_score=doc.get("similarity"),
                    )
                )

        # Check if objective health metrics logged warrant expert consult (Clinical Safety Guardrail)
        has_abnormal_metrics = self._check_abnormal_metrics_guardrail(request.recent_metrics)
        need_expert_consultation = has_critical_warning or need_expert_llm or has_abnormal_metrics

        return RagChatResponse(
            answer=answer_text.strip(),
            has_critical_warning=has_critical_warning,
            need_expert_consultation=need_expert_consultation,
            suggested_followups=dynamic_followups,
            sources=citations,
            disclaimer=MEDICAL_DISCLAIMER,
        )

    @staticmethod
    def _clean_latex_and_math_artifacts(text: str) -> str:
        """Removes LaTeX math notation and replaces with clean Unicode symbols."""
        if not text:
            return text
        import re

        cleaned = text
        replacements = [
            (r"\$\\ge\s*([^$]*)\$", r"≥ \1"),
            (r"\$\\le\s*([^$]*)\$", r"≤ \1"),
            (r"\$\\geq\s*([^$]*)\$", r"≥ \1"),
            (r"\$\\leq\s*([^$]*)\$", r"≤ \1"),
            (r"\$\\ge\$", "≥"),
            (r"\$\\le\$", "≤"),
            (r"\$\\geq\$", "≥"),
            (r"\$\\leq\$", "≤"),
            (r"\$\\ge\b", "≥"),
            (r"\$\\le\b", "≤"),
            (r"\$\\geq\b", "≥"),
            (r"\$\\leq\b", "≤"),
            (r"\\ge\b", "≥"),
            (r"\\le\b", "≤"),
            (r"\\geq\b", "≥"),
            (r"\\leq\b", "≤"),
            (r"\$\^\\circ\s*C\$", "°C"),
            (r"\^\\circ\s*C", "°C"),
            (r"\$\^\\circ\$", "°"),
            (r"\^\\circ", "°"),
            (r"\$\\approx\$", "≈"),
            (r"\\approx\b", "≈"),
            (r"\$\\pm\$", "±"),
            (r"\\pm\b", "±"),
            (r"\$\\times\$", "×"),
            (r"\\times\b", "×"),
        ]
        for pattern, repl in replacements:
            cleaned = re.sub(pattern, repl, cleaned)

        # Remove single $ wrapping around comparison expressions like $≥ 140/90$ or $>= 140$
        cleaned = re.sub(r"\$([≥≤><=+\-\d\.\s/]+)\$", r"\1", cleaned)
        return cleaned

    def _extract_llm_flags_and_followups(self, text: str) -> tuple[str, bool, bool, List[str]]:
        """Extracts dynamic clinical decision flags and follow-up questions generated by Gemini LLM."""
        has_critical_warning = False
        need_expert_from_llm = False
        cleaned_text = text

        # 1. Extract [CRITICAL_WARNING] tag if present
        if "[CRITICAL_WARNING]:" in cleaned_text:
            parts = cleaned_text.split("[CRITICAL_WARNING]:", 1)
            before_tag = parts[0]
            after_tag = parts[1]
            flag_line = after_tag.split("\n", 1)[0].strip().upper()
            if "YES" in flag_line or "TRUE" in flag_line:
                has_critical_warning = True
            rest = after_tag.split("\n", 1)[1] if "\n" in after_tag else ""
            cleaned_text = before_tag.strip() + ("\n\n" + rest.strip() if rest.strip() else "")

        # 2. Extract [NEED_EXPERT_CONSULTATION] tag if present
        if "[NEED_EXPERT_CONSULTATION]:" in cleaned_text:
            parts = cleaned_text.split("[NEED_EXPERT_CONSULTATION]:", 1)
            before_tag = parts[0]
            after_tag = parts[1]
            flag_line = after_tag.split("\n", 1)[0].strip().upper()
            if "YES" in flag_line or "TRUE" in flag_line:
                need_expert_from_llm = True
            rest = after_tag.split("\n", 1)[1] if "\n" in after_tag else ""
            cleaned_text = before_tag.strip() + ("\n\n" + rest.strip() if rest.strip() else "")

        # 3. Strip repetitive boilerplate self-introductions while preserving warm greeting (e.g. "Chào mẹ,")
        import re
        cleaned_text = re.sub(
            r"^(Chào\s+[^,\n]+[.,!:]?\s*)?(?:em|tôi|mình)\s+là\s+(?:CareBridge\s+AI\s+Nurse\s+Assistant|Trợ lý Điều dưỡng Y tế)[^.\n]*[.\n]+\s*",
            lambda m: (m.group(1).rstrip() + "\n\n") if m.group(1) else "",
            cleaned_text.strip(),
            flags=re.IGNORECASE,
        ).strip()

        # 4. Extract follow-up suggestions
        tag_candidates = [
            "[GỢI Ý CÂU HỎI]:",
            "[GỢI Ý CÂU HỎI TIẾP THEO]:",
            "[SUGGESTED_QUESTIONS]:",
            "[GỢI Ý]:",
        ]

        found_tag = None
        for tag in tag_candidates:
            if tag in cleaned_text:
                found_tag = tag
                break

        if not found_tag:
            return cleaned_text.strip(), has_critical_warning, need_expert_from_llm, []

        parts = cleaned_text.split(found_tag, 1)
        main_answer = parts[0].strip()
        followup_raw = parts[1].strip()

        followups: List[str] = []
        for line in followup_raw.splitlines():
            cleaned = line.strip().lstrip("-*•123456789.) ").strip()
            if cleaned and len(cleaned) > 3:
                if not cleaned.endswith("?"):
                    cleaned += "?"
                followups.append(cleaned)

        return main_answer, has_critical_warning, need_expert_from_llm, followups[:3]

    @staticmethod
    def _format_survey_profile(profile: dict | None) -> str | None:
        """Format medical history and risk factors from onboarding survey into a concise clinical string."""
        if not profile or not isinstance(profile, dict):
            return None
        parts = []
        conditions = profile.get("conditions") or profile.get("medicalHistory") or profile.get("riskFactors")
        if conditions:
            if isinstance(conditions, list):
                parts.append(f"Tiền sử bệnh lý/rủi ro: {', '.join(str(c) for c in conditions)}")
            elif isinstance(conditions, str):
                parts.append(f"Tiền sử bệnh lý: {conditions}")

        allergies = profile.get("allergies")
        if allergies:
            if isinstance(allergies, list):
                parts.append(f"Dị ứng: {', '.join(str(a) for a in allergies)}")
            elif isinstance(allergies, str):
                parts.append(f"Dị ứng: {allergies}")

        notes = profile.get("notes") or profile.get("specialNotes")
        if notes and isinstance(notes, str):
            parts.append(f"Ghi chú: {notes}")

        return "; ".join(parts) if parts else None

    @staticmethod
    def _check_abnormal_metrics_guardrail(metrics: HealthMetricsLogRequest | None) -> bool:
        """Evaluates numerical clinical thresholds from structured logged metrics (ACOG/WHO Standards)."""
        if not metrics:
            return False
        if (metrics.systolic_bp and metrics.systolic_bp >= BP_STAGE1_SYSTOLIC) or (
            metrics.diastolic_bp and metrics.diastolic_bp >= BP_STAGE1_DIASTOLIC
        ):
            return True
        if metrics.temperature and metrics.temperature >= TEMP_CRITICAL_FEVER_PREGNANCY:
            return True
        if metrics.blood_glucose and metrics.blood_glucose >= GLUCOSE_POST_MEAL_1H_WARNING_THRESHOLD:
            return True
        if metrics.epds_score and metrics.epds_score >= EPDS_MILD_RISK_DEPRESSION_THRESHOLD:
            return True
        if metrics.fetal_movements_count is not None and metrics.fetal_movements_count < FETAL_MIN_KICKS_2H_THRESHOLD:
            return True
        return False

    def _generate_fallback_followups(self, is_emergency: bool, is_family: bool = False) -> List[str]:
        """Minimal fallback only used if Gemini fails to provide dynamic follow-up tags."""
        if is_emergency:
            if is_family:
                return [
                    "Bệnh viện phụ sản cấp cứu gần nhất ở đâu?",
                    "Gọi cấp cứu 115 cho mẹ bầu như thế nào?",
                    "Gia đình cần chuẩn bị giấy tờ gì khi đưa mẹ đi viện?",
                ]
            return [
                "Bệnh viện phụ sản gần nhất ở đâu?",
                "Gọi cấp cứu 115 như thế nào?",
                "Cần chuẩn bị giấy tờ gì khi vào viện cấp cứu?",
            ]
        if is_family:
            return [
                "Món ăn và chế độ dinh dưỡng bồi bổ tốt nhất cho mẹ?",
                "Cách chăm sóc và massage giúp mẹ giảm đau lưng, mệt mỏi?",
                "Các dấu hiệu nguy hiểm của mẹ mà gia đình cần đưa đi viện ngay?",
            ]
        return [
            "Các mốc khám thai quan trọng cần nhớ?",
            "Chế độ dinh dưỡng khoa học theo từng giai đoạn?",
            "Dấu hiệu bất thường cần đến cơ sở y tế?",
        ]


rag_chat_service = RagChatService()


def get_rag_chat_service() -> RagChatService:
    return rag_chat_service
