"""Google GenAI Client with multi-model auto-fallback and error resilience."""

from __future__ import annotations

import logging
from typing import Optional
from google import genai
from google.genai import types
from app.config import GEMINI_SETTINGS

logger = logging.getLogger(__name__)

# Fallback model candidates if primary model is unavailable
FALLBACK_GENERATION_MODELS = [
    "gemini-flash-lite-latest",
    "gemini-2.5-flash",
    "gemini-flash-latest",
]

FALLBACK_EMBEDDING_MODELS = [
    "models/gemini-embedding-2",
    "models/gemini-embedding-2-preview",
    "models/gemini-embedding-001",
]


class EmbeddingUnavailableError(RuntimeError):
    """Raised when a query cannot be embedded because every API key is exhausted.

    Retrieval must fail loudly here. Searching with a deterministic pseudo-embedding "works" in the sense
    that it returns rows, but they are unrelated to the question and are then presented to the user as
    official Bộ Y Tế / WHO citations.
    """


class GeminiUnavailableError(RuntimeError):
    """Raised when no generation model could answer (no API key, quota exhausted, every fallback failed).

    Generation has no safe offline substitute: unlike embeddings, a fabricated answer would be
    ungrounded medical advice. Callers must degrade to an explicit service-outage message.
    """


class GeminiClient:
    def __init__(self) -> None:
        self._api_keys: list[str] = GEMINI_SETTINGS.api_keys
        self._current_key_idx: int = 0
        self._client: Optional[genai.Client] = None

        if GEMINI_SETTINGS.enabled and self._api_keys:
            self._init_client_for_current_key()
        else:
            logger.info("Gemini client running in offline/mock mode (no API key configured)")

    def _init_client_for_current_key(self) -> bool:
        if not self._api_keys:
            self._client = None
            return False
        import os
        for var in ("NO_PROXY", "no_proxy"):
            if var in os.environ and "::" in os.environ[var]:
                os.environ[var] = ",".join(p.strip() for p in os.environ[var].split(",") if "::" not in p)
        cur_key = self._api_keys[self._current_key_idx]
        masked = cur_key[:6] + "..." + cur_key[-4:] if len(cur_key) > 10 else "***"
        try:
            self._client = genai.Client(api_key=cur_key)
            logger.info(
                f"Gemini client initialized with Key #{self._current_key_idx + 1}/{len(self._api_keys)} ({masked}), "
                f"model={GEMINI_SETTINGS.model} embedding_model={GEMINI_SETTINGS.embedding_model}"
            )
            return True
        except Exception as e:
            logger.warning(f"Failed to initialize Gemini Client with Key #{self._current_key_idx + 1}: {e}")
            self._client = None
            return False

    def rotate_to_next_key(self) -> bool:
        """Switch to next API key if multiple keys are available."""
        if len(self._api_keys) > 1:
            self._current_key_idx = (self._current_key_idx + 1) % len(self._api_keys)
            logger.info(f"Tự động chuyển sang API Key tiếp theo: Key #{self._current_key_idx + 1}/{len(self._api_keys)}")
            return self._init_client_for_current_key()
        return False

    @property
    def is_available(self) -> bool:
        return self._client is not None

    async def embed_text(self, text: str) -> list[float]:
        """Generate a 768-dimensional vector embedding for a single text chunk.

        Raises EmbeddingUnavailableError when the API is configured but every key is exhausted.
        A pseudo-embedding is only returned in explicit offline mode: silently falling back to one for a
        live query made the search run against essentially random vectors, so a question about headache
        and swollen feet at 32 weeks retrieved "Bệnh bại liệt" and shipped it as a Bộ Y Tế citation.
        """
        if not text.strip():
            return [0.0] * GEMINI_SETTINGS.embedding_dimension

        if not GEMINI_SETTINGS.enabled:
            return self._mock_embedding(text)

        if self._client:
            import asyncio
            import re

            # One pass over the key ring: a daily quota is per key, so an exhausted key is retried on the
            # next one instead of degrading the whole service (embed_texts already did this).
            for _key_attempt in range(max(1, len(self._api_keys))):
                key_exhausted = False
                models_to_try = [GEMINI_SETTINGS.embedding_model] + [
                    m for m in FALLBACK_EMBEDDING_MODELS if m != GEMINI_SETTINGS.embedding_model
                ]
                for model_name in models_to_try:
                    max_retries = 4
                    for attempt in range(max_retries):
                        try:
                            def _call():
                                return self._client.models.embed_content(
                                    model=model_name,
                                    contents=text,
                                    config=types.EmbedContentConfig(
                                        output_dimensionality=GEMINI_SETTINGS.embedding_dimension
                                    ),
                                )

                            response = await asyncio.wait_for(
                                asyncio.to_thread(_call), timeout=GEMINI_SETTINGS.timeout_seconds
                            )
                            if hasattr(response, "embeddings") and response.embeddings:
                                return response.embeddings[0].values
                            if hasattr(response, "embedding") and response.embedding:
                                return response.embedding.values
                        except Exception as e:
                            err_msg = str(e)
                            if "perday" in err_msg.lower():
                                logger.warning(
                                    f"API Key #{self._current_key_idx + 1} đã hết hạn mức ngày "
                                    f"(1,000 requests/day) trên {model_name}!"
                                )
                                key_exhausted = True
                                break
                            if ("429" in err_msg or "RESOURCE_EXHAUSTED" in err_msg or "Too Many Requests" in err_msg) and attempt < max_retries - 1:
                                wait_sec = 5.0 * (attempt + 1)
                                m_delay = re.search(r"retry in ([0-9]+(?:\.[0-9]+)?)s", err_msg)
                                if m_delay:
                                    wait_sec = max(float(m_delay.group(1)) + 0.5, wait_sec)
                                logger.warning(
                                    f"Rate limit (429) on {model_name}. Waiting {wait_sec:.1f}s before retry (attempt {attempt+1}/{max_retries})..."
                                )
                                await asyncio.sleep(wait_sec)
                                continue
                            logger.debug(f"Embedding model {model_name} notice ({e}), trying next fallback...")
                            break
                    if key_exhausted:
                        break

                if not (key_exhausted and self.rotate_to_next_key()):
                    break

        raise EmbeddingUnavailableError(
            "No embedding available (every configured API key is exhausted or the embedding call failed). "
            "Refusing to search with a pseudo-embedding, which would return unrelated documents."
        )

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Generate vector embeddings for a list of text chunks with batching, throttling, and auto-retry."""
        if not texts:
            return []

        if not GEMINI_SETTINGS.enabled:
            return [self._mock_embedding(t) for t in texts]

        if self._client:
            models_to_try = [GEMINI_SETTINGS.embedding_model] + [
                m for m in FALLBACK_EMBEDDING_MODELS if m != GEMINI_SETTINGS.embedding_model
            ]
            batch_size = 50

            for model_name in models_to_try:
                try:
                    import asyncio
                    import re
                    embeddings = []
                    failed = False

                    for i in range(0, len(texts), batch_size):
                        batch = texts[i : i + batch_size]
                        # In google.genai, each text must be wrapped in types.Content to generate individual embeddings
                        batch_contents = [types.Content(parts=[types.Part.from_text(text=t)]) for t in batch]

                        max_retries = 5
                        batch_success = False
                        for attempt in range(max_retries):
                            try:
                                def _call_batch(contents=batch_contents):
                                    return self._client.models.embed_content(
                                        model=model_name,
                                        contents=contents,
                                        config=types.EmbedContentConfig(
                                            output_dimensionality=GEMINI_SETTINGS.embedding_dimension
                                        ),
                                    )

                                response = await asyncio.wait_for(
                                    asyncio.to_thread(_call_batch),
                                    timeout=GEMINI_SETTINGS.timeout_seconds,
                                )
                                if hasattr(response, "embeddings") and response.embeddings:
                                    embeddings.extend([e.values for e in response.embeddings])
                                    batch_success = True
                                    break
                                elif hasattr(response, "embedding") and response.embedding:
                                    embeddings.append(response.embedding.values)
                                    batch_success = True
                                    break
                            except Exception as e:
                                err_msg = str(e)
                                if "perday" in err_msg.lower():
                                    logger.warning(
                                        f"API Key #{self._current_key_idx + 1} đã hết hạn mức ngày (1,000 requests/day) trên {model_name}!"
                                    )
                                    if self.rotate_to_next_key():
                                        # Retry current batch with new rotated key
                                        continue
                                    else:
                                        logger.error("Đã hết toàn bộ API Key khả dụng cho ngày hôm nay.")
                                        break
                                if ("429" in err_msg or "RESOURCE_EXHAUSTED" in err_msg or "Too Many Requests" in err_msg) and attempt < max_retries - 1:
                                    wait_sec = 6.0 * (attempt + 1)
                                    m_delay = re.search(r"retry in ([0-9]+(?:\.[0-9]+)?)s", err_msg)
                                    if m_delay:
                                        wait_sec = max(float(m_delay.group(1)) + 1.0, wait_sec)
                                    logger.warning(
                                        f"Rate limit (429) on {model_name} (batch {i//batch_size + 1}). "
                                        f"Waiting {wait_sec:.1f}s before retry (attempt {attempt+1}/{max_retries})..."
                                    )
                                    await asyncio.sleep(wait_sec)
                                    continue
                                logger.warning(f"Batch embedding error on {model_name} (batch {i//batch_size + 1}): {e}")
                                break

                        if not batch_success:
                            failed = True
                            break

                        # Gentle throttle between batches to prevent triggering RPM rate limits
                        if i + batch_size < len(texts):
                            await asyncio.sleep(1.5)

                    if not failed and len(embeddings) == len(texts):
                        return embeddings
                except Exception as e:
                    logger.debug(f"Batch embedding model {model_name} notice ({e}), trying next fallback...")

        logger.warning("All live embedding models failed or rate-limited; falling back to offline deterministic embeddings.")
        return [self._mock_embedding(t) for t in texts]

    async def generate_response(
        self,
        prompt: str,
        system_instruction: str,
        temperature: float | None = None,
    ) -> str:
        """Generate a response with automatic model fallback for maximum uptime."""
        temp = temperature if temperature is not None else GEMINI_SETTINGS.temperature

        if self._client:
            models_to_try = [GEMINI_SETTINGS.model] + [
                m for m in FALLBACK_GENERATION_MODELS if m != GEMINI_SETTINGS.model
            ]

            for model_name in models_to_try:
                try:
                    import asyncio

                    def _call():
                        return self._client.models.generate_content(
                            model=model_name,
                            contents=prompt,
                            config=types.GenerateContentConfig(
                                system_instruction=system_instruction,
                                temperature=temp,
                            ),
                        )

                    response = await asyncio.wait_for(asyncio.to_thread(_call), timeout=GEMINI_SETTINGS.timeout_seconds)
                    if response and response.text:
                        return response.text.strip()
                except Exception as e:
                    logger.warning(
                        f"Notice calling model '{model_name}' ({e}), attempting fallback model..."
                    )
                    continue

        # No usable generation. Never invent medical content here: a hard-coded "safe" answer would be
        # ungrounded advice that the caller then ships next to real document citations, which is exactly
        # the hallucination the RAG grounding gate exists to prevent. Let the caller degrade explicitly.
        raise GeminiUnavailableError(
            "No Gemini generation available (client not configured or every model call failed)."
        )

    def _mock_embedding(self, text: str) -> list[float]:
        """Generate a deterministic semantic-weighted 768-dim vector for testing/fallback without external API."""
        import hashlib
        import math
        import re

        dim = GEMINI_SETTINGS.embedding_dimension
        vec = [0.0] * dim
        clean = re.sub(r"[^\w\s]", " ", text.lower())
        raw_words = clean.split()
        if not raw_words:
            return [0.0] * dim

        stopwords = {
            "là", "và", "của", "cho", "các", "những", "được", "có", "trong",
            "để", "khi", "ở", "gì", "thế", "nào", "ạ", "nhé", "với", "từ",
            "ra", "vào", "thì", "cần", "nên", "hãy", "bị", "do", "về",
        }
        words = [w for w in raw_words if (w not in stopwords and len(w) > 1) or w.isdigit()]
        if not words:
            words = raw_words

        # 1. Unigrams with frequency weighting
        word_freq: dict[str, int] = {}
        for w in words:
            word_freq[w] = word_freq.get(w, 0) + 1

        for w, count in word_freq.items():
            weight = 1.0 + math.log(count)
            h = int(hashlib.sha256(w.encode("utf-8")).hexdigest(), 16)
            idx = h % dim
            sign = 1.0 if ((h >> 8) & 1) else -1.0
            vec[idx] += sign * weight * 3.0

        # 2. Bigrams (capture phrases like "vi chất", "3 tháng đầu", "axit folic")
        for i in range(len(words) - 1):
            bigram = f"{words[i]}_{words[i+1]}"
            h = int(hashlib.sha256(bigram.encode("utf-8")).hexdigest(), 16)
            idx = h % dim
            sign = 1.0 if ((h >> 8) & 1) else -1.0
            vec[idx] += sign * 5.0

        # 3. Trigrams
        for i in range(len(words) - 2):
            trigram = f"{words[i]}_{words[i+1]}_{words[i+2]}"
            h = int(hashlib.sha256(trigram.encode("utf-8")).hexdigest(), 16)
            idx = h % dim
            sign = 1.0 if ((h >> 8) & 1) else -1.0
            vec[idx] += sign * 6.0

        # Normalize vector
        norm = math.sqrt(sum(x * x for x in vec)) or 1.0
        return [x / norm for x in vec]


# Global singleton client
gemini_client = GeminiClient()


def get_gemini_client() -> GeminiClient:
    return gemini_client
