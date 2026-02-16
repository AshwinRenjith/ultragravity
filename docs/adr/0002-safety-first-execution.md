# ADR 0002: Safety-First Execution Model

- Status: Accepted
- Date: 2026-02-16

## Context
Ultragravity performs potentially impactful actions (desktop control, app launch, shell execution, file edits). Safety must be a first-class runtime concern.

## Decision
Adopt a mandatory safety-first model:
- Every major action must pass through centralized policy and permission checks.
- Risk taxonomy (`R0` to `R3`) classifies execution impact.
- High-risk actions require explicit user approval.
- Decision and execution events are audited.

## Consequences
- Stronger user trust and safer automation.
- More implementation work up front for gateway integration.
- Reduced chance of bypass behavior as system grows.

## Alternatives considered
- Best-effort prompts scattered across modules.
- Trust-by-default mode with optional confirmations.

Rejected because they cannot guarantee consistent safety behavior.
