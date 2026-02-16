from __future__ import annotations

from ultragravity.actions import RiskLevel

from .base import ToolCapability, ToolExecutionResult


class SkillAdapter:
    name = "skill"

    def __init__(self, skills: list):
        self.skills = {skill.name: skill for skill in skills}

    def capabilities(self) -> dict[str, ToolCapability]:
        return {
            "execute": ToolCapability("execute", RiskLevel.R2, False, "Execute named skill"),
        }

    def execute(self, operation: str, params: dict[str, object]) -> ToolExecutionResult:
        if operation != "execute":
            return ToolExecutionResult(success=False, error=f"Unsupported operation: {operation}")

        skill_name = str(params.get("skill", ""))
        instruction = str(params.get("instruction", ""))

        if not skill_name:
            return ToolExecutionResult(success=False, error="Missing skill name")

        skill = self.skills.get(skill_name)
        if skill is None:
            return ToolExecutionResult(success=False, error=f"Unknown skill: {skill_name}")

        result = skill.execute({"instruction": instruction})
        if isinstance(result, dict) and result.get("status") == "success":
            return ToolExecutionResult(success=True, payload=result)
        return ToolExecutionResult(success=False, payload=result if isinstance(result, dict) else {}, error=str(result.get("reason", "Skill failed")) if isinstance(result, dict) else "Skill failed")
