from __future__ import annotations

from typing import Any

from .base import ToolAdapter


class ToolRegistry:
    def __init__(self):
        self._adapters: dict[str, ToolAdapter] = {}

    def register(self, adapter: ToolAdapter) -> None:
        self._adapters[adapter.name] = adapter

    def get(self, name: str) -> ToolAdapter:
        adapter = self._adapters.get(name)
        if adapter is None:
            raise KeyError(f"Tool adapter not registered: {name}")
        return adapter

    def list_capabilities(self) -> dict[str, dict[str, Any]]:
        capabilities: dict[str, dict[str, Any]] = {}
        for name, adapter in self._adapters.items():
            capabilities[name] = {
                operation: {
                    "risk_level": capability.risk_level,
                    "reversible": capability.reversible,
                    "description": capability.description,
                }
                for operation, capability in adapter.capabilities().items()
            }
        return capabilities
