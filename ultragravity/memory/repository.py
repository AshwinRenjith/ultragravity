from __future__ import annotations

from typing import Protocol

from .models import MemoryEvent


class MemoryRepository(Protocol):
    def initialize(self) -> None:
        ...

    def add_event(self, session_id: str, kind: str, content: str, metadata: dict[str, object]) -> int:
        ...

    def list_recent_events(self, limit: int) -> list[MemoryEvent]:
        ...

    def search_relevant_events(self, query: str, top_k: int, candidate_limit: int = 200) -> list[MemoryEvent]:
        ...

    def set_preference(self, key: str, value: str) -> None:
        ...

    def get_preference(self, key: str) -> str | None:
        ...

    def save_execution_snapshot(self, plan_id: str, payload_json: str) -> None:
        ...

    def load_execution_snapshot(self, plan_id: str) -> str | None:
        ...
