from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class ProviderTelemetry:
    def __init__(self, log_dir: str | Path = "logs/telemetry"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self._stats: dict[str, dict[str, int | float]] = {}

    def _log_path(self) -> Path:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
        return self.log_dir / f"provider-{stamp}.jsonl"

    def _ensure_provider(self, provider: str) -> None:
        if provider not in self._stats:
            self._stats[provider] = {
                "requests": 0,
                "successes": 0,
                "failures": 0,
                "estimated_tokens": 0,
                "actual_tokens": 0,
                "latency_ms_total": 0,
            }

    def record(
        self,
        provider: str,
        model: str,
        operation: str,
        estimated_tokens: int,
        actual_tokens: int,
        latency_ms: int,
        success: bool,
        error: str | None = None,
    ) -> None:
        self._ensure_provider(provider)
        provider_stats = self._stats[provider]
        provider_stats["requests"] = int(provider_stats["requests"]) + 1
        provider_stats["estimated_tokens"] = int(provider_stats["estimated_tokens"]) + max(0, estimated_tokens)
        provider_stats["actual_tokens"] = int(provider_stats["actual_tokens"]) + max(0, actual_tokens)
        provider_stats["latency_ms_total"] = int(provider_stats["latency_ms_total"]) + max(0, latency_ms)

        if success:
            provider_stats["successes"] = int(provider_stats["successes"]) + 1
        else:
            provider_stats["failures"] = int(provider_stats["failures"]) + 1

        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "provider": provider,
            "model": model,
            "operation": operation,
            "estimated_tokens": estimated_tokens,
            "actual_tokens": actual_tokens,
            "latency_ms": latency_ms,
            "success": success,
            "error": error,
        }

        with self._log_path().open("a", encoding="utf-8") as output:
            output.write(json.dumps(payload, ensure_ascii=False) + "\n")

    def snapshot(self) -> dict[str, dict[str, int | float]]:
        response: dict[str, dict[str, int | float]] = {}
        for provider, stats in self._stats.items():
            requests = int(stats["requests"])
            latency_total = int(stats["latency_ms_total"])
            response[provider] = {
                **stats,
                "latency_ms_avg": (latency_total / requests) if requests else 0,
                "success_rate": (int(stats["successes"]) / requests) if requests else 0,
            }
        return response
