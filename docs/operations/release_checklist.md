# Release Checklist (Phase 10)

## Build & packaging
- [x] `pip install -r requirements.txt -c constraints.txt`
- [x] `pip install -r requirements-dev.txt -c constraints.txt`
- [x] `pip install -e .`
- [x] `python -m ultragravity.cli --help`

## Regression quality gates
- [x] `pytest -q tests/unit`
- [x] `pytest -q tests/integration`
- [x] `pytest -q tests/e2e`
- [x] Full run: `pytest -q tests/unit tests/integration tests/e2e`

## Reliability benchmark gates
- [x] `PYTHONPATH=. python scripts/benchmark_phase10.py`
- [x] Confirm `reports/phase10_benchmark_report.md` generated
- [x] Confirm scheduler hard failures are near zero
- [x] Confirm permission denials are explicit and audited

## Safety & security review
- [x] Verify strict policy remains default
- [x] Review denied action patterns in audit logs
- [x] Confirm no secrets in tracked files
- [x] Confirm filesystem sandbox protections active

## Operational readiness
- [x] Incident playbook reviewed
- [x] Rollback procedures reviewed and tested
- [ ] On-call owner identified for first release window

## Release approval
- [x] Benchmark and regression evidence attached
- [x] Known limitations documented
- [x] Go/No-Go decision recorded

## Execution notes (2026-02-16)
- Checklist was executed end-to-end in Python 3.11 release environment (`.venv311_release`) due upstream package build incompatibility on Python 3.14 (`pydantic-core`/PyO3 max support 3.13).
- Evidence artifacts:
	- `reports/phase10_benchmark_report.md`
	- `reports/phase10_benchmark_report.json`
	- `reports/release_signoff_phase10.md`
