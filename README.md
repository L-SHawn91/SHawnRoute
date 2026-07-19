# SHawnRoute

**One routing layer for every AI agent you already use.**

SHawnRoute is a local-first, explainable router that detects installed AI agent runtimes, inventories safe capability metadata, and recommends the best available route for a task. It does not collect credential values and does not modify agent configuration in V1.

## Current status

Early Stage 1 implementation. Routing preview remains the public default. A bounded read-only executor and pure recovery-policy contracts exist, but write execution and autonomous multi-step orchestration remain blocked.

Implemented target:

- read-only runtime detection
- secret-free capability inventory
- deterministic, explainable route plans
- immutable preview-only execution/verification contracts
- bounded argv-only read-only worker execution with sanitized provenance
- criticality-gated AUP recovery decisions: routine defaults to no fallback; failed high-stakes AUP requires a non-empty reason and permits one fresh non-affine hop
- one-way, field-dropping compatibility for explicit dry-run manifests
- Codex and Claude Code vertical slice
- stdout-only `doctor`, `inventory`, and `plan`

Deferred:

- config mutation and rollback execution
- write-capable worker dispatch, autonomous retry loops, and full lifecycle management
- hosted credential handling
- account pooling or model-call resale

## Development

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e '.[dev]'
pytest
shawnroute doctor
shawnroute inventory --json
shawnroute plan --task coding --profile balanced --json
```

## Security model

SHawnRoute asks official runtimes for sanitized status. It must never read, return, log, or upload API-key/OAuth token values. Personal subscription execution remains on the user's machine through official runtime surfaces such as Codex CLI/App Server.

## License

Apache-2.0
