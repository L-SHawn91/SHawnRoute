# SHawnRoute V1 Implementation Plan

> **For Hermes:** Execute this plan with strict vertical-slice TDD and independent read-only review.

**Goal:** Build a local-first Python router that detects installed AI agent runtimes, inventories non-secret capabilities, and emits deterministic, explainable task routes without modifying user configuration.

**Architecture:** A runtime-neutral core owns immutable models and deterministic ranking. Runtime adapters own process detection and sanitized status probes. The CLI prints JSON/text to stdout only. Codex and Claude Code prove the adapter contract; additional runtimes are deferred until the vertical slice is stable.

**Tech Stack:** Python 3.10+, standard library, pytest, setuptools.

---

## Product boundary

V1 is routing preview, not orchestration. It performs no config writes, no OAuth/API-key file parsing, no model calls, no worker dispatch, and no account pooling.

## Public interfaces

- `Adapter.detect() -> RuntimeInfo`
- `Adapter.inventory() -> RuntimeInfo`
- `Router.plan(task, profile, runtimes) -> RoutePlan`
- CLI: `doctor`, `inventory`, `plan`

## Data contract

`RuntimeInfo` includes adapter API version, installation status, executable/version, capability level, a tuple of supported transport tags, capabilities, and sanitized evidence. Transport is a set because Codex can support ChatGPT OAuth, API-key auth, and local runtime execution simultaneously.

## Safety invariants

1. Adapter outputs never contain environment values or credential-file contents.
2. Subprocess calls use argv arrays with no shell.
3. V1 writes nothing outside ordinary package/test artifacts.
4. Runtime evidence records command names and exit status only, not raw stderr unless sanitized.
5. Tie-breaking is explicit and stable.
6. Missing/broken runtimes degrade to structured unavailable results.

## Task 1: Immutable schema

**Files:** `tests/test_models.py`, `src/shawnroute/models.py`

- RED: assert transport tags serialize in sorted order and output is byte-stable.
- GREEN: implement enums and frozen dataclasses with deterministic `to_dict()`.
- Verify focused test and full suite.

## Task 2: Safe command runner and adapters

**Files:** `tests/test_adapters.py`, `src/shawnroute/commands.py`, `src/shawnroute/adapters/{base,cli}.py`

- RED: fake PATH detects Codex/Claude; missing and failing binaries return structured states.
- GREEN: implement argv-only runner, generic CLI adapter, Codex/Claude definitions.
- Add leak fixture asserting fake tokens never appear in outputs/exceptions.

## Task 3: Deterministic planner

**Files:** `tests/test_planner.py`, `src/shawnroute/planner.py`

- RED: coding+balanced prefers installed coding-capable route; unavailable runtimes are excluded; ties are stable.
- GREEN: implement static explainable scoring and explicit tie break.
- Add high-stakes reviewer requirement as an explanation/warning, not orchestration claim.

## Task 4: CLI vertical slice

**Files:** `tests/test_cli.py`, `src/shawnroute/cli.py`, `src/shawnroute/__init__.py`

- RED: doctor/inventory/plan produce valid output and never create files under a temporary HOME.
- GREEN: implement argparse CLI and adapter registry.
- Verify installed entry point in a clean venv.

## Task 5: Public hardening

**Files:** `scripts/public_safety_scan.py`, `SECURITY.md`, `CONTRIBUTING.md`

- Scan tracked text for private absolute paths, credential assignments, and common secret formats.
- Run deterministic repeat test, read-only filesystem snapshot test, pytest, compile, package build/install smoke.
- Obtain Fable read-only architecture/readback review and DeepSeek independent review.

## Release gate

- all tests pass with no warnings
- two identical inventory inputs produce byte-identical plan JSON
- fake credential markers absent from stdout/stderr/exceptions
- clean temporary-HOME CLI smoke writes no files
- public safety scan passes
- `git diff --check` passes
- GitHub publication remains a separate explicit step after final readback
