# newbrain-router

Execute-safely layer: dry-run-only public agent-router templates, scoring, explainability, and approval-gate examples. No live private agents, credentials, or internal routing state.

**License:** Apache-2.0

## SHawn OSS stack role

This repository is an **early-stage public-safe scaffold**. APIs are unstable. It supports the SHawn Research OS flagship rather than replacing it.

| Layer | Public repo | Role |
|---|---|---|
| Search | [`shawn-bio-search-lite`](https://github.com/L-SHawn91/shawn-bio-search-lite) | Public scholarly metadata adapters |
| Map | [`paper-map-lite`](https://github.com/L-SHawn91/paper-map-lite) | Toy claim/evidence graph schemas |
| Report | [`SHawn-ResearchOS`](https://github.com/L-SHawn91/SHawn-ResearchOS) | Flagship evidence maps and public reports |
| Coordinate | [`shawn-sync-lite`](https://github.com/L-SHawn91/shawn-sync-lite) | Public-safe manifests and boundary templates |
| Execute safely | [`newbrain-router`](https://github.com/L-SHawn91/newbrain-router) | Dry-run routing and approval-gate examples |
| QA docs | [`shawn-docx-qa`](https://github.com/L-SHawn91/shawn-docx-qa) / [`SHawn-hwp`](https://github.com/L-SHawn91/SHawn-hwp) | Document QA utilities |
| Present | [`SHawn-WEB`](https://github.com/L-SHawn91/SHawn-WEB) | Public hub/demo surface |

## Public boundary

This repository is a clean public-safe projection. It contains only schemas, templates, toy data, public metadata adapters, mock executors, and public reports.

It must not contain private databases, private manuscripts, PDFs, private corpora, local/internal paths, Discord identifiers, workflow logs, memory exports, credentials, or private project state.

## Quick start

```bash
python -m pip install -e .[dev]
python -m pytest -q
python scripts/public_safety_scan.py .
```

## Status

Early public scaffold for OpenAI/Codex OSS maintainer evidence and public-safe SHawn OSS release gates.

## Project documents

- [Roadmap](ROADMAP.md)
- [Changelog](CHANGELOG.md)
- [Contributing](CONTRIBUTING.md)
- [Security](SECURITY.md)
- [Public boundary](docs/PUBLIC_BOUNDARY.md)
