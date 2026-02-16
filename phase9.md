# Phase 9 Implementation — Productization & Terminal UX

Date: 2026-02-16

## Objective
Ship an operator-friendly local product with a robust CLI, guided first-run setup, and actionable runtime observability.

## Implemented

### 1) Installable CLI command (`ultragravity`)
- Added packaging entrypoint to expose `ultragravity` command.
- Added module execution support (`python -m ultragravity`).

Files:
- `pyproject.toml`
- `ultragravity/__main__.py`
- `ultragravity/cli.py`

### 2) CLI command surface
Implemented required commands:
- `run`
- `ask`
- `policy`
- `logs`
- `status`

Command behavior:
- `run` / `ask`: launch runtime with config + diagnostics + runtime state tracking.
- `policy`: read/update persisted policy preference (`strict`, `balanced`, `developer`).
- `logs`: tail audit/telemetry logs from local JSONL files.
- `status`: report runtime state, mode, queue depth, provider usage snapshot, approval counts.

Files:
- `ultragravity/cli.py`

### 3) First-run setup wizard
Implemented wizard flow triggered automatically on first run (or explicitly via `--wizard`):
- Ensures `.env` exists (from `.env.example` if present)
- Prompts for provider keys (optional update)
- Displays macOS permissions checklist
- Persists default policy profile in memory
- Stores setup-completed marker in `data/setup_state.json`

File:
- `ultragravity/cli.py`

### 4) Runtime status UI foundation
Added runtime status persistence for operator visibility:
- `logs/runtime/status.json` maintained during run lifecycle
- `status` command reads runtime state + provider telemetry + approvals
- Includes budget soft-cap context from config and observed usage from logs

File:
- `ultragravity/cli.py`

### 5) Backward compatibility
Updated legacy `main.py` to delegate to the new CLI legacy path, preserving old invocation style.

File:
- `main.py`

### 6) Operator docs
Updated docs for:
- installable CLI setup
- first-run wizard
- command reference
- updated `run.sh` behavior

Files:
- `README.md`
- `run.sh`

## Quality Gate Mapping
- [x] New user can install command and run through guided setup
- [x] Operator has command-level controls for run/policy/logs/status
- [x] Runtime state and approvals are visible through terminal UX

## Notes
- Status queue depth currently reports local runtime queue state (`0` when idle) because scheduler queue is process-local.
- Existing safety gateway/policy/audit model remains the mandatory execution path for major actions.
