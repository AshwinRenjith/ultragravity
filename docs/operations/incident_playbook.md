# Incident Playbook (Phase 10)

## Purpose
Standardize incident response for Ultragravity local deployments with strict safety, auditability, and rapid recovery.

## Severity levels
- **SEV-1**: Safety control bypass, destructive unintended action, or unrecoverable crash loop.
- **SEV-2**: Major degradation (frequent action failures, scheduler starvation, widespread denials from policy misconfig).
- **SEV-3**: Non-critical defects with workaround.

## Immediate triage (first 10 minutes)
1. Freeze active risky operations: set profile to strict.
   - `ultragravity policy --set strict`
2. Capture current runtime state.
   - `ultragravity status`
3. Capture latest logs.
   - `ultragravity logs --kind all --lines 200 > incident.log`
4. If action safety is suspect, terminate active session and preserve logs.

## Core diagnostics
- Audit stream: `logs/audit/actions-*.jsonl`
- Telemetry stream: `logs/telemetry/provider-*.jsonl`
- Runtime state: `logs/runtime/status.json`
- Setup state: `data/setup_state.json`
- Memory DB: configured by `memory.sqlite_path`

## Failure mode guidance
### 1) Repeated provider rate limits / quota pressure
- Confirm soft-cap thresholds in `ultragravity.config.yaml`.
- Validate scheduler retries are active.
- Reduce task concurrency and step frequency.
- Re-run soak benchmark locally before resuming sustained operation.

### 2) Permission storm (too many prompts) or unexpected denies
- Verify policy profile in memory via `ultragravity policy`.
- Review `permission_outcome` audit events for scope mismatch.
- Validate risk classification for high-frequency operations.

### 3) Planner abort loops
- Inspect execution recovery context from logs.
- Verify deterministic router + call-reduction caches are not stale.
- Re-run regression suite (`pytest -q tests/unit tests/integration tests/e2e`).

### 4) Adapter execution drift
- Check adapter-specific errors in audit logs.
- Validate tool registry entries and operation names.
- Run adapter tests (`tests/unit/test_phase8_adapters.py`).

## Communication template
- Incident ID:
- Detected at (UTC):
- Severity:
- Affected workflows:
- Current policy profile:
- Initial hypothesis:
- Mitigation applied:
- Next update ETA:

## Exit criteria
- Root cause identified and documented.
- Regression and reliability tests pass.
- Mitigation validated and released with rollback path.
- Incident note appended to release notes.
