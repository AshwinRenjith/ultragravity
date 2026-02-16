from __future__ import annotations

import math
import re
from dataclasses import dataclass


@dataclass(frozen=True)
class SummaryChunk:
    index: int
    text: str
    score: float


class ContextShaper:
    @staticmethod
    def compact_text(text: str) -> str:
        return re.sub(r"\s+", " ", text).strip()

    def build_delta_context(
        self,
        state_changed: bool,
        changed_by_url: bool,
        changed_by_image: bool,
        last_action: str | None,
        current_url: str,
        memory_hints: list[str] | None = None,
    ) -> str:
        parts = [
            f"state_changed={state_changed}",
            f"changed_by_url={changed_by_url}",
            f"changed_by_image={changed_by_image}",
            f"last_action={last_action or 'none'}",
        ]
        if current_url:
            parts.append(f"url={current_url}")
        if memory_hints:
            compact_hints = [self.compact_text(hint) for hint in memory_hints if hint and hint.strip()]
            if compact_hints:
                parts.append("memory=" + " | ".join(compact_hints[:5]))
        return "; ".join(parts)

    def chunk_text(self, content: str, chunk_chars: int, overlap_chars: int) -> list[str]:
        text = self.compact_text(content)
        if not text:
            return []

        chunk_chars = max(500, chunk_chars)
        overlap_chars = max(0, min(overlap_chars, chunk_chars // 2))

        chunks: list[str] = []
        start = 0
        while start < len(text):
            end = min(len(text), start + chunk_chars)
            chunk = text[start:end]
            chunks.append(chunk)
            if end >= len(text):
                break
            start = max(0, end - overlap_chars)
        return chunks

    @staticmethod
    def _keyword_set(query: str) -> set[str]:
        keywords = re.findall(r"[a-zA-Z0-9]{3,}", query.lower())
        return set(keywords)

    def rank_chunks(self, chunks: list[str], query: str, top_k: int) -> list[SummaryChunk]:
        keywords = self._keyword_set(query)
        if not keywords:
            keywords = {"summary"}

        ranked: list[SummaryChunk] = []
        for index, chunk in enumerate(chunks):
            lowered = chunk.lower()
            hits = sum(1 for keyword in keywords if keyword in lowered)
            density = hits / max(1, math.log2(len(chunk) + 8))
            score = float(hits + density)
            ranked.append(SummaryChunk(index=index, text=chunk, score=score))

        ranked.sort(key=lambda item: item.score, reverse=True)
        return ranked[: max(1, min(top_k, len(ranked)))]
