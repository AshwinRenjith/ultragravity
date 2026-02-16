# Contributing to Ultragravity

## Engineering Principles
- Safety first: all high-impact behavior must be explicit, reviewable, and testable.
- Small, focused changes: avoid broad unrelated refactors in feature PRs.
- Deterministic behavior: prefer explicit contracts over implicit side effects.
- Observability by default: add logs/metrics when adding new control paths.

## Code Standards
- Use Python type hints for public interfaces and core logic.
- Keep modules cohesive and keep functions small when practical.
- Preserve existing style unless a scoped refactor is approved.
- Do not add secrets or machine-local artifacts.

## Testing Standards
- Add or update tests for all behavior changes.
- Prefer unit tests first, then integration tests for cross-module flows.
- Ensure new safety-critical logic includes failure-path coverage.

## Pull Request Checklist
- [ ] Change is scoped to one objective.
- [ ] Behavior changes are documented in PR description.
- [ ] Tests added/updated and passing locally.
- [ ] No secrets, generated binaries, or local artifacts included.
- [ ] Documentation updated (`README`, ADRs, or module docs) where relevant.

## Definition of Done (Feature Work)
A change is done only if:
1. Code is implemented and readable.
2. Tests pass for impacted logic.
3. Safety implications are documented.
4. Operational impact (logging/metrics/config) is addressed.
5. Reviewer can reproduce the feature/fix with provided steps.

## Architecture Decision Records (ADR)
- Add ADRs under `docs/adr/` for decisions with long-term architectural impact.
- Use incremental numbering (`0001`, `0002`, ...).
- Include context, decision, consequences, and alternatives.
