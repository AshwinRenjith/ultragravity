# Phase 1 Implementation Plan — Foundation Hardening & Security Hygiene

Date: 2026-02-16

## Objective
Stabilize runtime setup and eliminate baseline security/reproducibility risks before feature expansion.

## Strategy

### 1) Dependency normalization
- Deduplicate runtime dependencies.
- Separate runtime and development requirements.
- Introduce constraints baseline for reproducible installs.

### 2) Environment and secret hygiene
- Ensure `.env.example` contains placeholders only.
- Keep `.env` git-ignored.
- Add startup diagnostics to detect missing keys or placeholder secrets.

### 3) Config model introduction
- Add `ultragravity.config.yaml` as default runtime config.
- Add schema-validated loader (`pydantic`) to fail fast on invalid config.
- Expose CLI override `--config`.

### 4) Startup diagnostics
- Validate `.env` presence.
- Validate provider key availability.
- Provide clear warnings before runtime execution.

## Deliverables implemented
- `requirements.txt` normalized (deduped, bounded versions).
- `requirements-dev.txt` introduced.
- `constraints.txt` added for reproducibility baseline.
- `.env.example` replaced with placeholders and config path variable.
- `ultragravity/config.py` schema-validated config loader.
- `ultragravity/diagnostics.py` startup checks.
- `ultragravity.config.yaml` default runtime config file.
- `main.py` updated to load config and run diagnostics.
- `README.md` updated for hardened install and config workflow.

## Exit Criteria
- Fresh setup has deterministic dependency path.
- Secret templates are safe by default.
- Runtime config is validated before execution.
- Startup prints actionable diagnostics when baseline is unsafe.

## Phase 1 Done Checklist
- [x] Dependency dedupe completed
- [x] Runtime/dev requirements split
- [x] Reproducibility constraints file added
- [x] Safe `.env.example` placeholders
- [x] Config schema + loader wired
- [x] Startup diagnostics integrated
- [x] Docs updated
