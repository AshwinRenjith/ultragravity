# Ultragravity Release Candidate (Phase 10)

Date: 2026-02-16

## Candidate summary
This release candidate completes Phases 0–10 with safety-first execution, budget-aware scheduling, planner/executor determinism, unified tool adapters, and productized CLI UX.

## Validation evidence
- Full regression suite: `37 passed`
- Benchmark report:
  - Scheduler soak requests: `300`
  - Success rate: `100.00%`
  - Hard failures: `0`
  - Gateway deny-path checks: `18` denied of `180` high-risk actions

Reference artifacts:
- `reports/phase10_benchmark_report.md`
- `reports/phase10_benchmark_report.json`

## Operational readiness
- Incident playbook: `docs/operations/incident_playbook.md`
- Rollback procedures: `docs/operations/rollback_procedures.md`
- Release checklist: `docs/operations/release_checklist.md`

## Release decision
Status: **Ready for controlled release window**

Conditions:
1. Keep default policy profile as `strict`.
2. Monitor audit and telemetry logs during initial sessions.
3. Use rollback procedures immediately on safety or reliability regressions.

## Known limitations
- Python 3.14 is not currently a valid release interpreter for this stack because `pydantic-core` build chain (PyO3) caps at Python 3.13; release validation and packaging are therefore executed on Python 3.11.
