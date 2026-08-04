"""
LLM transport — OpenAI client and Gemini HTTP for chat + ticket classify.

generate_answer/stream_answer: Knowledge Agent (RAG). classify_ticket_json: Slack
tickets only; trips LlmClassifyCircuit on Gemini 429.
"""

import logging
from collections.abc import AsyncGenerator, Sequence

import httpx
from openai import AsyncOpenAI

from app.core.config import settings
from app.core.llm_classify_circuit import LlmClassifyCircuit
from app.models.internal.domain import RagChunkItem
from app.prompts.knowledge_rag import KNOWLEDGE_AGENT_SYSTEM_PROMPT
from app.services.citation_parser import build_structured_fallback_answer

logger = logging.getLogger(__name__)

_CLASSIFY_HTTP_TIMEOUT_SECONDS = 8.0
_CLASSIFY_SYSTEM = "You classify support tickets. Reply with JSON only."


class LLMService:
    """Thin provider wrapper; routing policy lives in llm_registry + feature flags."""

    def __init__(self) -> None:
        self._client: AsyncOpenAI | None = None
        if settings.openai_api_key:
            self._client = AsyncOpenAI(api_key=settings.openai_api_key)

    @property
    def has_openai_client(self) -> bool:
        return self._client is not None

    @property
    def has_client(self) -> bool:
        return self.has_openai_client or bool(settings.gemini_api_key)

    def _structured_fallback(
        self,
        chunk_items: Sequence[RagChunkItem] | None,
        *,
        query: str,
    ) -> str:
        if chunk_items:
            return build_structured_fallback_answer(chunk_items, query=query)
        return (
            "I couldn't reach the language model right now. "
            "Please retry in a moment."
        )

    async def _gemini_complete(
        self,
        system: str,
        user: str,
        *,
        timeout_seconds: float = 60.0,
        trip_circuit_on_429: bool = False,
    ) -> str | None:
        model = settings.gemini_chat_model
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{model}:generateContent"
        )
        payload = {
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": user}]}],
            "generationConfig": {"temperature": 0.2},
        }
        try:
            async with httpx.AsyncClient(timeout=timeout_seconds) as client:
                response = await client.post(
                    url,
                    params={"key": settings.gemini_api_key},
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            if status == 429:
                if trip_circuit_on_429:
                    LlmClassifyCircuit.trip(reason="gemini_429")
                logger.warning("Gemini rate limited (429); using fallback")
            else:
                logger.warning("Gemini HTTP %s; using fallback", status)
            return None
        except httpx.HTTPError as exc:
            logger.warning("Gemini request failed: %s", exc)
            return None

        candidates = data.get("candidates") or []
        if not candidates:
            return None
        parts = candidates[0].get("content", {}).get("parts") or []
        text = "".join(part.get("text", "") for part in parts).strip()
        return text or None

    async def classify_ticket_json(self, message_text: str) -> str | None:
        """Fast LLM classify for Slack tickets. Returns raw JSON text or None."""
        if LlmClassifyCircuit.is_open():
            return None

        user = (
            f"Classify this Slack message:\n{message_text}\n\n"
            "Return JSON with keys: intent, priority (1-5), summary, department."
        )

        if self._client:
            try:
                response = await self._client.chat.completions.create(
                    model=settings.openai_chat_model,
                    messages=[
                        {"role": "system", "content": _CLASSIFY_SYSTEM},
                        {"role": "user", "content": user},
                    ],
                    temperature=0.2,
                    timeout=_CLASSIFY_HTTP_TIMEOUT_SECONDS,
                )
                return response.choices[0].message.content or None
            except Exception as exc:
                logger.warning("OpenAI classify failed: %s", exc)
                return None

        if settings.gemini_api_key:
            return await self._gemini_complete(
                _CLASSIFY_SYSTEM,
                user,
                timeout_seconds=_CLASSIFY_HTTP_TIMEOUT_SECONDS,
                trip_circuit_on_429=True,
            )

        return None

    async def generate_answer(
        self,
        query: str,
        context: str,
        *,
        chunk_items: Sequence[RagChunkItem] | None = None,
    ) -> str:
        system = KNOWLEDGE_AGENT_SYSTEM_PROMPT
        user = f"Retrieved chunks:\n{context}\n\nUser question: {query}"

        if self._client:
            response = await self._client.chat.completions.create(
                model=settings.openai_chat_model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                temperature=0.2,
            )
            return response.choices[0].message.content or ""

        if settings.gemini_api_key and context.strip():
            answer = await self._gemini_complete(system, user)
            if answer:
                return answer
            return self._structured_fallback(chunk_items, query=query)

        if not context.strip():
            return (
                "I don't have enough information in the knowledge base to answer that question."
            )
        return self._structured_fallback(chunk_items, query=query)

    async def stream_answer(
        self,
        query: str,
        context: str,
        *,
        chunk_items: Sequence[RagChunkItem] | None = None,
    ) -> AsyncGenerator[str, None]:
        if not context.strip():
            yield (
                "I don't have enough information in the knowledge base to answer "
                "that question."
            )
            return

        system = KNOWLEDGE_AGENT_SYSTEM_PROMPT
        user = f"Retrieved chunks:\n{context}\n\nUser question: {query}"

        if self._client:
            stream = await self._client.chat.completions.create(
                model=settings.openai_chat_model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                temperature=0.2,
                stream=True,
            )
            async for event in stream:
                delta = event.choices[0].delta.content
                if delta:
                    yield delta
            return

        if settings.gemini_api_key:
            answer = await self._gemini_complete(system, user)
            if answer:
                yield answer
                return

        text = self._structured_fallback(chunk_items, query=query)
        for word in text.split():
            yield word + " "
