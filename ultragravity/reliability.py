from __future__ import annotations

import random
from contextlib import redirect_stdout
from dataclasses import dataclass
from io import StringIO
from statistics import mean
from time import perf_counter

from .actions import Action, RiskLevel
from .audit import AuditLogger
from .budget import BudgetManager, ProviderBudgetLimits
from .gateway import ActionGateway
from .permissions import PermissionBroker
from .policy import PolicyEngine, PolicyProfile
from .scheduler import ProviderCallRequest, ProviderScheduler
from .telemetry import ProviderTelemetry


@dataclass(frozen=True)
class ReliabilitySnapshot:
    total_requests: int
    successful_requests: int
    failed_requests: int
    hard_failures: int
    retries_triggered: int
    success_rate: float
    avg_latency_ms: float


@dataclass(frozen=True)
class GatewaySnapshot:
    total_actions: int
    allowed: int
    denied: int
    executed: int


@dataclass(frozen=True)
class Phase10BenchmarkResult:
    scheduler: ReliabilitySnapshot
    gateway: GatewaySnapshot


def _build_scheduler(log_dir: str, clock_start: float = 1000.0) -> tuple[ProviderScheduler, list[float]]:
    now = [clock_start]
    sleep_calls: list[float] = []

    def fake_sleep(seconds: float) -> None:
        bounded = max(0.0, float(seconds))
        sleep_calls.append(bounded)
        now[0] += bounded

    budget = BudgetManager(
        limits_by_provider={
            "gemini": ProviderBudgetLimits(
                rpm_limit=30,
                tpm_limit=40000,
                daily_request_limit=2000,
                soft_cap_ratio=0.8,
            )
        },
        clock=lambda: now[0],
    )
    telemetry = ProviderTelemetry(log_dir=log_dir)
    scheduler = ProviderScheduler(budget_manager=budget, telemetry=telemetry, sleep_fn=fake_sleep)
    return scheduler, now


def run_scheduler_soak(
    iterations: int = 200,
    rate_limit_frequency: int = 20,
    transient_failure_frequency: int = 33,
    seed: int = 42,
    log_dir: str = "logs/telemetry",
) -> ReliabilitySnapshot:
    random.seed(seed)

    scheduler, _ = _build_scheduler(log_dir=log_dir)
    successful = 0
    failed = 0
    hard_failures = 0
    retries_triggered = 0
    latencies_ms: list[float] = []

    for index in range(1, iterations + 1):
        call_attempts = {"count": 0}

        def flaky_call() -> dict[str, object]:
            call_attempts["count"] += 1

            if call_attempts["count"] == 1 and index % rate_limit_frequency == 0:
                raise RuntimeError("429 rate limit")

            if call_attempts["count"] == 1 and index % transient_failure_frequency == 0:
                raise RuntimeError("temporary upstream failure")

            return {
                "id": index,
                "tokens": 120,
            }

        request = ProviderCallRequest(
            provider="gemini",
            model="gemini-2.5-flash",
            operation="phase10_soak",
            estimated_tokens=120,
            call=flaky_call,
            max_retries=3,
            base_backoff_seconds=0.05,
            max_backoff_seconds=0.2,
            jitter_seconds=0.0,
        )

        started = perf_counter()
        result = scheduler.execute(request)
        elapsed_ms = (perf_counter() - started) * 1000.0
        latencies_ms.append(elapsed_ms)

        if call_attempts["count"] > 1:
            retries_triggered += 1

        if result.success:
            successful += 1
        else:
            failed += 1
            if call_attempts["count"] >= request.max_retries:
                hard_failures += 1

    success_rate = (successful / iterations) if iterations else 0.0

    return ReliabilitySnapshot(
        total_requests=iterations,
        successful_requests=successful,
        failed_requests=failed,
        hard_failures=hard_failures,
        retries_triggered=retries_triggered,
        success_rate=success_rate,
        avg_latency_ms=mean(latencies_ms) if latencies_ms else 0.0,
    )


def run_gateway_reliability(
    actions: int = 120,
    deny_every: int = 10,
    log_dir: str = "logs/audit",
) -> GatewaySnapshot:
    approvals = {"count": 0}

    def input_func(_prompt: str) -> str:
        approvals["count"] += 1
        if approvals["count"] % deny_every == 0:
            return "3"
        return "1"

    gateway = ActionGateway(
        policy_engine=PolicyEngine(PolicyProfile.STRICT),
        permission_broker=PermissionBroker(input_func=input_func),
        audit_logger=AuditLogger(log_dir=log_dir),
    )

    allowed = 0
    denied = 0
    executed = 0

    for index in range(actions):
        action = Action(
            tool_name="terminal",
            operation="shell_command",
            params={"command": f"echo action-{index}"},
            risk_level=RiskLevel.R2,
            scope=["phase10", "reliability"],
            reversible=True,
            reason="Phase 10 reliability run",
        )

        with redirect_stdout(StringIO()):
            result = gateway.execute(action, lambda: "ok")
        if result.allowed:
            allowed += 1
        else:
            denied += 1
        if result.executed:
            executed += 1

    return GatewaySnapshot(
        total_actions=actions,
        allowed=allowed,
        denied=denied,
        executed=executed,
    )


def run_phase10_benchmark(
    soak_iterations: int = 200,
    gateway_actions: int = 120,
    telemetry_log_dir: str = "logs/telemetry",
    audit_log_dir: str = "logs/audit",
) -> Phase10BenchmarkResult:
    scheduler_snapshot = run_scheduler_soak(
        iterations=soak_iterations,
        log_dir=telemetry_log_dir,
    )
    gateway_snapshot = run_gateway_reliability(
        actions=gateway_actions,
        log_dir=audit_log_dir,
    )
    return Phase10BenchmarkResult(
        scheduler=scheduler_snapshot,
        gateway=gateway_snapshot,
    )
