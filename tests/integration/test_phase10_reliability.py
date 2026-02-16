from ultragravity.reliability import run_gateway_reliability, run_scheduler_soak


def test_scheduler_soak_recovers_from_injected_failures(tmp_path):
    snapshot = run_scheduler_soak(
        iterations=180,
        rate_limit_frequency=15,
        transient_failure_frequency=22,
        seed=7,
        log_dir=str(tmp_path / "telemetry"),
    )

    assert snapshot.total_requests == 180
    assert snapshot.successful_requests == 180
    assert snapshot.failed_requests == 0
    assert snapshot.hard_failures == 0
    assert snapshot.retries_triggered > 0
    assert snapshot.success_rate == 1.0


def test_gateway_reliability_tracks_denials_and_execution(tmp_path):
    snapshot = run_gateway_reliability(
        actions=90,
        deny_every=9,
        log_dir=str(tmp_path / "audit"),
    )

    assert snapshot.total_actions == 90
    assert snapshot.denied > 0
    assert snapshot.allowed + snapshot.denied == snapshot.total_actions
    assert snapshot.executed == snapshot.allowed


def test_scheduler_soak_free_tier_safe_bounds(tmp_path):
    snapshot = run_scheduler_soak(
        iterations=120,
        rate_limit_frequency=12,
        transient_failure_frequency=17,
        seed=99,
        log_dir=str(tmp_path / "telemetry2"),
    )

    assert snapshot.total_requests <= 500
    assert snapshot.success_rate >= 0.99
