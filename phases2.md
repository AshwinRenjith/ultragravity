# Phases 2: Ultragravity Development Phases (Execution Plan)

Date: 2026-02-16  
Workspace: ultragravity

This file converts `plan2.md` into a build-ready phase sequence focused on:
- Maximum implementation efficiency
- Highest code quality and maintainability
- Strong safety and reliability guarantees
- Refined final user experience

---

## Phase 0 — Program Setup & Engineering Standards

## Objective
Create a high-discipline engineering baseline so all later phases scale cleanly.

## Scope
- Define architecture decision records (ADRs) for safety, budgeting, and execution flow.
- Set coding standards, lint/test conventions, and module boundaries.
- Establish branch/PR checklist and Definition of Done template.

## Deliverables
- `docs/adr/` with initial ADRs.
- `CONTRIBUTING.md` with standards/checklist.
- Test structure finalized (`tests/unit`, `tests/integration`, `tests/e2e`).

## Quality gate
- Team can implement new modules with consistent structure and test conventions.

---

## Phase 1 — Foundation Hardening & Security Hygiene

## Objective
Stabilize environment and remove baseline risk before feature work.

## Scope
- Clean dependencies (dedupe, lock strategy, reproducible install).
- Harden `.gitignore`, `.env` usage, startup diagnostics.
- Introduce configuration model (`ultragravity.config.yaml`).

## Deliverables
- Reproducible local setup.
- Secure secret handling rules.
- Config loader with schema validation.

## Quality gate
- Fresh setup succeeds reliably; no secret leakage in tracked files.

---

## Phase 2 — Action Contract + Mandatory Safety Gateway (Critical)

## Objective
Guarantee every major operation is policy- and permission-mediated.

## Scope
- Define `Action` schema and risk taxonomy (`R0–R3`).
- Build `PermissionBroker` and policy engine (`strict` default).
- Implement non-bypassable `ActionGateway` pipeline.
- Add audit trail for decisions and executions.

## Deliverables
- `ultragravity/actions.py`, `permissions.py`, `policy.py`, `gateway.py`, `audit.py`.
- Approval prompts for all high-impact operations.

## Quality gate
- No major action executes without gateway decision; test-proven non-bypass.

---

## Phase 3 — Provider Observability + Budget Control (Rate-Limit Core)

## Objective
Prevent quota spikes by design and make API usage measurable.

## Scope
- Add provider telemetry wrapper (requests, tokens, latency, failures).
- Implement `BudgetManager` with hard admission control.
- Add scheduler queue and retry policy with jitter.

## Deliverables
- Metered Gemini/Mistral calls.
- Central budget status model and enforcement.

## Quality gate
- Every provider call is budget-gated and traceable.

---

## Phase 4 — Call Reduction Engine (Cost & Rate Optimization)

## Objective
Cut unnecessary multimodal calls and reduce token burn aggressively.

## Scope
- State-change detector (image hash + DOM/URL signals).
- Deterministic-first routing before multimodal escalation.
- Multi-layer caches (vision decision, summary, tool outcome).

## Deliverables
- Reduced call frequency in normal loops.
- Cache-backed reuse of prior decisions and summaries.

## Quality gate
- Measurable drop in calls/task and improved cache hit ratio.

---

## Phase 5 — Prompt/Context Optimization & Summarization Refactor

## Objective
Maximize output quality per token.

## Scope
- Compact prompt templates and strict output schemas.
- Token caps and debug-only verbose reasoning.
- Hierarchical summarization (chunk → local summaries → merge).

## Deliverables
- Prompt library and context shaper module.
- Efficient summarization pipeline.

## Quality gate
- Lower tokens/task without reduced task success quality.

---

## Phase 6 — Planner/Executor Separation with Checkpoints

## Objective
Move from loop-based behavior to explicit, controllable plan execution.

## Scope
- Build planner producing step graph with risk tags.
- Add checkpoint confirmations for high-risk branches.
- Add structured retries, fallback paths, and recovery states.

## Deliverables
- `planner.py`, `executor.py`, step-state machine.
- User-visible plan preview and checkpoint confirmations.

## Quality gate
- End-to-end flows are deterministic, inspectable, and resumable.

---

## Phase 7 — Memory System (Session + Persistent)

## Objective
Enable continuity while keeping context lean.

## Scope
- Session memory and persistent memory store (SQLite).
- Preference memory (policy profile, trusted scopes, interaction style).
- Retrieval strategy with top-k relevant facts only.

## Deliverables
- `ultragravity/memory/` package and schema migrations.
- Memory retrieval integrated into planning/context shaping.

## Quality gate
- Agent retains useful preferences/history across runs with controlled context size.

---

## Phase 8 — Tool Unification & Adapter Migration

## Objective
Standardize all capabilities under one tool interface and safety path.

## Scope
- Migrate `skills/` and legacy executors behind tool adapters.
- Add filesystem adapter with path sandbox.
- Harden desktop/browser adapters with fallback logic.

## Deliverables
- Unified tool registry with capability metadata and risk annotations.
- Legacy direct execution paths removed.

## Quality gate
- All tool calls follow same contract, policy, and audit flow.

---

## Phase 9 — Productization & Terminal UX

## Objective
Ship a robust operator-friendly local product.

## Scope
- Create installable CLI command (`ultragravity`).
- First-run setup wizard (keys, macOS permissions, profile selection).
- Runtime status UI (budget, queue, mode, approvals).

## Deliverables
- CLI commands: `run`, `ask`, `policy`, `logs`, `status`.
- User docs and quickstart for macOS.

## Quality gate
- New user can install, configure, and safely run in under 10 minutes.

---

## Phase 10 — Reliability Hardening, Benchmarks, and Release

## Objective
Refine to production-grade reliability and confidence.

## Scope
- Full regression suite (safety, budget, planner, adapters).
- Load/soak tests in free-tier-safe mode.
- Security and failure-mode review; finalize release checklist.

## Deliverables
- Release candidate with benchmark report.
- Incident playbook and rollback procedures.

## Quality gate
- Stable operation under constrained budgets with near-zero hard failures.

---

## Cross-Phase Quality Framework (applies to every phase)

## Engineering quality standards
- Type hints and strict schema validation for all boundaries.
- Small modules with explicit interfaces and low coupling.
- Backward-compatible refactors with deprecation path.

## Testing standards
- Unit tests for each new policy/logic unit.
- Integration tests for every critical execution path.
- Failure injection tests for provider throttling and denied permissions.

## Observability standards
- Structured logs with correlation IDs.
- Metrics for cost, latency, retries, cache hits, and denied actions.
- Audit events for each major decision and action.

## Documentation standards
- Every new module includes usage notes and contract docs.
- ADR updates when architecture decisions change.

---

## Suggested execution order for highest efficiency

1. Phase 0 → 1 (clean baseline)
2. Phase 2 (safety gateway first, non-negotiable)
3. Phase 3 → 4 → 5 (rate-limit and token system)
4. Phase 6 (planner/executor)
5. Phase 7 → 8 (memory + tool unification)
6. Phase 9 → 10 (productization + hardening)

This order minimizes rework because safety and budget controls become foundational constraints before advanced orchestration and UX layers.

---

## Milestone mapping

## Milestone M1 (Secure Core)
- Phases 0–2 complete.

## Milestone M2 (Budget-Safe Intelligence)
- Phases 3–5 complete.

## Milestone M3 (Autonomous Reliability)
- Phases 6–8 complete.

## Milestone M4 (Release-Ready Product)
- Phases 9–10 complete.

---

## Definition of “Perfectly Ready” for final outcome

- Every major action is permission-gated and auditable.
- Free-tier mode runs stably with strong quota resilience.
- Token efficiency is measured and continuously optimized.
- Planner/executor behavior is deterministic, resumable, and explainable.
- Tooling is unified, test-backed, and maintainable.
- CLI UX is polished and reliable for daily use on macOS.
