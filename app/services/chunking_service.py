from dataclasses import dataclass

import tiktoken

from app.core.config import settings


@dataclass
class TextChunk:
    content: str
    chunk_index: int
    page_number: int | None = None


class ChunkingService:
    def __init__(self, max_tokens: int | None = None) -> None:
        self.max_tokens = max_tokens or settings.max_chunk_tokens
        try:
            self._encoding = tiktoken.get_encoding("cl100k_base")
        except Exception:
            self._encoding = None

    def count_tokens(self, text: str) -> int:
        if not text.strip():
            return 0
        if self._encoding:
            return len(self._encoding.encode(text))
        return max(1, len(text) // 4)

    def chunk_text(
        self, text: str, page_number: int | None = None
    ) -> list[TextChunk]:
        cleaned = text.strip()
        if not cleaned:
            return []

        paragraphs = [p.strip() for p in cleaned.split("\n\n") if p.strip()]
        chunks: list[TextChunk] = []
        buffer = ""
        index = 0

        for paragraph in paragraphs:
            candidate = f"{buffer}\n\n{paragraph}".strip() if buffer else paragraph
            if self.count_tokens(candidate) <= self.max_tokens:
                buffer = candidate
                continue

            if buffer:
                chunks.append(
                    TextChunk(content=buffer, chunk_index=index, page_number=page_number)
                )
                index += 1
                buffer = ""

            if self.count_tokens(paragraph) <= self.max_tokens:
                buffer = paragraph
            else:
                words = paragraph.split()
                word_buffer: list[str] = []
                for word in words:
                    test = " ".join(word_buffer + [word])
                    if self.count_tokens(test) <= self.max_tokens:
                        word_buffer.append(word)
                    else:
                        if word_buffer:
                            chunks.append(
                                TextChunk(
                                    content=" ".join(word_buffer),
                                    chunk_index=index,
                                    page_number=page_number,
                                )
                            )
                            index += 1
                        word_buffer = [word]
                if word_buffer:
                    buffer = " ".join(word_buffer)

        if buffer.strip():
            chunks.append(
                TextChunk(content=buffer.strip(), chunk_index=index, page_number=page_number)
            )

        return [c for c in chunks if c.content.strip()]
