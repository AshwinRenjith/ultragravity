from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


class RiskLevel(str, Enum):
    R0 = "R0"
    R1 = "R1"
    R2 = "R2"
    R3 = "R3"


class Action(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action_id: str = Field(default_factory=lambda: str(uuid4()))
    tool_name: str
    operation: str
    params: dict[str, Any] = Field(default_factory=dict)
    risk_level: RiskLevel
    scope: list[str] = Field(default_factory=list)
    reversible: bool = False
    reason: str = ""
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class PolicyDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    allow: bool = True
    require_prompt: bool = False
    reason: str = ""


class PermissionOutcome(BaseModel):
    model_config = ConfigDict(extra="forbid")

    approved: bool
    abort_requested: bool = False
    grant_scope: str = "once"
    reason: str = ""


class GatewayExecutionResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    allowed: bool
    executed: bool = False
    aborted: bool = False
    result: Any = None
    error: str | None = None


def action_signature(action: Action) -> str:
    scope = "|".join(sorted(action.scope))
    return f"{action.tool_name}:{action.operation}:{action.risk_level}:{scope}"
