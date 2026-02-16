from __future__ import annotations

from typing import Any

from ultragravity.actions import RiskLevel

from .base import ToolCapability, ToolExecutionResult


class DesktopAdapter:
    name = "desktop"

    def __init__(self, desktop_agent):
        self.desktop = desktop_agent

    def capabilities(self) -> dict[str, ToolCapability]:
        return {
            "execute_action": ToolCapability("execute_action", RiskLevel.R2, False, "Execute desktop action plan"),
            "screenshot": ToolCapability("screenshot", RiskLevel.R0, True, "Capture desktop screenshot"),
        }

    def execute(self, operation: str, params: dict[str, Any]) -> ToolExecutionResult:
        if operation == "execute_action":
            action_plan = params.get("action_plan")
            if not isinstance(action_plan, dict):
                return ToolExecutionResult(success=False, error="Missing action_plan")

            action = str(action_plan.get("action", ""))
            target = action_plan.get("target_element", {}) if isinstance(action_plan.get("target_element"), dict) else {}
            coords = target.get("coordinates")

            if action in {"click", "type"} and (not isinstance(coords, list) or len(coords) < 2):
                return ToolExecutionResult(success=False, error="Desktop action requires coordinates")

            self.desktop.execute_action(action_plan)
            return ToolExecutionResult(success=True, payload={"action": action})

        if operation == "screenshot":
            path = str(params.get("path", "desktop_screenshot.png"))
            screenshot_path = self.desktop.get_screenshot(path)
            return ToolExecutionResult(success=True, payload={"path": screenshot_path})

        return ToolExecutionResult(success=False, error=f"Unsupported operation: {operation}")
