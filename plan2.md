# Plan 2: Build a Complete Local “Ultragravity” Assistant (Permission-First)

Date: 2026-02-16  
Workspace: ultragravity

## 1) Target state (what “complete Ultragravity” means for this project)

A local assistant that runs from terminal in your laptop root context, can orchestrate browser + desktop + system tasks, and **always asks permission before every major action**.

### Product goals
- Always-on local CLI assistant (`ultragravity`) launched from terminal.
- Can understand high-level goals and break them into executable steps.
- Supports browser actions, desktop app control, file operations, terminal commands, and summarization.
- Has memory (session + persistent) for context continuity.
- Has strict safety controls: permission prompts, allow/deny policies, audit logs, rollback where possible.
- Works reliably on macOS first (your environment), then extensible to Linux/Windows.

### Safety-first behavior (mandatory)
Before any major action, Ultragravity must ask:
- What action will run
- Why this action is needed
- Potential impact/risk
- Exact command/API call/path scope
- Await explicit user approval (`yes/no`) with optional “always allow this exact pattern for this session”.

Major actions include:
- Running shell commands
- Editing/deleting/creating files outside safe workspace scope
- Sending network requests to unknown domains
- Launching or controlling desktop applications
- Clipboard access, notifications, keyboard/mouse automation
- Any irreversible or high-impact operation

---

## 2) Current codebase analysis vs target

## Current strengths (already useful)
- Agent orchestration loop exists (`agent/core.py`) with observe → think → act.
- Vision planning exists with provider fallback (`agent/vision.py`: Gemini + Mistral).
- Browser automation exists (`agent/browser.py`: Playwright + stealth + humanized interactions).
- Desktop automation exists (`agent/desktop.py`: screenshots + mouse/typing execution).
- Skill architecture exists (`skills/base.py` and skill modules).
- AppleScript bridge exists for macOS app interactions (`agent/bridge_applescript.py`).
- CLI entrypoint exists (`main.py`) and script launcher (`run.sh`).

## Critical gaps to become a full local Ultragravity assistant
1. **No permission gateway**
   - Actions can execute directly without explicit per-action approvals.
2. **No policy engine**
   - No configurable allow/deny rules, trust scopes, risk categories.
3. **No robust planner/executor separation**
   - Current flow is loop-driven; needs explicit task graph, checkpoints, and approval boundaries.
4. **No persistent memory system**
   - `history` exists in memory only; no long-term profile/preferences/task context.
5. **No full system command framework with sandboxing**
   - Terminal execution helper exists but lacks hardened safe execution model.
6. **No standardized tool registry contract**
   - Skills exist, but not a unified tool capability manifest + risk metadata.
7. **No audit/event log model**
   - Need durable trace of decisions, prompts, actions, approvals, outputs, failures.
8. **No recovery/retry strategy layer**
   - Need structured error taxonomy and auto-recovery policy.
9. **No packaging/runtime profile for “run from terminal root” as product**
   - Needs installable CLI, config home, first-run setup, and daemon/session UX.
10. **Security hygiene gaps**
   - `.env` handling, secret management and command constraints need hardening.

---

## 3) Capability analysis: what I can build with you in this repo

## I can build directly
- End-to-end Python architecture in this repo (new modules, refactors, CLI flows).
- Permission middleware and policy/risk classification for every tool/action.
- Tool registry with metadata (risk level, scope, reversible flag, required approval).
- Persistent memory layer (SQLite + optional vector index).
- Structured planner/executor with approval checkpoints.
- Logging + audit trail + session replay.
- Mac-focused integrations (AppleScript, Playwright, pyautogui) with safer wrappers.
- Tests for policy, planner, permission prompts, and action adapters.

## Constraints to note
- True “always-listening” voice assistant requires additional audio stack and process management; feasible but separate phase.
- Some OS-level controls are permission-gated by macOS privacy settings (Accessibility, Screen Recording, Automation).
- Safety depends on local policy quality; we can strongly reduce risk but not guarantee zero-risk autonomy.

Conclusion: building a strong local terminal-first Ultragravity assistant in this codebase is feasible with staged implementation.

---

## 4) Proposed architecture for Ultragravity v1

## Core runtime modules (new)
- `ultragravity/cli.py` — command-line entry (`ultragravity run`, `ultragravity ask`, `ultragravity policy`, `ultragravity logs`).
- `ultragravity/session.py` — session lifecycle, context, checkpoints.
- `ultragravity/planner.py` — convert user goal into step plan with risk tags.
- `ultragravity/executor.py` — executes approved steps through tool adapters.
- `ultragravity/permissions.py` — interactive approval broker + cached session approvals.
- `ultragravity/policy.py` — allow/deny/risk rules (YAML/JSON policy files).
- `ultragravity/tools/` — unified adapters for browser, desktop, terminal, filesystem, web.
- `ultragravity/memory/` — short-term + long-term memory store (SQLite).
- `ultragravity/audit.py` — immutable action logs.
- `ultragravity/safety.py` — guards for path scope, command blacklist/allowlist, network domain controls.

## Existing modules to keep/reuse
- Reuse `agent/vision.py`, `agent/browser.py`, `agent/desktop.py`, selected skills.
- Wrap all existing actions through permission + policy middleware.

---

## 5) Build plan (phased roadmap)

## Phase 0 — Foundation hardening (1-2 days)
- Normalize dependencies and environment handling.
- Remove duplicate requirements and lock versions.
- Add secure defaults: `.gitignore`, `.env` safety checks, startup diagnostics.
- Define project configuration file (e.g., `ultragravity.config.yaml`).

**Exit criteria**
- Clean install + deterministic startup.
- No secrets in tracked files.

## Phase 1 — Permission-first action layer (2-4 days)
- Introduce `Action` schema: id, type, params, risk, reversible, scope.
- Build `PermissionBroker` to prompt before major actions.
- Add policy profiles: `strict`, `balanced`, `developer`.
- Enforce gating across terminal, filesystem, browser navigation, desktop control.

**Exit criteria**
- Every major action is blocked until explicit approval.
- Approval decision and rationale is logged.

## Phase 2 — Planner/Executor split (3-5 days)
- Implement goal decomposition into step plans.
- Add checkpoints where plan requests user confirmation before high-risk branches.
- Add retry/backoff/error classes and deterministic fallback order.

**Exit criteria**
- Ultragravity can present a plan, request approval, and execute step-by-step safely.

## Phase 3 — Memory + context continuity (2-4 days)
- Add session memory and persistent memory with TTL and pinning.
- Add user preferences memory (style, safe scopes, trusted apps/domains).
- Add memory retrieval to planning prompt.

**Exit criteria**
- Ultragravity remembers previous tasks/preferences across runs.

## Phase 4 — Tool unification + capability expansion (4-7 days)
- Convert existing `skills/` into standardized tool adapters.
- Add filesystem tool with path sandbox + confirm-on-write/delete.
- Add network/web fetch tool with domain permissions.
- Improve desktop action reliability with coordinate calibration and fallback selectors.

**Exit criteria**
- Unified tool contract with risk metadata and consistent execution semantics.

## Phase 5 — Productization (2-4 days)
- Create installable CLI (`pip install -e .` + entry point).
- Add first-run setup wizard (API keys, macOS permissions checks, policy mode).
- Add rich terminal UX: concise prompts, confirmations, action previews.

**Exit criteria**
- Launchable as `ultragravity` from terminal with clear setup and safe defaults.

## Phase 6 — Optional voice mode (later)
- Wake word / push-to-talk mode.
- Speech-to-text + text-to-speech pipeline.
- Voice-safe confirmation prompts for major actions.

---

## 6) Safety model design (detailed)

Each action gets a risk level:
- `R0`: read-only low risk (e.g., summarize visible page)
- `R1`: navigational/temporary changes (open URL/app)
- `R2`: local state change (create/edit files, type into apps)
- `R3`: high impact (delete files, execute shell, external side effects)

Permission defaults:
- `R0`: auto-allow (log only)
- `R1`: ask once per session per scope
- `R2`: always ask unless narrowly pre-approved
- `R3`: always ask with explicit confirmation phrase

Approval prompt template:
1. Step summary
2. Impact + scope
3. Exact operation preview
4. Options: `approve once`, `approve for session`, `deny`, `abort plan`

---

## 7) Suggested repository evolution

Potential structure:
- `ultragravity/` (new runtime package)
- `ultragravity/tools/` (tool adapters)
- `ultragravity/policies/` (default policy profiles)
- `ultragravity/prompts/` (planner/executor prompt templates)
- `tests/unit/` and `tests/integration/`
- Keep `agent/` as legacy modules gradually migrated behind adapters

---

## 8) Testing strategy required for trust

- Unit tests: policy evaluation, risk classification, permission broker, action schema validation.
- Integration tests: planner → permission → executor flow with mock tools.
- Safety tests: blocked dangerous commands, restricted path writes, denied domain access.
- Reliability tests: provider failures, retries, timeout handling, partial plan recovery.
- Manual acceptance tests on macOS privacy permissions and desktop automation stability.

---

## 9) Milestone roadmap (practical)

## MVP (safe terminal Ultragravity)
- Phase 0 + 1 + minimal phase 2
- Delivers permission-first terminal assistant with browser + terminal + basic filesystem tools.

## V1 (daily usable)
- Full phase 2 + 3 + 4
- Delivers memory, robust plans, broad toolset, stronger recovery.

## V2 (assistant personality + voice)
- Phase 5 + optional phase 6
- Delivers polished product and optional speech interface.

---

## 10) Immediate next implementation sequence (recommended)

1. Add `Action` model + risk taxonomy.
2. Build `PermissionBroker` and wire it in front of all existing skill executions.
3. Add policy file and strict default profile.
4. Refactor current loop to explicit plan/checkpoint/execute flow.
5. Add audit logging and tests for permission enforcement.
6. Package CLI commands (`ultragravity run`, `ultragravity policy`, `ultragravity logs`).

This sequence gives maximum safety earliest while preserving your existing strengths.

---

## Final assessment

You already have strong execution primitives (vision, browser, desktop, skills).  
To become a true local Ultragravity assistant, the main work is not raw automation; it is **permission architecture, policy control, planning discipline, and reliability layers**.  
This codebase is a solid base, and the target is realistic with a staged build.

---

## 11) Biggest current gap (deep analysis) and rectification plan

## The biggest gap
The largest blocker is the absence of a **single mandatory control plane** that all actions must pass through before execution.

Right now, actions can be triggered from multiple places:
- Skill fast-path execution in core loop
- Browser action execution
- Desktop action execution
- AppleScript bridge operations
- Terminal helper execution

Because these paths are not uniformly mediated by one policy/permission layer, safety behavior can become inconsistent. Even if one path is protected, another may still execute directly.

## Why this is the highest-priority risk
- Safety guarantees are only as strong as the weakest execution path.
- The product promise is explicit user approval before major actions.
- Without a unified gate, auditability and trust cannot be guaranteed.
- Future features (memory, autonomous planning, voice) amplify impact if this core remains unresolved.

## Rectification strategy: build a mandatory Action Gateway

### A. Introduce one action contract (foundation)
Create a typed Action model used everywhere:
- action_id
- tool_name
- operation
- params
- risk_level (R0-R3)
- scope (paths/domains/apps)
- reversible (true/false)
- reason

No adapter executes raw commands directly; all adapters receive validated Action objects.

### B. Enforce one execution pipeline (non-bypassable)
Execution order for every action:
1. Validate schema
2. Classify risk
3. Evaluate policy
4. Request permission if needed
5. Execute tool adapter
6. Record immutable audit event
7. Return result + postcondition status

If any step fails, execution halts.

### C. Add policy + approvals with strict defaults
- Default mode: strict
- R2 and R3 always require explicit approval
- Session-scoped approvals allowed only for exact signature/scope
- Denied actions are blocked and logged with reason

### D. Add anti-bypass controls
- Remove direct calls from skills/agents to raw tool methods
- Route all skill outputs to Action Gateway
- Add test that fails if prohibited direct execution methods are called

### E. Add proof through tests and telemetry
- Unit: risk classification, policy decisions, permission transitions
- Integration: planner/skill to gateway to adapter path
- Security: command/path/domain deny cases
- Audit integrity: each action has decision trail

## Delivery plan to close this gap

### Sprint 1 (2-3 days)
- Implement Action model + Gateway skeleton
- Add PermissionBroker with interactive prompt
- Wire terminal and filesystem actions first

Exit criteria:
- No terminal/file mutation runs without gateway decision

### Sprint 2 (2-3 days)
- Wire browser + desktop + AppleScript actions
- Add policy profiles and session approval cache
- Add complete audit log schema

Exit criteria:
- All major action types share same approval/policy path

### Sprint 3 (1-2 days)
- Remove bypass paths in skills/core
- Add regression tests for non-bypass guarantee
- Add startup safety self-check report

Exit criteria:
- Safety promise is enforceable and test-backed

## Feasibility assessment
Yes, this is fully feasible in this codebase. The current architecture already has centralized orchestration and modular tools; we need to make execution mediation explicit and mandatory. Once this gap is closed, the remaining roadmap items become much safer and easier to deliver.

---

## 12) Rate-limit and token-efficiency gap (deep analysis) and rectification plan

## Gap statement
Another major blocker is provider overuse behavior in the vision/summarization loop, which can trigger quota/rate-limit events on Gemini and Mistral, especially on free tiers.

Important reality: no external API can be guaranteed to never rate-limit under all conditions (provider-side changes/outages can still happen).  
What we can do is architect Ultragravity so that in normal operation it runs far below limits and degrades gracefully without hard failure.

## Root-cause analysis in current flow

1. High-frequency full-screen multimodal calls
- Repeated screenshot analysis sends large payloads frequently.
- Current loop can call vision every cycle even when screen state did not materially change.

2. No unified quota governor
- There is cooldown handling, but no global RPM/TPM budget manager with hard admission control.
- Retries may still consume burst budget when both providers are stressed.

3. Prompt/context payloads are larger than needed
- Full instruction + generic schema sent each time.
- Summarization path may pass large content chunks instead of hierarchical compression.

4. No strong dedupe/cache layer
- Similar screenshots and repeated goals are re-processed from scratch.
- No semantic memoization of prior action decisions.

5. No deterministic-first execution path
- Many decisions that can be handled by cheap local heuristics still escalate to LLM vision.

## Target outcome
- Operate with a strict budget model that keeps average usage below free-tier thresholds.
- Reduce token/image calls through local routing, caching, and state-change gating.
- Convert rate-limit events from hard failures into queued/deferred progress.
- Improve answer quality per token via prompt compaction and staged reasoning.

## Architecture to close the gap

### A. Global Budget Manager (mandatory)
Build a central `BudgetManager` that every provider call must request before execution.

Tracks by provider and model:
- Requests per minute (RPM)
- Tokens per minute (TPM) estimated + observed
- Daily request budget
- In-flight requests

Controls:
- Hard admission gate (reject/defer if budget unavailable)
- Sliding-window accounting
- Soft cap and hard cap thresholds
- Priority lanes (critical, normal, background)

Effect:
- Prevents bursty loops from exceeding budget by design.

### B. State-change gate before multimodal inference
Only call vision when screen meaningfully changed.

Use:
- Perceptual image hash diff (pHash/dHash)
- DOM/url change checks (browser mode)
- Time since last action and expected UI transition windows

If no meaningful change:
- Reuse previous decision
- Or run lightweight local wait/scroll logic

Effect:
- Removes redundant image calls.

### C. Deterministic-first router (LLM as escalation, not default)
Add local decision layers before provider call:
- Skill resolver and regex/intent parser
- Selector-based browser operations
- Rule-based desktop action patterns
- Local extraction where possible

Only escalate to multimodal when confidence is low.

Effect:
- Major reduction in paid/free-tier API dependency.

### D. Prompt compaction and context shaping
Adopt compact prompts with strict schemas and rolling context windows.

Techniques:
- Static system prompt cached in process
- Delta context only (what changed since last step)
- Short action schema and bounded reasoning field
- Remove repeated instruction boilerplate

For summarization:
- Hierarchical map-reduce summarization
- Chunk scoring + top-k relevance
- Progressive compression memory (briefs instead of raw text replay)

Effect:
- Lower tokens per call and better consistency.

### E. Multi-layer cache
1. Vision decision cache
- Key: image hash + normalized goal + mode
- Value: action plan + confidence + TTL

2. Content summary cache
- Key: content hash + question
- Value: summary artifact

3. Tool outcome cache
- Key: deterministic operation signature
- Value: prior result metadata

Effect:
- Eliminates repeated spend for repeated states/tasks.

### F. Provider scheduler and circuit breakers
Use a scheduler instead of ad-hoc fallback.

Features:
- Weighted provider routing by current budget and latency
- Per-provider circuit breaker (open, half-open, closed)
- Exponential backoff with jitter and capped retries
- Queue with deadline-aware draining

Effect:
- Stable behavior under temporary provider throttling.

### G. Graceful degradation modes (no hard stop)
When budget is tight:
- Switch to low-cost mode (deterministic only + cached decisions)
- Lower screenshot frequency/resolution
- Skip non-critical summarization
- Ask user whether to continue in delayed mode

Effect:
- System continues to function instead of failing.

## Free-tier-safe operating profile

Implement configuration profiles:
- `free_tier_ultra_safe`
- `balanced`
- `performance`

For `free_tier_ultra_safe`:
- Conservative soft caps below observed quota ceilings
- Mandatory queueing beyond soft cap
- One active multimodal call at a time
- Aggressive cache and state-diff gating enabled by default
- Summarization always chunked and compressed

Policy principle:
- Operate at roughly 40-60% of observed limits to absorb variance and provider policy changes.

## Token-efficiency plan (curated)

### 1) Action calls
- Short, schema-only prompts
- Hard max output tokens with compact JSON response
- Remove verbose reasoning unless debugging mode is enabled

### 2) Memory
- Store compact task state (goal, last action, blockers)
- Keep long-form history out of every request
- Retrieve only top-k relevant facts per step

### 3) Summarization
- Extractive pre-pass locally
- Rank chunks by relevance to user query
- Summarize per chunk, then merge summaries
- Persist reusable summary snapshots

### 4) Vision payload
- Crop to regions of interest when possible
- Downscale screenshots for planning passes
- Use full-resolution screenshot only on uncertainty escalation

### 5) Tool-call minimization
- Combine compatible actions into one planned step
- Avoid validation loops that call LLM repeatedly without state change

## Implementation plan to rectify this gap

### Sprint A (2-3 days): instrumentation + budgets
- Add usage telemetry wrappers around Gemini/Mistral calls.
- Implement `BudgetManager` with admission control and windows.
- Add provider scheduler skeleton and queue.

Exit criteria:
- Every provider call is metered and budget-gated.

### Sprint B (3-4 days): call reduction layer
- Add state-change detector (image hash + DOM/url checks).
- Implement deterministic-first router before multimodal calls.
- Add vision/action cache and summary cache.

Exit criteria:
- Significant drop in multimodal call count per task.

### Sprint C (2-3 days): token shaping + summarization refactor
- Replace large prompts with compact templates.
- Implement hierarchical summarization pipeline.
- Add output-token caps and debug-only verbose reasoning mode.

Exit criteria:
- Lower average tokens per successful task and fewer quota breaches.

### Sprint D (1-2 days): hardening and fail-safe UX
- Add circuit breaker policy and graceful degradation modes.
- Add user-facing status: budget usage, queue state, degrade mode.
- Add integration tests for provider throttling scenarios.

Exit criteria:
- Rate-limit events no longer cause task collapse; system degrades predictably.

## Success metrics (must track)
- Multimodal calls per completed task
- Tokens per completed task
- Cache hit ratio (vision and summary)
- Rate-limit incidents per day
- Task success rate under constrained budget
- P95 task latency in free-tier mode

Target trend after implementation:
- 50-80% fewer provider calls for repetitive workflows
- 40-70% lower token consumption per task
- Near-zero user-visible hard failures from throttling in normal usage

## Feasibility assessment for this gap
Yes, this is implementable in the current codebase. Existing separation (vision module, skills, core loop) gives clear insertion points for a Budget Manager, scheduler, state-diff gate, and caching. This is the right next deep reliability upgrade after permission architecture.
