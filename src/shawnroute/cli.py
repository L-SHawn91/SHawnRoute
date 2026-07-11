"""Command-line interface for the SHawnRoute routing preview."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Iterable, Sequence, TextIO

from shawnroute.adapters.base import RuntimeAdapter
from shawnroute.adapters.cli import CliAdapter, RuntimeSpec
from shawnroute.models import RuntimeInfo
from shawnroute.planner import PROFILES, TASKS, Router


SCHEMA_VERSION = "1"


def builtin_adapters() -> list[RuntimeAdapter]:
    return [CliAdapter(spec) for spec in RuntimeSpec.builtins()]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="shawnroute",
        description="Local-first, explainable AI-agent routing preview.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    doctor = subparsers.add_parser("doctor", help="Check installed runtime status")
    doctor.add_argument("--json", action="store_true", dest="as_json")

    inventory = subparsers.add_parser(
        "inventory", help="Print secret-free runtime capability inventory"
    )
    inventory.add_argument("--json", action="store_true", dest="as_json")

    plan = subparsers.add_parser("plan", help="Create an explainable routing preview")
    plan.add_argument("--task", choices=TASKS, required=True)
    plan.add_argument("--profile", choices=PROFILES, default="balanced")
    plan.add_argument("--json", action="store_true", dest="as_json")

    return parser


def _inventory(adapters: Iterable[RuntimeAdapter]) -> list[RuntimeInfo]:
    return sorted(
        (adapter.inventory() for adapter in adapters),
        key=lambda runtime: runtime.name,
    )


def _detect(adapters: Iterable[RuntimeAdapter]) -> list[RuntimeInfo]:
    return sorted(
        (adapter.detect() for adapter in adapters),
        key=lambda runtime: runtime.name,
    )


def _inventory_payload(runtimes: Sequence[RuntimeInfo]) -> dict[str, object]:
    return {
        "schema_version": SCHEMA_VERSION,
        "execution_mode": "read_only",
        "runtimes": [runtime.to_dict() for runtime in runtimes],
    }


def _write_json(stdout: TextIO, payload: object) -> None:
    stdout.write(json.dumps(payload, indent=2, sort_keys=True))
    stdout.write("\n")


def main(
    argv: Sequence[str] | None = None,
    *,
    adapters: Sequence[RuntimeAdapter] | None = None,
    stdout: TextIO | None = None,
) -> int:
    args = build_parser().parse_args(argv)
    output = stdout or sys.stdout
    selected_adapters = list(adapters) if adapters is not None else builtin_adapters()

    if args.command == "doctor":
        runtimes = _detect(selected_adapters)
        if args.as_json:
            _write_json(output, _inventory_payload(runtimes))
        else:
            output.write("SHawnRoute V1 — non-executing runtime detection\n")
            for runtime in runtimes:
                output.write(
                    f"- {runtime.name}: {runtime.status} "
                    f"(installed={str(runtime.installed).lower()})\n"
                )
        return 0

    runtimes = _inventory(selected_adapters)

    if args.command == "inventory":
        if args.as_json:
            _write_json(output, _inventory_payload(runtimes))
        else:
            output.write("SHawnRoute V1 — read-only routing preview\n")
            for runtime in runtimes:
                version = runtime.version or "unknown"
                output.write(
                    f"- {runtime.name}: {runtime.status} "
                    f"(installed={str(runtime.installed).lower()}, version={version})\n"
                )
        return 0

    if args.command == "plan":
        plan = Router().plan(args.task, args.profile, runtimes)
        if args.as_json:
            _write_json(output, plan.to_dict())
        else:
            output.write("SHawnRoute routing preview\n")
            output.write(f"task: {plan.task}\n")
            output.write(f"profile: {plan.profile}\n")
            output.write(f"selected: {plan.selected_runtime or 'none'}\n")
            for candidate in plan.candidates:
                output.write(
                    f"- {candidate.runtime}: score={candidate.score}; "
                    f"reasons={', '.join(candidate.reasons)}\n"
                )
            for warning in plan.warnings:
                output.write(f"warning: {warning}\n")
        return 0

    raise AssertionError(f"unhandled command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
