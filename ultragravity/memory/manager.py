from __future__ import annotations

import json
from uuid import uuid4

from .models import MemoryEvent
from .repository import MemoryRepository


class MemoryManager:
    def __init__(self, repository: MemoryRepository, retrieval_top_k: int = 5):
        self.repository = repository
        self.repository.initialize()
        self.retrieval_top_k = max(1, retrieval_top_k)
        self.session_id = str(uuid4())
        self.session_events: list[MemoryEvent] = []

    def remember(self, kind: str, content: str, metadata: dict[str, object] | None = None) -> int:
        metadata = metadata or {}
        event_id = self.repository.add_event(
            session_id=self.session_id,
            kind=kind,
            content=content,
            metadata=metadata,
        )
        event = MemoryEvent(
            id=event_id,
            session_id=self.session_id,
            kind=kind,
            content=content,
            metadata=metadata,
            created_at="",
        )
        self.session_events.insert(0, event)
        return event_id

    def set_preference(self, key: str, value: str) -> None:
        self.repository.set_preference(key, value)

    def get_preference(self, key: str, default: str | None = None) -> str | None:
        value = self.repository.get_preference(key)
        return value if value is not None else default

    def retrieve_relevant_facts(self, query: str, top_k: int | None = None) -> list[str]:
        limit = top_k if top_k is not None else self.retrieval_top_k
        persistent = self.repository.search_relevant_events(query=query, top_k=max(1, limit))

        session_matches = [
            event.content
            for event in self.session_events
            if any(token in event.content.lower() for token in query.lower().split() if len(token) >= 3)
        ]

        merged: list[str] = []
        seen: set[str] = set()

        for item in session_matches + [event.content for event in persistent]:
            normalized = item.strip()
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            merged.append(normalized)
            if len(merged) >= max(1, limit):
                break

        return merged

    def build_memory_context(self, query: str, top_k: int | None = None) -> str:
        facts = self.retrieve_relevant_facts(query=query, top_k=top_k)
        if not facts:
            return ""
        lines = [f"- {fact}" for fact in facts]
        return "\n".join(lines)

    def augment_goal_with_memory(self, goal: str, top_k: int | None = None) -> str:
        context = self.build_memory_context(goal, top_k=top_k)
        if not context:
            return goal
        return f"{goal}\n\nRelevant Memory:\n{context}"

    def save_execution_state(self, plan_id: str, state_payload: dict[str, object]) -> None:
        self.repository.save_execution_snapshot(plan_id, json.dumps(state_payload, ensure_ascii=False))

    def load_execution_state(self, plan_id: str) -> dict[str, object] | None:
        raw = self.repository.load_execution_snapshot(plan_id)
        if not raw:
            return None
        try:
            return json.loads(raw)
        except Exception:
            return None
