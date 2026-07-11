# Product Strategy

## Positioning

SHawnRoute is the local-first routing layer for the AI agents and providers a person already uses. It does not sell model access. It discovers runtimes, classifies safe capabilities, and explains which route best fits a task and preference profile.

## Brand

- Product: **SHawnRoute**
- Package: `shawnroute`
- Promise: **One routing layer for every AI agent you already use.**
- V1 claim: routing preview
- Future claim, only after execution lifecycle exists: orchestration

## Users

1. Individual developers paying for multiple subscriptions
2. Researchers using coding agents plus long-context and review models
3. Teams that need a shared allowed-model and approval policy
4. Enterprises that require private deployment, audit trails, and custom adapters

## Differentiation

Model routers choose a model endpoint. Workflow frameworks require users to author the workflow. SHawnRoute starts from the user's existing Claude Code, Codex, Cursor, Hermes, OpenClaw, OpenCode, API, and local-model inventory and produces a reversible, explainable policy.

## Delivery phases

### V1 — Personal routing preview

- read-only detector and inventory
- transport tags: API, subscription API, subscription OAuth, subscription CLI, native runtime, local
- deterministic task/profile ranking
- doctor, inventory, plan CLI
- Codex OAuth detection
- no config writes and no dispatch

### V1.1 — Official runtime depth

- Codex App Server account/plan/rate-limit probe
- official model-list probes where available
- Claude subscription status through supported CLI surfaces
- OpenCode Go model-list adapter
- runtime health and compatibility registry

### V1.2 — Reversible installation

- per-client generated integration plans
- backup manifest, diff, approval, apply, verify, rollback
- MCP registration for Claude Code, Codex, Cursor, OpenCode, and Hermes
- OpenClaw/Hermes native adapter installation

### V2 — Local broker

- explicit `shawn-auto` routes only
- task dispatch through official SDK/App Server/CLI/native child surfaces
- trace ID, route owner, idempotency, recursion depth, bounded fallback
- no interception of pinned auxiliary/internal calls
- evidence read-back and deterministic verification

### V3 — Team and enterprise

- policy sync and role-based approvals
- budgets, audit trails, and evaluation-backed custom ranking
- private control plane and local execution companions
- custom adapters, support, and SLA

## Monetization

Keep the correctness-critical local core and basic adapters Apache-2.0. Charge for convenience and operations rather than reselling model calls:

- paid setup and environment optimization
- cloud policy/config sync across machines
- team governance, budgets, and dashboards
- evaluation-backed personalized ranking
- enterprise private deployment and custom adapters
- support and SLA

Never pool accounts, collect personal OAuth tokens, or resell subscription capacity.

## Release sequence

1. Validate the Codex+Claude vertical slice locally.
2. Publish an alpha with explicit maturity labels.
3. Recruit a small group of users with different provider mixes.
4. Record routing decisions, user overrides, and failures without prompt/secret collection by default.
5. Build reversible installers only after adapter contracts survive version-skew testing.
6. Add execution only after recursion, approval, cancellation, and verification gates exist.

## Success metrics

- detector precision by runtime/version
- percentage of plans accepted without override
- repeatability of identical plans
- zero credential or private-path leakage
- successful rollback rate once writes are introduced
- time saved versus manual agent selection
- routing quality evaluated by task outcome, not model popularity
