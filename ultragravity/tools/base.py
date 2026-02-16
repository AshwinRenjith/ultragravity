from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from ultragravity.actions import RiskLevel


@dataclass(frozen=True)
class ToolCapability:
    operation: str
    risk_level: RiskLevel
    reversible: bool
    description: str


@dataclass(frozen=True)
class ToolExecutionResult:
    success: bool
    payload: dict[str, Any] = field(default_factory=dict)
    error: str = ""


class ToolAdapter(Protocol):
    name: str

    def capabilities(self) -> dict[str, ToolCapability]:
        ...

    def execute(self, operation: str, params: dict[str, Any]) -> ToolExecutionResult:
        ...
