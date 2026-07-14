"""Stage 1 Executor: safe argv-only worker dispatch for READ_ONLY mode.

Safety invariants (mirror spec):
- No shell; all subprocess calls go through commands.CommandRunner (argv arrays only).
- WRITE mode is unconditionally blocked — raises ValueError at ExecutionRequest construction.
- Workers carrying write-capable tools (Edit, Write, Bash) are rejected at WorkerSpec
  construction, not at run time.
- Provenance records command name + exit status only; raw stdout/stderr never surfaces.
- Credential-like values in WorkerSpec.argv are rejected at construction.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from typing import Sequence

from shawnroute.commands import CommandResult, CommandRunner
from shawnroute.models import (
    ExecutionMode,
    ExecutionRequest,
    ExecutorHandle,
    ProvenanceEntry,
    _reject_secret_like,
)


# ---------------------------------------------------------------------------
# Write-capable tool allowlist / denylist
# ---------------------------------------------------------------------------

# Tools that are provably non-mutating and legal in READ_ONLY mode.
_READ_ONLY_TOOLS: frozenset[str] = frozenset(
    {
        "Read",
        "Glob",
        "Grep",
        "LS",
        "WebSearch",
        "WebFetch",
    }
)

# Tools that can mutate filesystem or execute arbitrary code — forbidden in READ_ONLY.
_WRITE_CAPABLE_TOOLS: frozenset[str] = frozenset(
    {
        "Edit",
        "Write",
        "Bash",
        "MultiEdit",
        "NotebookEdit",
        "NotebookRun",
        "TodoWrite",
    }
)

# Pattern to extract tool names from --allowedTools value.
# Handles both comma-separated ("Read,Edit") and space-separated lists.
_TOOL_SPLIT = re.compile(r"[,\s]+")


def _extract_allowed_tools(argv: Sequence[str]) -> list[str]:
    """Return the tool names from --allowedTools flag in argv, or []."""
    argv_list = list(argv)
    for i, arg in enumerate(argv_list):
        if arg == "--allowedTools" and i + 1 < len(argv_list):
            return [t.strip() for t in _TOOL_SPLIT.split(argv_list[i + 1]) if t.strip()]
        if arg.startswith("--allowedTools="):
            value = arg.split("=", 1)[1]
            return [t.strip() for t in _TOOL_SPLIT.split(value) if t.strip()]
    return []


def _reject_write_capable_tools(argv: Sequence[str]) -> None:
    """Raise ValueError if argv carries any write-capable tool in --allowedTools."""
    tools = _extract_allowed_tools(argv)
    for tool in tools:
        if tool in _WRITE_CAPABLE_TOOLS:
            raise ValueError(
                f"write-capable tool '{tool}' is not permitted in READ_ONLY WorkerSpec; "
                f"allowedTools must only contain read-only tools: {sorted(_READ_ONLY_TOOLS)}"
            )


# ---------------------------------------------------------------------------
# WorkerSpec — the unit of work submitted to Executor.run
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class WorkerSpec:
    """Description of a single worker command to dispatch.

    Construction rejects:
    - Any mode other than PREVIEW_ONLY or READ_ONLY (WRITE is blocked Stage 1+).
    - Any --allowedTools list that includes a write-capable tool.
    - Any credential-like value in argv.
    """

    name: str
    argv: tuple[str, ...]
    mode: ExecutionMode = ExecutionMode.READ_ONLY

    def __init__(
        self,
        name: str,
        argv: Sequence[str],
        mode: ExecutionMode | str = ExecutionMode.READ_ONLY,
    ) -> None:
        # Normalise mode to enum.
        if not isinstance(mode, ExecutionMode):
            try:
                mode = ExecutionMode(mode)
            except ValueError:
                raise ValueError(
                    f"WorkerSpec mode must be a valid ExecutionMode; got {mode!r}"
                )

        if mode is ExecutionMode.WRITE:
            raise ValueError(
                "WorkerSpec mode 'write' is blocked — "
                "WRITE mode is not implemented in Stage 1"
            )

        argv_tuple = tuple(argv)

        # Reject credential-like values in argv.
        _reject_secret_like(argv_tuple)

        # Reject write-capable tools in --allowedTools.
        _reject_write_capable_tools(argv_tuple)

        object.__setattr__(self, "name", name)
        object.__setattr__(self, "argv", argv_tuple)
        object.__setattr__(self, "mode", mode)


# ---------------------------------------------------------------------------
# Executor
# ---------------------------------------------------------------------------

class Executor:
    """Dispatch read-only workers via argv-only subprocess (no shell).

    For PREVIEW_ONLY requests: returns a non-dispatching handle (executes_workers=False).
    For READ_ONLY requests: dispatches each worker via CommandRunner, records sanitized
    provenance (command name + exit status only — no raw stdout/stderr).
    WRITE requests are blocked at ExecutionRequest construction and never reach here.
    """

    def __init__(self, runner: CommandRunner | None = None) -> None:
        self._runner: CommandRunner = runner or CommandRunner()

    def run(
        self,
        request: ExecutionRequest,
        workers: Sequence[WorkerSpec] = (),
    ) -> ExecutorHandle:
        mode = request.execution_mode
        execution_id = str(uuid.uuid4())
        trace_id = request.trace_id

        if mode is ExecutionMode.PREVIEW_ONLY:
            return ExecutorHandle(
                execution_id=execution_id,
                trace_id=trace_id,
                adapter="executor:preview",
                status="preview_only",
                executes_workers=False,
                provenance=None,
            )

        if mode is ExecutionMode.READ_ONLY:
            return self._run_read_only(execution_id, trace_id, list(workers))

        # Should never be reached (WRITE blocked at ExecutionRequest construction),
        # but guard defensively.
        raise ValueError(
            f"Executor.run: execution_mode {mode!r} is blocked or unimplemented"
        )

    def _run_read_only(
        self,
        execution_id: str,
        trace_id: str,
        workers: list[WorkerSpec],
    ) -> ExecutorHandle:
        if not workers:
            return ExecutorHandle(
                execution_id=execution_id,
                trace_id=trace_id,
                adapter="executor:read_only",
                status="read_only_no_workers",
                executes_workers=False,
                provenance=(),
            )

        provenance_entries: list[ProvenanceEntry] = []
        any_failure = False

        for worker in workers:
            result: CommandResult = self._runner.run(
                worker.argv,
                isolate_home=True,
            )
            # Record command name (argv[0]) + exit status only.
            # Raw stdout/stderr are intentionally dropped here.
            command_name = worker.argv[0] if worker.argv else "(empty)"
            provenance_entries.append(
                ProvenanceEntry(
                    worker=worker.name,
                    command=command_name,
                    exit_status=result.returncode,
                )
            )
            if result.returncode != 0:
                any_failure = True

        status = "read_only_failed" if any_failure else "read_only_ok"

        return ExecutorHandle(
            execution_id=execution_id,
            trace_id=trace_id,
            adapter="executor:read_only",
            status=status,
            executes_workers=True,
            provenance=tuple(provenance_entries),
        )
