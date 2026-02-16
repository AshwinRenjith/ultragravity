# Phase 4 Implementation — Call Reduction Engine (Cost & Rate Optimization)

Date: 2026-02-16

## Objective
Reduce unnecessary multimodal/provider calls by introducing state-change gating, deterministic routing shortcuts, and multi-layer caches.

## What was implemented

## 1) State-change detector
- Added perceptual image hashing (`dHash`) and Hamming-distance thresholding.
- Combined image signal + URL signal + external state signal into a unified `StateSnapshot`.
- Provides cheap change/no-change decision before expensive provider calls.

File:
- `ultragravity/call_reduction.py` (`StateChangeDetector`, `StateSnapshot`)

## 2) Deterministic-first router
- Added deterministic router executed before multimodal escalation.
- Current conservative shortcuts:
  - explicit wait intent
  - unchanged-state after recent interactive action (`click/type/scroll`) -> `wait`

File:
- `ultragravity/call_reduction.py` (`DeterministicRouter`)

## 3) Multi-layer caches
- Added generic TTL cache for bounded in-memory caching.
- Added cache key builders:
  - vision decision cache key
  - summary cache key
  - tool outcome cache key

File:
- `ultragravity/call_reduction.py` (`TTLCache` + key builders)

## 4) Vision pipeline integration
- `VisionAgent.analyze_image(...)` now:
  1. computes state snapshot
  2. runs deterministic router (optional)
  3. checks vision decision cache
  4. calls provider scheduler only if needed
- `VisionAgent.summarize_content(...)` now uses summary cache before provider calls.
- Added Phase-4 reduction counters:
  - `vision_cache_hits`
  - `summary_cache_hits`
  - `deterministic_shortcuts`
  - `state_unchanged_shortcuts`

File:
- `agent/vision.py`

## 5) Core runtime integration
- Passed mode/URL/state-change signals from agent loop to vision analysis.
- Added read-only tool outcome cache for low-risk skill outputs (`R0`), currently applied to extraction-style fast-paths.

File:
- `agent/core.py`

## 6) Config and exports
- Added configurable call-reduction section:
  - enable toggle
  - state change threshold
  - deterministic router toggle
  - per-cache TTL and max entry limits

Files:
- `ultragravity/config.py`
- `ultragravity.config.yaml`
- `ultragravity/__init__.py`

## Exit criteria status
- [x] State-change detector implemented
- [x] Deterministic-first routing implemented
- [x] Vision decision cache implemented
- [x] Summary cache implemented
- [x] Tool outcome cache implemented
- [x] Runtime integrated and configurable

## Notes
- This phase reduces calls without weakening safety controls from Phase 2.
- Phase 5 can now optimize prompt payloads and summarization quality/token shape on top of this reduced-call baseline.
