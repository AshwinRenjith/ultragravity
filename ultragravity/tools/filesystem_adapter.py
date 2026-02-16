from __future__ import annotations

from pathlib import Path
from typing import Any

from ultragravity.actions import RiskLevel

from .base import ToolCapability, ToolExecutionResult


class FileSystemAdapter:
    name = "filesystem"

    def __init__(self, sandbox_root: str):
        self.sandbox_root = Path(sandbox_root).resolve()

    def capabilities(self) -> dict[str, ToolCapability]:
        return {
            "read": ToolCapability("read", RiskLevel.R0, True, "Read file inside sandbox"),
            "write": ToolCapability("write", RiskLevel.R2, False, "Write file inside sandbox"),
            "delete": ToolCapability("delete", RiskLevel.R3, False, "Delete file inside sandbox"),
            "list": ToolCapability("list", RiskLevel.R0, True, "List directory inside sandbox"),
        }

    def _resolve(self, relative_path: str) -> Path:
        path = (self.sandbox_root / relative_path).resolve()
        if not str(path).startswith(str(self.sandbox_root)):
            raise PermissionError("Path escapes sandbox root")
        return path

    def execute(self, operation: str, params: dict[str, Any]) -> ToolExecutionResult:
        try:
            rel_path = str(params.get("path", ""))
            target = self._resolve(rel_path) if rel_path else self.sandbox_root

            if operation == "read":
                if not target.is_file():
                    return ToolExecutionResult(success=False, error="File not found")
                return ToolExecutionResult(success=True, payload={"content": target.read_text(encoding="utf-8")})

            if operation == "write":
                content = str(params.get("content", ""))
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content, encoding="utf-8")
                return ToolExecutionResult(success=True, payload={"path": str(target)})

            if operation == "delete":
                if target.is_file():
                    target.unlink()
                    return ToolExecutionResult(success=True, payload={"deleted": str(target)})
                return ToolExecutionResult(success=False, error="Target file not found")

            if operation == "list":
                if not target.exists() or not target.is_dir():
                    return ToolExecutionResult(success=False, error="Directory not found")
                entries = sorted(child.name for child in target.iterdir())
                return ToolExecutionResult(success=True, payload={"entries": entries})

            return ToolExecutionResult(success=False, error=f"Unsupported operation: {operation}")
        except PermissionError as exc:
            return ToolExecutionResult(success=False, error=str(exc))
        except Exception as exc:
            return ToolExecutionResult(success=False, error=str(exc))
