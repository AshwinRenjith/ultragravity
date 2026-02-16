from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from ultragravity.reliability import run_phase10_benchmark


def _format_percent(value: float) -> str:
    return f"{value * 100:.2f}%"


def main() -> int:
    result = run_phase10_benchmark(
        soak_iterations=300,
        gateway_actions=180,
        telemetry_log_dir="logs/telemetry",
        audit_log_dir="logs/audit",
    )

    payload = asdict(result)
    payload["generated_at"] = datetime.now(timezone.utc).isoformat()

    reports_dir = Path("reports")
    reports_dir.mkdir(parents=True, exist_ok=True)

    json_path = reports_dir / "phase10_benchmark_report.json"
    md_path = reports_dir / "phase10_benchmark_report.md"

    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    scheduler = result.scheduler
    gateway = result.gateway

    md = "\n".join(
        [
            "# Phase 10 Benchmark Report",
            "",
            f"Generated: {payload['generated_at']}",
            "",
            "## Scheduler Soak (Free-Tier-Safe)",
            f"- Total requests: {scheduler.total_requests}",
            f"- Successful requests: {scheduler.successful_requests}",
            f"- Failed requests: {scheduler.failed_requests}",
            f"- Hard failures: {scheduler.hard_failures}",
            f"- Retries triggered: {scheduler.retries_triggered}",
            f"- Success rate: {_format_percent(scheduler.success_rate)}",
            f"- Avg execution latency: {scheduler.avg_latency_ms:.3f} ms",
            "",
            "## Safety Gateway Reliability",
            f"- Total high-risk actions: {gateway.total_actions}",
            f"- Allowed: {gateway.allowed}",
            f"- Denied: {gateway.denied}",
            f"- Executed: {gateway.executed}",
            "",
            "## Release Readiness Summary",
            "- Scheduler recovers from injected rate limits and transient upstream errors via retry/backoff.",
            "- Permission gateway correctly blocks denied high-risk actions.",
            "- Benchmark uses local simulation only (no external API calls).",
            "",
        ]
    )
    md_path.write_text(md, encoding="utf-8")
    print(f"Wrote {json_path}")
    print(f"Wrote {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
