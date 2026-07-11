# Architecture

## Data flow

```text
installed runtimes
  → read-only adapters
  → secret-free RuntimeInfo inventory
  → deterministic Router
  → explainable RoutePlan on stdout
```

V1 stops at the plan. It does not dispatch workers or mutate configuration.

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
- no writes in V1

## Auxiliary/runtime coexistence

SHawnRoute is not an internal auxiliary replacement. Future execution will only route explicit user-level tasks. Pinned provider/model calls and runtime-internal compression, memory, extraction, or vision helpers bypass the broker. Future envelopes will include `trace_id`, `route_owner`, and `broker_depth` to prevent duplicate dispatch and recursion.

## Maturity levels

- `detected`: executable exists
- `inventoried`: version/status probe completed but execution readiness is uncertain
- `plannable`: sufficient safe metadata exists for routing preview

These levels prevent shallow GUI/runtime adapters from pretending to have deep programmatic execution support.
