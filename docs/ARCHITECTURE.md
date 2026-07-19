# Architecture

## Data flow

```text
installed runtimes
  → read-only adapters
  → secret-free RuntimeInfo inventory
  → deterministic Router
  → explainable RoutePlan on stdout
  → optional bounded READ_ONLY Executor
  → sanitized provenance only
```

Routing preview is the default. Stage 1 may dispatch explicitly supplied, allowlisted read-only workers through argv-only subprocess calls. WRITE remains blocked and configuration is not mutated.

## Criticality-gated AUP recovery contract

`shawnroute.recovery` is a runtime-neutral pure policy layer. Runtime adapters classify a completed primary attempt into a sanitized `FailureKind`; the policy never reads raw prompts, stdout, stderr, credentials, or model sessions.

An explicit fallback is allowed only when all gates hold:

1. the primary subprocess failed (`returncode != 0`);
2. the sanitized failure kind is `aup_refusal`;
3. criticality is `high_stakes`;
4. a non-empty escalation reason is recorded.

The decision permits exactly one fresh process and never creates permanent model affinity. Routine requests, successful primary output that merely quotes a refusal marker, timeout, session lock, context overflow, authentication/network failure, malformed output, and other failures all return a no-fallback decision.

The contract uses route names supplied by adapters rather than hardcoding Fable or Opus. A Hermes adapter may map `claude_fable_strategy → claude_opus`; another runtime may use different route names while preserving the same gate.

## Adapter contract

Each adapter implements:

- `detect()` — PATH/application presence only
- `inventory()` — bounded official status/version probes and static capability metadata

The public result carries `adapter_api_version`, capability level, supported transport tags, and sanitized evidence. Raw command stdout/stderr never enters public models.

## Transport model

Transport is a set, not an enum field. One runtime can support multiple routes simultaneously. Codex, for example, may support ChatGPT OAuth, API-key authentication, and native App Server execution.

## Determinism

Candidates are scored using explicit capability, runtime-task fit, authentication state, and preference-profile rules. Final ordering uses `(-score, runtime_name)` so identical inventories produce byte-identical plans.

## Security boundary

- subprocess argv lists only; never `shell=True`
- bounded timeout and output capture
- version probes use ephemeral HOME/XDG plus a credential-free environment
- authentication status probes keep only path context (for example HOME/CODEX_HOME) and drop API-key/token environment values
- no credential-file parsing
- no environment-value enumeration
- no token values in evidence, logs, exceptions, or plans
- executable paths are represented by basename only
- no configuration writes; Stage 1 WRITE execution remains blocked

## Public core / private overlay boundary

```text
public shawnroute core
  ← imported by a private policy/plugin overlay
  ← private controller produces a non-executing manifest
  → public one-way preview adapter
  → secret-free RoutePlan
```

The dependency direction is one-way: a private overlay may import `shawnroute`, but the public package must not import private controller or plugin modules. Compatibility adapters accept plain mappings only and explicitly drop raw prompts, owner repositories, filesystem paths, private skill names, and full provider/model selectors.

The initial lifecycle contracts (`TaskRequest`, `ExecutionRequest`, `ExecutionHandle`, and `VerificationResult`) preserve preview compatibility. Stage 1 additionally allows `ExecutionRequest.execution_mode=read_only` through `Executor`, whose provenance contains only worker name, command basename, and exit status. `RoutePlan` remains preview-only, WRITE construction is blocked, and the NewBrain compatibility adapter remains non-executing.

## Auxiliary/runtime coexistence

SHawnRoute is not an internal auxiliary replacement. Future execution will only route explicit user-level tasks. Pinned provider/model calls and runtime-internal compression, memory, extraction, or vision helpers bypass the broker. Future envelopes will include `trace_id`, `route_owner`, and `broker_depth` to prevent duplicate dispatch and recursion.

## Maturity levels

- `detected`: executable exists
- `inventoried`: version/status probe completed but execution readiness is uncertain
- `plannable`: sufficient safe metadata exists for routing preview

These levels prevent shallow GUI/runtime adapters from pretending to have deep programmatic execution support.
