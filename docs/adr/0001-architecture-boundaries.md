# ADR 0001: Core Architecture Boundaries

- Status: Accepted
- Date: 2026-02-16

## Context
Ultragravity includes browser automation, desktop control, AI planning, and skills. Without clear boundaries, cross-module coupling and hidden side effects become difficult to maintain.

## Decision
Adopt explicit architectural boundaries:
- Orchestration layer coordinates flow and state.
- Capability/tool layers execute isolated operations.
- AI/provider layers produce plans/analysis only.
- Safety/policy layer mediates high-impact actions.

## Consequences
- Better modularity and easier testing.
- Refactors become safer and localized.
- Requires discipline to avoid direct cross-layer shortcuts.

## Alternatives considered
- Monolithic loop with direct calls across modules.
- Per-feature architecture without global layering.

Both alternatives were rejected due to long-term maintainability and safety risks.
