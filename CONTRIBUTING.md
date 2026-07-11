# Contributing

SHawnRoute welcomes small, tested adapters and routing improvements.

## Requirements

1. Open an issue describing the official runtime surface and supported versions.
2. Do not parse or include credential values.
3. Add fake-secret non-leak tests and missing/broken-runtime tests.
4. Keep subprocess calls argv-only, bounded, and read-only.
5. Preserve deterministic plan output.
6. Label adapter maturity honestly: detected, inventoried, or plannable.
7. Run `pytest`, `python -m compileall`, and the public safety scanner.

Adapters based on unofficial browser-cookie extraction, account sharing, rate-limit bypass, or token forwarding will not be accepted.
