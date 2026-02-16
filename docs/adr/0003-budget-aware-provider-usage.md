# ADR 0003: Budget-Aware Provider Usage

- Status: Accepted
- Date: 2026-02-16

## Context
Ultragravity relies on external LLM providers (Gemini/Mistral) with rate and quota limits, especially restrictive on free tiers.

## Decision
Adopt budget-aware provider architecture:
- All provider calls are metered and centrally budget-gated.
- Admission control prevents burst overrun.
- Deterministic-first routing and caching reduce unnecessary calls.
- Graceful degradation keeps system functional under throttling.

## Consequences
- Higher reliability and lower token cost.
- Additional infrastructure required (telemetry, scheduler, budgets).
- Better predictability for free-tier operation.

## Alternatives considered
- Retry-only strategy with provider fallback.
- Static delays without budget accounting.

Rejected due to continued burst risk and poor cost control.
