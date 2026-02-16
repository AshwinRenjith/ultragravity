from ultragravity.budget import BudgetManager, ProviderBudgetLimits
from ultragravity.scheduler import ProviderCallRequest, ProviderScheduler
from ultragravity.telemetry import ProviderTelemetry


def test_budget_blocks_when_soft_rpm_reached():
    now = [1000.0]

    manager = BudgetManager(
        limits_by_provider={
            "gemini": ProviderBudgetLimits(rpm_limit=2, tpm_limit=1000, daily_request_limit=10, soft_cap_ratio=0.5)
        },
        clock=lambda: now[0],
    )

    decision_before = manager.evaluate("gemini", estimated_tokens=50)
    assert decision_before.allowed is True

    manager.reserve("gemini", estimated_tokens=50)
    decision_after = manager.evaluate("gemini", estimated_tokens=50)

    assert decision_after.allowed is False
    assert "RPM" in decision_after.reason


def test_budget_blocks_when_soft_tpm_reached():
    now = [1000.0]

    manager = BudgetManager(
        limits_by_provider={
            "mistral": ProviderBudgetLimits(rpm_limit=10, tpm_limit=200, daily_request_limit=10, soft_cap_ratio=0.5)
        },
        clock=lambda: now[0],
    )

    manager.reserve("mistral", estimated_tokens=90)
    decision = manager.evaluate("mistral", estimated_tokens=20)

    assert decision.allowed is False
    assert "TPM" in decision.reason


def test_scheduler_retries_rate_limit_then_succeeds(tmp_path):
    now = [1000.0]
    sleep_calls = []
    attempts = {"count": 0}

    def fake_sleep(seconds: float):
        sleep_calls.append(seconds)
        now[0] += seconds

    manager = BudgetManager(
        limits_by_provider={
            "gemini": ProviderBudgetLimits(rpm_limit=20, tpm_limit=10000, daily_request_limit=100, soft_cap_ratio=1.0)
        },
        clock=lambda: now[0],
    )
    telemetry = ProviderTelemetry(log_dir=tmp_path / "telemetry")
    scheduler = ProviderScheduler(manager, telemetry, fake_sleep)

    def flaky_call():
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise RuntimeError("429 rate limit")
        return "ok"

    request = ProviderCallRequest(
        provider="gemini",
        model="gemini-2.5-flash",
        operation="analyze_image",
        estimated_tokens=120,
        call=flaky_call,
        max_retries=3,
        base_backoff_seconds=0.5,
        max_backoff_seconds=1.0,
        jitter_seconds=0.0,
    )

    result = scheduler.execute(request)
    snapshot = telemetry.snapshot()["gemini"]

    assert result.success is True
    assert attempts["count"] == 2
    assert len(sleep_calls) >= 1
    assert int(snapshot["requests"]) == 2
    assert int(snapshot["failures"]) == 1
    assert int(snapshot["successes"]) == 1


def test_scheduler_waits_for_budget_window_then_executes(tmp_path):
    now = [1000.0]
    sleep_calls = []

    def fake_sleep(seconds: float):
        sleep_calls.append(seconds)
        now[0] += seconds

    manager = BudgetManager(
        limits_by_provider={
            "mistral": ProviderBudgetLimits(rpm_limit=1, tpm_limit=10000, daily_request_limit=100, soft_cap_ratio=1.0)
        },
        clock=lambda: now[0],
    )

    manager.reserve("mistral", estimated_tokens=10)

    telemetry = ProviderTelemetry(log_dir=tmp_path / "telemetry")
    scheduler = ProviderScheduler(manager, telemetry, fake_sleep)

    request = ProviderCallRequest(
        provider="mistral",
        model="pixtral-12b-2409",
        operation="analyze_image",
        estimated_tokens=40,
        call=lambda: "ok-after-wait",
        max_retries=2,
        base_backoff_seconds=0.1,
        max_backoff_seconds=0.2,
        jitter_seconds=0.0,
    )

    result = scheduler.execute(request)

    assert result.success is True
    assert result.result == "ok-after-wait"
    assert len(sleep_calls) >= 1
    assert sum(sleep_calls) >= 59.0
