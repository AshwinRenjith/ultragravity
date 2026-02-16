from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable


@dataclass(frozen=True)
class ProviderBudgetLimits:
    rpm_limit: int
    tpm_limit: int
    daily_request_limit: int
    soft_cap_ratio: float = 0.6


@dataclass(frozen=True)
class BudgetDecision:
    allowed: bool
    reason: str
    retry_after_seconds: float = 0.0


class BudgetManager:
    def __init__(
        self,
        limits_by_provider: dict[str, ProviderBudgetLimits],
        clock: Callable[[], float],
    ):
        self._limits_by_provider = limits_by_provider
        self._clock = clock
        self._requests_by_provider: dict[str, deque[tuple[float, int]]] = {
            provider: deque() for provider in limits_by_provider
        }
        self._daily_counts: dict[str, dict[str, int]] = {
            provider: {} for provider in limits_by_provider
        }

    def _current_day(self) -> str:
        return datetime.fromtimestamp(self._clock(), tz=timezone.utc).strftime("%Y-%m-%d")

    def _prune_window(self, provider: str) -> None:
        now = self._clock()
        window = self._requests_by_provider[provider]
        while window and now - window[0][0] >= 60.0:
            window.popleft()

    def _remaining_daily(self, provider: str) -> int:
        day = self._current_day()
        used = self._daily_counts[provider].get(day, 0)
        return max(self._limits_by_provider[provider].daily_request_limit - used, 0)

    def evaluate(self, provider: str, estimated_tokens: int) -> BudgetDecision:
        if provider not in self._limits_by_provider:
            return BudgetDecision(allowed=False, reason=f"Unknown provider: {provider}")

        self._prune_window(provider)
        now = self._clock()
        limits = self._limits_by_provider[provider]
        window = self._requests_by_provider[provider]

        soft_rpm = max(1, int(limits.rpm_limit * limits.soft_cap_ratio))
        soft_tpm = max(1, int(limits.tpm_limit * limits.soft_cap_ratio))

        request_count = len(window)
        token_count = sum(tokens for _, tokens in window)

        if self._remaining_daily(provider) <= 0:
            return BudgetDecision(allowed=False, reason="Daily request budget exhausted", retry_after_seconds=60.0)

        if request_count >= soft_rpm:
            oldest_ts = window[0][0] if window else now
            retry_after = max(0.1, 60.0 - (now - oldest_ts))
            return BudgetDecision(allowed=False, reason="Soft RPM cap reached", retry_after_seconds=retry_after)

        if token_count + estimated_tokens > soft_tpm:
            oldest_ts = window[0][0] if window else now
            retry_after = max(0.1, 60.0 - (now - oldest_ts))
            return BudgetDecision(allowed=False, reason="Soft TPM cap reached", retry_after_seconds=retry_after)

        return BudgetDecision(allowed=True, reason="Budget available", retry_after_seconds=0.0)

    def reserve(self, provider: str, estimated_tokens: int) -> None:
        if provider not in self._limits_by_provider:
            return
        now = self._clock()
        self._prune_window(provider)
        self._requests_by_provider[provider].append((now, max(1, estimated_tokens)))

        day = self._current_day()
        provider_daily = self._daily_counts[provider]
        provider_daily[day] = provider_daily.get(day, 0) + 1

        for stale_day in list(provider_daily.keys()):
            if stale_day != day:
                del provider_daily[stale_day]

    def provider_snapshot(self, provider: str) -> dict[str, int | float]:
        if provider not in self._limits_by_provider:
            return {}
        self._prune_window(provider)
        limits = self._limits_by_provider[provider]
        window = self._requests_by_provider[provider]
        current_rpm = len(window)
        current_tpm = sum(tokens for _, tokens in window)
        return {
            "rpm_current": current_rpm,
            "tpm_current": current_tpm,
            "rpm_soft_cap": int(limits.rpm_limit * limits.soft_cap_ratio),
            "tpm_soft_cap": int(limits.tpm_limit * limits.soft_cap_ratio),
            "daily_remaining": self._remaining_daily(provider),
        }
