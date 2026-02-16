from __future__ import annotations

from enum import Enum

from .actions import Action, PolicyDecision, RiskLevel


class PolicyProfile(str, Enum):
    STRICT = "strict"
    BALANCED = "balanced"
    DEVELOPER = "developer"


class PolicyEngine:
    def __init__(self, profile: PolicyProfile = PolicyProfile.STRICT):
        self.profile = profile

    def evaluate(self, action: Action) -> PolicyDecision:
        if self.profile == PolicyProfile.DEVELOPER:
            return PolicyDecision(allow=True, require_prompt=action.risk_level in {RiskLevel.R2, RiskLevel.R3}, reason="Developer profile")

        if self.profile == PolicyProfile.BALANCED:
            if action.risk_level == RiskLevel.R0:
                return PolicyDecision(allow=True, require_prompt=False, reason="Low-risk read-only action")
            if action.risk_level == RiskLevel.R1:
                return PolicyDecision(allow=True, require_prompt=True, reason="Balanced profile requires confirmation for R1+")
            return PolicyDecision(allow=True, require_prompt=True, reason="Balanced profile requires confirmation for R2/R3")

        if action.risk_level == RiskLevel.R0:
            return PolicyDecision(allow=True, require_prompt=False, reason="Strict profile auto-approves R0")

        return PolicyDecision(allow=True, require_prompt=True, reason="Strict profile requires explicit confirmation for R1+")
