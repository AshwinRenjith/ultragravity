from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class SessionPhase(str, Enum):
    IDLE = "idle"
    PLANNING = "planning"
    CHECKPOINT = "checkpoint"
    EXECUTING = "executing"
    RECOVERY = "recovery"
    COMPLETED = "completed"
    ABORTED = "aborted"


@dataclass
class SessionStateMachine:
    phase: SessionPhase = SessionPhase.IDLE

    def transition_to(self, phase: SessionPhase) -> None:
        self.phase = phase
