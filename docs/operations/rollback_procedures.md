# Rollback Procedures (Phase 10)

## Objective
Provide a low-risk rollback path for reliability regressions without compromising safety controls.

## Preconditions
- Keep strict policy profile enabled during rollback.
- Preserve all logs before any file change.

## Step-by-step rollback
1. Snapshot diagnostics:
   - `ultragravity status`
   - `ultragravity logs --kind all --lines 500 > rollback-precheck.log`
2. Backup mutable runtime data:
   - `data/setup_state.json`
   - memory database from `memory.sqlite_path`
   - `logs/` directory
3. Revert to previous known-good source revision.
4. Reinstall dependencies and package:
   - `pip install -r requirements.txt -c constraints.txt`
   - `pip install -e .`
5. Run minimum rollback verification:
   - `pytest -q tests/unit`
   - `python -m ultragravity.cli --help`
6. Run high-priority operational checks:
   - `ultragravity policy`
   - `ultragravity status`
7. Resume with strict profile and monitor audit/telemetry closely for first session.

## Data consistency notes
- Memory schema is append-oriented; rollback should not mutate prior events.
- If schema mismatch occurs, restore backed-up DB and rerun migration-compatible version.

## Abort rollback if
- Safety gateway tests fail.
- Policy profile cannot be resolved.
- CLI command surface is broken.

## Roll-forward criteria
- Root cause fixed.
- Regression + reliability benchmark pass.
- Updated phase report and checklist approved.
