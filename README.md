# SHawnRoute

**One routing layer for every AI agent you already use.**

SHawnRoute is a local-first, explainable router that detects installed AI agent runtimes, inventories safe capability metadata, and recommends the best available route for a task. It does not collect credential values and does not modify agent configuration in V1.

## Current status

Early V1 implementation. The honest boundary is **routing preview**, not orchestration.

Implemented target:

- read-only runtime detection
- secret-free capability inventory
- deterministic, explainable route plans
- Codex and Claude Code vertical slice
- stdout-only `doctor`, `inventory`, and `plan`

Deferred:

- config mutation and rollback execution
- worker dispatch and lifecycle management
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
