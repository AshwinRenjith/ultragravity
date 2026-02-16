from __future__ import annotations

from typing import Any

from ultragravity.actions import RiskLevel

from .base import ToolCapability, ToolExecutionResult


class BrowserAdapter:
    name = "browser"

    def __init__(self, browser_agent):
        self.browser = browser_agent

    def capabilities(self) -> dict[str, ToolCapability]:
        return {
            "start": ToolCapability("start", RiskLevel.R1, True, "Start browser context"),
            "navigate": ToolCapability("navigate", RiskLevel.R1, True, "Navigate to URL"),
            "execute_action": ToolCapability("execute_action", RiskLevel.R1, False, "Execute browser action plan"),
            "screenshot": ToolCapability("screenshot", RiskLevel.R0, True, "Capture browser screenshot"),
        }

    def execute(self, operation: str, params: dict[str, Any]) -> ToolExecutionResult:
        if operation == "start":
            self.browser.start()
            return ToolExecutionResult(success=True)

        if operation == "navigate":
            url = str(params.get("url", ""))
            if not url:
                return ToolExecutionResult(success=False, error="Missing URL")
            self.browser.navigate(url)
            return ToolExecutionResult(success=True, payload={"url": url})

        if operation == "execute_action":
            action_plan = params.get("action_plan")
            if not isinstance(action_plan, dict):
                return ToolExecutionResult(success=False, error="Missing action_plan")

            action = str(action_plan.get("action", ""))
            target = action_plan.get("target_element", {}) if isinstance(action_plan.get("target_element"), dict) else {}
            coords = target.get("coordinates")

            if action in {"click", "type"} and (not isinstance(coords, list) or len(coords) < 2):
                return ToolExecutionResult(
                    success=True,
                    payload={
                        "fallback": "wait",
                        "reason": "Missing coordinates for interactive action",
                    },
                )

            self.browser.execute_action(action_plan)
            return ToolExecutionResult(success=True, payload={"action": action})

        if operation == "screenshot":
            path = str(params.get("path", "screenshot.png"))
            screenshot_path = self.browser.get_screenshot(path)
            return ToolExecutionResult(success=True, payload={"path": screenshot_path})

        return ToolExecutionResult(success=False, error=f"Unsupported operation: {operation}")
