# Phase 10 Benchmark Report

Generated: 2026-02-16T05:32:20.835092+00:00

## Scheduler Soak (Free-Tier-Safe)
- Total requests: 300
- Successful requests: 300
- Failed requests: 0
- Hard failures: 0
- Retries triggered: 24
- Success rate: 100.00%
- Avg execution latency: 0.307 ms

## Safety Gateway Reliability
- Total high-risk actions: 180
- Allowed: 162
- Denied: 18
- Executed: 162

## Release Readiness Summary
- Scheduler recovers from injected rate limits and transient upstream errors via retry/backoff.
- Permission gateway correctly blocks denied high-risk actions.
- Benchmark uses local simulation only (no external API calls).
