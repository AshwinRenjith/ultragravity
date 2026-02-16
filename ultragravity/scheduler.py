from __future__ import annotations

import random
from collections import deque
from dataclasses import dataclass
from time import perf_counter
from typing import Any, Callable

from .budget import BudgetManager
from .telemetry import ProviderTelemetry


@dataclass(frozen=True)
class ProviderCallRequest:
    provider: str
    model: str
    operation: str
    estimated_tokens: int
    call: Callable[[], Any]
    extract_actual_tokens: Callable[[Any], int | None] | None = None
    max_retries: int = 3
    base_backoff_seconds: float = 2.0
    max_backoff_seconds: float = 20.0
    jitter_seconds: float = 0.4


@dataclass(frozen=True)
class ProviderCallResult:
    success: bool
    result: Any = None
    error: str | None = None
    provider: str = ""
    model: str = ""


class ProviderScheduler:
    def __init__(
        self,
        budget_manager: BudgetManager,
        telemetry: ProviderTelemetry,
        sleep_fn: Callable[[float], None],
    ):
        self.budget_manager = budget_manager
        self.telemetry = telemetry
        self.sleep_fn = sleep_fn
        self.queue: deque[ProviderCallRequest] = deque()

    @staticmethod
    def _is_rate_limited(error_message: str) -> bool:
        lowered = error_message.lower()
        return "429" in lowered or "rate" in lowered and "limit" in lowered or "quota" in lowered

    def execute(self, request: ProviderCallRequest) -> ProviderCallResult:
        self.queue.append(request)
        active = self.queue.popleft()

        for attempt in range(active.max_retries):
            decision = self.budget_manager.evaluate(active.provider, active.estimated_tokens)
            if not decision.allowed:
                wait_time = max(0.1, decision.retry_after_seconds)
                self.sleep_fn(wait_time)
                continue

            self.budget_manager.reserve(active.provider, active.estimated_tokens)
            started = perf_counter()

            try:
                response = active.call()
                duration_ms = int((perf_counter() - started) * 1000)
                actual_tokens = active.estimated_tokens
                if active.extract_actual_tokens is not None:
                    extracted = active.extract_actual_tokens(response)
                    if extracted is not None and extracted > 0:
                        actual_tokens = extracted

                self.telemetry.record(
                    provider=active.provider,
                    model=active.model,
                    operation=active.operation,
                    estimated_tokens=active.estimated_tokens,
                    actual_tokens=actual_tokens,
                    latency_ms=duration_ms,
                    success=True,
                )
                return ProviderCallResult(
                    success=True,
                    result=response,
                    provider=active.provider,
                    model=active.model,
                )
            except Exception as exc:
                duration_ms = int((perf_counter() - started) * 1000)
                error_message = str(exc)
                self.telemetry.record(
                    provider=active.provider,
                    model=active.model,
                    operation=active.operation,
                    estimated_tokens=active.estimated_tokens,
                    actual_tokens=0,
                    latency_ms=duration_ms,
                    success=False,
                    error=error_message,
                )

                if attempt >= active.max_retries - 1:
                    return ProviderCallResult(
                        success=False,
                        error=error_message,
                        provider=active.provider,
                        model=active.model,
                    )

                backoff = min(active.max_backoff_seconds, active.base_backoff_seconds * (2 ** attempt))
                jitter = random.uniform(0, active.jitter_seconds)

                if self._is_rate_limited(error_message):
                    self.sleep_fn(backoff + jitter)
                else:
                    self.sleep_fn(min(1.0 + jitter, backoff))

        return ProviderCallResult(success=False, error="Provider scheduler exhausted retries", provider=active.provider, model=active.model)
