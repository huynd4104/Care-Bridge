"""AI Nurse Assistant RAG Chat Service (Step 10 in Workflow)."""

from __future__ import annotations

import logging
import re
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
from app.core.gemini import EmbeddingUnavailableError, GeminiUnavailableError, get_gemini_client
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
from app.services.chat_red_flags import (
    RED_FLAG_SELF_HARM,
    detect_red_flags,
    leads_with_urgent_referral,
    strip_diacritics,
)

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
# Returned when no generation model is available (no API key, quota exhausted, every fallback failed).
# Deliberately contains no medical content: the previous hard-coded "safe" answer was ungrounded advice
# that still shipped with real document citations attached.
BLANK_MESSAGE_ANSWER = (
    "Mình chưa nhận được nội dung câu hỏi của bạn. "
    "Bạn vui lòng mô tả cụ thể hơn điều đang băn khoăn về sức khỏe mẹ và bé "
    "(ví dụ: tuần thai, triệu chứng đang gặp, hoặc chủ đề muốn tìm hiểu) để mình hỗ trợ chính xác nhé!"
)
# Minimum cosine similarity for a retrieved chunk to be usable as grounding.
RELEVANCE_THRESHOLD = 0.20
SERVICE_UNAVAILABLE_ANSWER = (
    "Hệ thống AI Nurse đang tạm thời gián đoạn kết nối nên chưa thể tra cứu cẩm nang y tế cho câu hỏi này. "
    "Để đảm bảo an toàn, CareBridge không đưa ra lời khuyên y khoa khi chưa đối soát được tài liệu chính thống. "
    "Mẹ/Gia đình vui lòng thử lại sau ít phút, hoặc liên hệ trực tiếp Bác sĩ chuyên khoa nếu cần giải đáp gấp."
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

        user_role = (request.user_role or "MOTHER").upper()
        is_family = user_role == "FAMILY"

        # A blank or content-free message ("   ", "?????", emoji only) has nothing to embed: retrieval
        # returns noise and the grounding gate then answers it as if a medical question had been asked.
        if not self._has_answerable_content(search_query):
            return RagChatResponse(
                answer=BLANK_MESSAGE_ANSWER,
                has_critical_warning=False,
                need_expert_consultation=False,
                suggested_followups=self._generate_fallback_followups(is_emergency=False, is_family=is_family),
                sources=[],
                disclaimer=MEDICAL_DISCLAIMER,
            )

        # 2. Semantic Search across Maternal Knowledge pgvector.
        # Multi-turn query expansion: a follow-up that points back at an earlier turn ("Nó có nguy hiểm
        # đến em bé không ạ?") names no symptom, so searching it verbatim cannot reach the guidance the
        # mother is asking about. Expansion is conditional rather than unconditional - always pasting the
        # history in drags stale symptoms into an unrelated new question and pulls retrieval off topic.
        stage_filter = request.stage.value if request.stage else "PREGNANCY"
        expanded_query = self._expand_with_history(search_query, request.conversation_history)
        first_query = (
            expanded_query
            if (expanded_query != search_query and self._looks_like_followup(search_query))
            else search_query
        )

        try:
            retrieved_chunks = await self.vector_store.similarity_search(
                query=first_query, stage=stage_filter, top_k=4, session=session,
            )
            # Second pass: the heuristic above only catches obvious follow-ups. If a plain search came
            # back with nothing grounded and history is available, retry expanded before refusing.
            if first_query == search_query and expanded_query != search_query and not self._grounded(retrieved_chunks):
                logger.info("Plain query found nothing grounded; retrying with history-expanded query.")
                expanded_chunks = await self.vector_store.similarity_search(
                    query=expanded_query, stage=stage_filter, top_k=4, session=session,
                )
                if self._grounded(expanded_chunks):
                    retrieved_chunks = expanded_chunks
        except EmbeddingUnavailableError:
            # Searching with a pseudo-embedding returns rows unrelated to the question and ships them as
            # official citations, so an embedding outage degrades exactly like a generation outage.
            logger.error("Embedding unavailable; refusing to search with a pseudo-embedding.")
            return self._service_outage_response(request, is_family=is_family)

        # 3. Format Clinical Context & Survey Profile based on User Role
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

        # 4. Filter relevant chunks
        valid_chunks = [c for c in retrieved_chunks if self._is_relevant(c)]

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
        try:
            raw_answer = await self.gemini.generate_response(
                prompt=prompt,
                system_instruction=NURSE_ASSISTANT_SYSTEM_PROMPT,
            )
        except GeminiUnavailableError:
            # No generation available. Degrade explicitly with no medical content and no citations, but
            # never let an outage swallow an emergency: the deterministic red-flag screen still applies.
            logger.error("Gemini generation unavailable; returning service-outage answer without citations.")
            return self._service_outage_response(request, is_family=is_family)

        # 6. Extract Dynamic Follow-up Suggestions & AI Clinical Decision Flags
        (
            answer_text,
            has_critical_warning,
            need_expert_llm,
            llm_out_of_scope,
            dynamic_followups,
        ) = self._extract_llm_flags_and_followups(raw_answer)

        # Clean any LaTeX math artifacts from output
        answer_text = self._clean_latex_and_math_artifacts(answer_text)
        dynamic_followups = [self._clean_latex_and_math_artifacts(f) for f in dynamic_followups]

        # Safety floor: the LLM decides the critical flag from whatever chunks were retrieved; when those
        # chunks are off-topic it can answer "no information" with [CRITICAL_WARNING]: NO for a real emergency.
        # A critical flag is not enough either: in a live run the LLM flagged a febrile newborn as critical but its
        # answer only quoted an off-topic chunk and never told the parent to seek care. Whenever the message is an
        # emergency, the answer text itself must carry the referral - and in its opening paragraph, since a referral
        # placed after the routine advice is read too late (audit C7).
        red_flags = detect_red_flags(request.message)
        if red_flags and not has_critical_warning:
            logger.warning("Red flags %s detected but LLM returned no critical warning; forcing emergency.",
                           [f.category for f in red_flags])
            has_critical_warning = True
        if has_critical_warning and not leads_with_urgent_referral(answer_text):
            logger.warning("Critical answer does not open with an urgent referral; prepending safety floor.")
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

        # Check if the AI answered with an out-of-scope refusal. The [OUT_OF_SCOPE] tag is authoritative:
        # matching refusal wording alone was unreliable because the prompt never mandated a fixed phrase,
        # so a politely-worded refusal ("mình là trợ lý mẹ và bé, câu này mình không hỗ trợ") still shipped
        # maternal handbook citations. The phrase list is kept only as a fallback for answers missing the tag.
        is_refusal = llm_out_of_scope or any(
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
        # An out-of-scope question ("giá Bitcoin hôm nay?") must not tell the user to see an obstetrician.
        # A red flag or an abnormal logged metric still overrides this, whatever the question was about.
        if is_refusal and not (has_critical_warning or has_abnormal_metrics):
            need_expert_consultation = False

        return RagChatResponse(
            answer=answer_text.strip(),
            has_critical_warning=has_critical_warning,
            need_expert_consultation=need_expert_consultation,
            suggested_followups=dynamic_followups,
            sources=citations,
            disclaimer=MEDICAL_DISCLAIMER,
        )

    def _service_outage_response(self, request: RagChatRequest, is_family: bool) -> RagChatResponse:
        """Degrade with no medical content and no citations, without swallowing an emergency.

        Shared by the generation outage and the embedding outage: in both cases the assistant has lost
        the ability to answer truthfully, but the deterministic red-flag screen still works and an
        emergency must still be escalated.
        """
        red_flags = detect_red_flags(request.message)
        if red_flags:
            is_self_harm = any(f.category == RED_FLAG_SELF_HARM for f in red_flags)
            return RagChatResponse(
                answer=GATE_SELF_HARM_ANSWER if is_self_harm else GATE_EMERGENCY_ANSWER,
                has_critical_warning=True,
                need_expert_consultation=True,
                suggested_followups=self._generate_fallback_followups(is_emergency=True, is_family=is_family),
                sources=[],
                disclaimer=MEDICAL_DISCLAIMER,
            )
        return RagChatResponse(
            answer=SERVICE_UNAVAILABLE_ANSWER,
            has_critical_warning=False,
            need_expert_consultation=self._check_abnormal_metrics_guardrail(request.recent_metrics),
            suggested_followups=self._generate_fallback_followups(is_emergency=False, is_family=is_family),
            sources=[],
            disclaimer=MEDICAL_DISCLAIMER,
        )

    @staticmethod
    def _is_relevant(chunk: dict) -> bool:
        """True when a retrieved chunk is close enough to be used as grounding."""
        similarity = chunk.get("similarity")
        return similarity is not None and similarity >= RELEVANCE_THRESHOLD

    @classmethod
    def _grounded(cls, chunks) -> bool:
        """True when at least one retrieved chunk clears the relevance threshold."""
        return any(cls._is_relevant(c) for c in (chunks or []))

    @staticmethod
    def _expand_with_history(message: str, conversation_history) -> str:
        """Fold the mother's own recent turns into the query so a follow-up can be searched on.

        "Nó có nguy hiểm đến em bé không ạ?" names no symptom - the headache and swollen feet live in
        her previous message - so searching it verbatim cannot reach the preeclampsia guidance she is
        actually asking about.

        Only the user's turns are folded in: the assistant's replies are long and full of generic
        maternal vocabulary that would dominate the query vector.
        """
        query = (message or "").strip()
        if not conversation_history:
            return query
        user_turns = [
            (msg.content or "").strip()
            for msg in conversation_history
            if getattr(msg, "role", None) in ("user", "human") and (msg.content or "").strip()
        ]
        if not user_turns:
            return query
        return " ".join(user_turns[-2:] + ([query] if query else []))

    # A follow-up that points back at something already said instead of naming it. Matched on
    # accent-stripped text so messages typed without diacritics behave the same.
    _REFERENTIAL_FOLLOWUP = re.compile(
        r"\bno\b|\bvay\b|\bthe a\b|\bthe khong\b|"
        r"(cai|dieu|viec|tinh trang|trieu chung|benh|hien tuong|chuyen)\s+(nay|do|ay)"
    )

    @classmethod
    def _looks_like_followup(cls, message: str) -> bool:
        """True when the message leans on earlier context instead of standing on its own."""
        text = strip_diacritics(message)
        if not text:
            return False
        if cls._REFERENTIAL_FOLLOWUP.search(text):
            return True
        # Very short questions ("Vậy ạ?", "Có sao không?") carry no searchable content either.
        return len(text.split()) <= 4

    @staticmethod
    def _has_answerable_content(message: str) -> bool:
        """True when the message carries at least one word to search on.

        Punctuation runs ("?????"), emoji-only messages and stray symbols embed to near-random vectors,
        so they must not be routed into retrieval and answered as though a question had been asked.
        """
        import re

        if not message or not message.strip():
            return False
        # Keep letters (any script) and digits; drop punctuation, symbols and emoji.
        meaningful = re.sub(r"[^\w]", "", message, flags=re.UNICODE)
        meaningful = re.sub(r"_", "", meaningful)
        return len(meaningful) >= 2

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

    @staticmethod
    def _extract_flag(text: str, tag_name: str) -> tuple[str, bool]:
        """Pull one decision tag out of the answer, returning the text without it and its boolean value.

        Matched permissively: the model routinely emits `**[CRITICAL_WARNING]:** YES`, a lowercase
        spelling, or a stray space before the colon. An exact-substring match left those variants in
        the answer, so the raw tag was rendered to the user.
        """
        import re

        # The markdown prefix is only consumed when it starts its own line, so a bolded closing "**" on
        # the preceding sentence ("...**đi khám ngay**\n[CRITICAL_WARNING]: YES") is not swallowed into
        # the tag match - which left the answer ending in an unclosed "**".
        pattern = re.compile(
            r"(?:^[ \t]*[*_#]*[ \t]*|[ \t]*)\[\s*" + tag_name + r"\s*\]\s*:[ \t]*",
            re.IGNORECASE | re.MULTILINE,
        )
        match = pattern.search(text)
        if not match:
            return text, False

        before_tag = text[: match.start()]
        after_tag = text[match.end():]
        flag_line, _, rest = after_tag.partition("\n")
        value = flag_line.strip().upper()
        is_set = "YES" in value or "TRUE" in value
        cleaned = before_tag.strip() + ("\n\n" + rest.strip() if rest.strip() else "")
        return cleaned, is_set

    def _extract_llm_flags_and_followups(self, text: str) -> tuple[str, bool, bool, bool, List[str]]:
        """Extracts dynamic clinical decision flags and follow-up questions generated by Gemini LLM."""
        cleaned_text = text

        # 1-3. Extract decision tags if present
        cleaned_text, has_critical_warning = self._extract_flag(cleaned_text, "CRITICAL_WARNING")
        cleaned_text, need_expert_from_llm = self._extract_flag(cleaned_text, "NEED_EXPERT_CONSULTATION")
        cleaned_text, out_of_scope = self._extract_flag(cleaned_text, "OUT_OF_SCOPE")

        # 4. Strip repetitive boilerplate self-introductions while preserving warm greeting (e.g. "Chào mẹ,")
        import re
        cleaned_text = re.sub(
            r"^(Chào\s+[^,\n]+[.,!:]?\s*)?(?:em|tôi|mình)\s+là\s+(?:CareBridge\s+AI\s+Nurse\s+Assistant|Trợ lý Điều dưỡng Y tế)[^.\n]*[.\n]+\s*",
            lambda m: (m.group(1).rstrip() + "\n\n") if m.group(1) else "",
            cleaned_text.strip(),
            flags=re.IGNORECASE,
        ).strip()

        # 5. Extract follow-up suggestions
        followup_tag = re.compile(
            r"[*_#\s]*\[\s*(?:GỢI Ý CÂU HỎI TIẾP THEO|GỢI Ý CÂU HỎI|SUGGESTED_QUESTIONS|GỢI Ý)\s*\]\s*:\s*",
            re.IGNORECASE,
        )
        match = followup_tag.search(cleaned_text)
        if not match:
            return cleaned_text.strip(), has_critical_warning, need_expert_from_llm, out_of_scope, []

        main_answer = cleaned_text[: match.start()].strip()
        followup_raw = cleaned_text[match.end():].strip()

        followups: List[str] = []
        for line in followup_raw.splitlines():
            cleaned = line.strip().lstrip("-*•123456789.) ").strip()
            # A chip is a short question. Prose that the model sometimes writes after the tag used to be
            # turned into a chip by blindly appending "?", producing paragraph-long suggestion buttons.
            if not cleaned or len(cleaned) <= 3 or len(cleaned) > 120:
                continue
            if not cleaned.endswith("?"):
                cleaned += "?"
            followups.append(cleaned)

        return main_answer, has_critical_warning, need_expert_from_llm, out_of_scope, followups[:3]

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
