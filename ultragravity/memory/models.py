from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class MemoryEvent:
    id: int
    session_id: str
    kind: str
    content: str
    metadata: dict[str, Any]
    created_at: str


@dataclass(frozen=True)
class PreferenceEntry:
    key: str
    value: str
    updated_at: str


@dataclass(frozen=True)
class ExecutionSnapshot:
    plan_id: str
    payload_json: str
    updated_at: str
