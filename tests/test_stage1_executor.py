"""Stage 1 TDD tests: ExecutionMode enum, read-only allowlist, Executor.run, provenance.

RED phase: all tests here must FAIL before implementation exists.
They must pass GREEN after implementation without weakening
test_execution_contracts.py.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from typing import Sequence

import pytest

# Imports that will fail until implementation exists.
from shawnroute.executor import (  # noqa: F401  (intentional — will fail RED)
    Executor,
    WorkerSpec,
)
from shawnroute.models import (
    ExecutionMode,
    ExecutionRequest,
    RoutePlan,
    TaskRequest,
)


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _task() -> TaskRequest:
    return TaskRequest(task="coding", profile="balanced")


def _plan() -> RoutePlan:
    return RoutePlan(
        task="coding",
        profile="balanced",
        selected_runtime=None,
        candidates=(),
    )


def _req(mode: ExecutionMode | str = ExecutionMode.PREVIEW_ONLY) -> ExecutionRequest:
    return ExecutionRequest(
        task=_task(),
        plan=_plan(),
        trace_id="trace-s1-001",
        route_owner="controller",
        idempotency_key="idem-s1-001",
        execution_mode=mode,
    )


# ---------------------------------------------------------------------------
# 1. ExecutionMode enum shape
# ---------------------------------------------------------------------------

class TestExecutionModeEnum:
    def test_three_rungs_exist(self):
        assert ExecutionMode.PREVIEW_ONLY.value == "preview_only"
        assert ExecutionMode.READ_ONLY.value == "read_only"
        assert ExecutionMode.WRITE.value == "write"

    def test_enum_is_ordered_ascending(self):
        # PREVIEW_ONLY < READ_ONLY < WRITE by declaration order.
        members = list(ExecutionMode)
        assert members == [
            ExecutionMode.PREVIEW_ONLY,
            ExecutionMode.READ_ONLY,
            ExecutionMode.WRITE,
        ]


# ---------------------------------------------------------------------------
# 2. ExecutionRequest accepts PREVIEW_ONLY and READ_ONLY; blocks WRITE
# ---------------------------------------------------------------------------

class TestExecutionRequestMode:
    def test_preview_only_accepted(self):
        req = _req(ExecutionMode.PREVIEW_ONLY)
        assert req.execution_mode == ExecutionMode.PREVIEW_ONLY

    def test_read_only_accepted(self):
        req = _req(ExecutionMode.READ_ONLY)
        assert req.execution_mode == ExecutionMode.READ_ONLY

    def test_write_is_rejected_at_construction(self):
        """WRITE must never be constructable in Stage 1."""
        with pytest.raises(ValueError, match="write.*blocked|blocked.*write|WRITE.*not.*implemented|not.*implemented.*WRITE"):
            _req(ExecutionMode.WRITE)

    def test_unknown_string_still_rejected(self):
        with pytest.raises((ValueError, TypeError)):
            _req("execute")


# ---------------------------------------------------------------------------
# 3. WorkerSpec allowlist — write-capable workers rejected at construction
# ---------------------------------------------------------------------------

class TestWorkerSpecAllowlist:
    """A WorkerSpec carrying any write-capable tool must be rejected at
    WorkerSpec.__init__ / construction time, not at run time."""

    def test_read_only_worker_is_accepted(self):
        spec = WorkerSpec(
            name="claude-read-probe",
            argv=["claude", "-p", "--allowedTools", "Read", "list runtimes"],
            mode=ExecutionMode.READ_ONLY,
        )
        assert spec.name == "claude-read-probe"

    def test_git_status_worker_is_accepted(self):
        spec = WorkerSpec(
            name="git-status",
            argv=["git", "status"],
            mode=ExecutionMode.READ_ONLY,
        )
        assert spec.name == "git-status"

    def test_worker_with_edit_tool_is_rejected(self):
        with pytest.raises(ValueError, match="write.capable|allowedTools.*Edit|Edit.*not.*permitted"):
            WorkerSpec(
                name="claude-edit",
                argv=["claude", "-p", "--allowedTools", "Edit", "fix bug"],
                mode=ExecutionMode.READ_ONLY,
            )

    def test_worker_with_write_tool_is_rejected(self):
        with pytest.raises(ValueError, match="write.capable|allowedTools.*Write|Write.*not.*permitted"):
            WorkerSpec(
                name="claude-write",
                argv=["claude", "-p", "--allowedTools", "Write,Read", "write file"],
                mode=ExecutionMode.READ_ONLY,
            )

    def test_worker_with_bash_in_allowed_tools_is_rejected(self):
        """Bash can mutate filesystem — must be blocked."""
        with pytest.raises(ValueError, match="write.capable|Bash.*not.*permitted"):
            WorkerSpec(
                name="claude-bash",
                argv=["claude", "-p", "--allowedTools", "Bash", "run script"],
                mode=ExecutionMode.READ_ONLY,
            )

    def test_write_mode_worker_rejected_regardless_of_tools(self):
        """Even a read-tool worker declared under WRITE mode must fail."""
        with pytest.raises(ValueError, match="write.*blocked|WRITE.*not.*implemented"):
            WorkerSpec(
                name="write-mode-worker",
                argv=["git", "status"],
                mode=ExecutionMode.WRITE,
            )

    def test_preview_only_worker_is_accepted_with_no_argv_execution(self):
        """PREVIEW_ONLY workers are also valid to construct."""
        spec = WorkerSpec(
            name="preview-check",
            argv=["git", "status"],
            mode=ExecutionMode.PREVIEW_ONLY,
        )
        assert spec.mode == ExecutionMode.PREVIEW_ONLY


# ---------------------------------------------------------------------------
# 4. Executor.run — PREVIEW_ONLY produces preview handle, no worker dispatch
# ---------------------------------------------------------------------------

class TestExecutorPreviewPath:
    def test_preview_only_handle_has_executes_workers_false(self):
        req = _req(ExecutionMode.PREVIEW_ONLY)
        handle = Executor().run(req)

        assert handle.executes_workers is False
        assert handle.status in {"preview_only", "blocked_preview_only"}

    def test_preview_only_handle_has_no_provenance_dispatch(self):
        """In preview mode provenance is present but no command was dispatched."""
        req = _req(ExecutionMode.PREVIEW_ONLY)
        handle = Executor().run(req)

        assert hasattr(handle, "provenance")
        # No dispatch means dispatch entries are empty or explicitly None.
        assert handle.provenance is None or handle.provenance == ()

    def test_preview_only_does_not_invoke_subprocess(self, monkeypatch):
        called = []

        def fake_run(*args, **kwargs):
            called.append(args)
            raise AssertionError("subprocess must not be called in preview mode")

        monkeypatch.setattr(subprocess, "run", fake_run)

        req = _req(ExecutionMode.PREVIEW_ONLY)
        Executor().run(req)

        assert called == []


# ---------------------------------------------------------------------------
# 5. Executor.run — READ_ONLY dispatches workers, populates provenance
# ---------------------------------------------------------------------------

class TestExecutorReadOnlyPath:
    def _fake_runner_returning(self, returncode: int, stdout: str = "", stderr: str = ""):
        """Return a CommandRunner-like object that records calls and returns fixed result."""
        from shawnroute.commands import CommandResult

        @dataclass
        class FakeRunner:
            calls: list = None

            def __post_init__(self):
                self.calls = []

            def run(self, argv: Sequence[str], timeout: float = 5.0, **kwargs) -> CommandResult:
                self.calls.append(list(argv))
                return CommandResult(returncode=returncode, stdout=stdout, stderr=stderr)

        return FakeRunner()

    def test_read_only_handle_has_executes_workers_true(self, monkeypatch):
        fake_runner = self._fake_runner_returning(0, stdout="ok")

        worker = WorkerSpec(
            name="git-status",
            argv=["git", "status"],
            mode=ExecutionMode.READ_ONLY,
        )
        req = _req(ExecutionMode.READ_ONLY)
        handle = Executor(runner=fake_runner).run(req, workers=(worker,))

        assert handle.executes_workers is True

    def test_read_only_handle_status_reflects_execution(self, monkeypatch):
        fake_runner = self._fake_runner_returning(0)
        worker = WorkerSpec(name="git-status", argv=["git", "status"], mode=ExecutionMode.READ_ONLY)
        req = _req(ExecutionMode.READ_ONLY)
        handle = Executor(runner=fake_runner).run(req, workers=(worker,))

        assert handle.status == "read_only_ok"

    def test_read_only_handle_has_provenance_with_command_and_exit_status(self):
        fake_runner = self._fake_runner_returning(0)
        worker = WorkerSpec(name="git-status", argv=["git", "status"], mode=ExecutionMode.READ_ONLY)
        req = _req(ExecutionMode.READ_ONLY)
        handle = Executor(runner=fake_runner).run(req, workers=(worker,))

        assert handle.provenance is not None
        assert len(handle.provenance) == 1
        entry = handle.provenance[0]
        # Provenance records command name and exit status — not raw stdout/stderr.
        assert entry["command"] == "git"
        assert entry["exit_status"] == 0
        assert entry["worker"] == "git-status"

    def test_provenance_does_not_contain_stdout_or_stderr(self):
        secret_output = "secret output should never appear"
        fake_runner = self._fake_runner_returning(0, stdout=secret_output, stderr=secret_output)
        worker = WorkerSpec(name="git-status", argv=["git", "status"], mode=ExecutionMode.READ_ONLY)
        req = _req(ExecutionMode.READ_ONLY)
        handle = Executor(runner=fake_runner).run(req, workers=(worker,))

        serialized = json.dumps(handle.to_dict())
        assert secret_output not in serialized

    def test_multiple_workers_produce_multiple_provenance_entries(self):
        fake_runner = self._fake_runner_returning(0)
        workers = (
            WorkerSpec(name="git-status", argv=["git", "status"], mode=ExecutionMode.READ_ONLY),
            WorkerSpec(name="git-version", argv=["git", "--version"], mode=ExecutionMode.READ_ONLY),
        )
        req = _req(ExecutionMode.READ_ONLY)
        handle = Executor(runner=fake_runner).run(req, workers=workers)

        assert len(handle.provenance) == 2
        commands = {e["command"] for e in handle.provenance}
        assert commands == {"git"}

    def test_read_only_with_no_workers_returns_no_dispatch_handle(self):
        req = _req(ExecutionMode.READ_ONLY)
        handle = Executor().run(req, workers=())

        # No workers dispatched — executes_workers can be False, status = read_only_ok
        assert handle.status in {"read_only_ok", "read_only_no_workers"}


# ---------------------------------------------------------------------------
# 6. WRITE mode is always blocked (never executes) — the hard gate
# ---------------------------------------------------------------------------

class TestWriteModeAlwaysBlocked:
    def test_executor_rejects_write_mode_request_before_any_dispatch(self, monkeypatch):
        """Executor.run must raise or return structured blocked for WRITE."""
        called = []

        def fake_subprocess(*args, **kwargs):
            called.append(args)
            raise AssertionError("subprocess must NEVER be called for WRITE mode")

        monkeypatch.setattr(subprocess, "run", fake_subprocess)

        # WRITE mode must be blocked at ExecutionRequest construction,
        # so we can't even build one. This test confirms the ValueError happens.
        with pytest.raises(ValueError, match="write.*blocked|WRITE.*not.*implemented|not.*implemented"):
            _req(ExecutionMode.WRITE)

        assert called == []


# ---------------------------------------------------------------------------
# 7. Secret-leak fixture — credential markers never appear in handle/result
# ---------------------------------------------------------------------------

class TestSecretLeakFixture:
    """Inject fake credential markers into env/args and assert they never
    surface in any handle, result, exception, or provenance output."""

    FAKE_CREDENTIALS = [
        "sk-" + "FAKELEAKTEST1234567890",
        "api_" + "key=NEVER_SURFACE_THIS",
        "AKIA" + "FAKELEAKTEST0123",  # exactly 16 uppercase/digit chars after AKIA
        "gh" + "p_FAKELEAKTESTTOKEN1234567890AB",
    ]

    def test_credential_in_env_never_surfaces_in_preview_handle(self, monkeypatch):
        for cred in self.FAKE_CREDENTIALS:
            monkeypatch.setenv("FAKE_SECRET_VAR", cred)

        req = _req(ExecutionMode.PREVIEW_ONLY)
        handle = Executor().run(req)
        serialized = json.dumps(handle.to_dict())

        for cred in self.FAKE_CREDENTIALS:
            assert cred not in serialized, f"credential leaked into preview handle: {cred!r}"

    def test_credential_in_env_never_surfaces_in_read_only_handle(self, monkeypatch):
        from shawnroute.commands import CommandResult

        @dataclass
        class LeakyFakeRunner:
            """Simulates a runner that echoes secrets (to test that executor filters them)."""
            calls: list = None

            def __post_init__(self):
                self.calls = []

            def run(self, argv: Sequence[str], timeout: float = 5.0, **kwargs) -> CommandResult:
                self.calls.append(list(argv))
                # Return exit code 0 and empty stdout — secrets must not appear from env
                return CommandResult(returncode=0, stdout="", stderr="")

        for cred in self.FAKE_CREDENTIALS:
            monkeypatch.setenv("FAKE_SECRET_VAR", cred)

        runner = LeakyFakeRunner()
        worker = WorkerSpec(name="git-status", argv=["git", "status"], mode=ExecutionMode.READ_ONLY)
        req = _req(ExecutionMode.READ_ONLY)
        handle = Executor(runner=runner).run(req, workers=(worker,))
        serialized = json.dumps(handle.to_dict())

        for cred in self.FAKE_CREDENTIALS:
            assert cred not in serialized, f"credential leaked into read-only handle: {cred!r}"

    def test_credential_in_worker_argv_is_rejected_at_construction(self):
        """WorkerSpec argv must not carry credential-like tokens."""
        for cred in self.FAKE_CREDENTIALS:
            with pytest.raises(ValueError, match="secret|credential|rejected"):
                WorkerSpec(
                    name="probe",
                    argv=["git", "status", f"--token={cred}"],
                    mode=ExecutionMode.READ_ONLY,
                )

    def test_handle_to_dict_never_emits_raw_stderr(self, monkeypatch):
        from shawnroute.commands import CommandResult

        @dataclass
        class StderrRunner:
            calls: list = None

            def __post_init__(self):
                self.calls = []

            def run(self, argv: Sequence[str], timeout: float = 5.0, **kwargs) -> CommandResult:
                self.calls.append(list(argv))
                return CommandResult(returncode=1, stdout="", stderr="access_token=NEVER_SURFACE")

        runner = StderrRunner()
        worker = WorkerSpec(name="git-fail", argv=["git", "status"], mode=ExecutionMode.READ_ONLY)
        req = _req(ExecutionMode.READ_ONLY)
        handle = Executor(runner=runner).run(req, workers=(worker,))
        serialized = json.dumps(handle.to_dict())

        assert "access_token=NEVER_SURFACE" not in serialized


# ---------------------------------------------------------------------------
# 8. Existing contracts unchanged (spot-check re-import)
# ---------------------------------------------------------------------------

class TestExistingContractsStillHold:
    def test_execution_handle_still_rejects_executes_workers_true_without_executor(self):
        """Direct ExecutionHandle construction with executes_workers=True must still raise."""
        from shawnroute.models import ExecutionHandle

        with pytest.raises(ValueError, match="executes_workers"):
            ExecutionHandle(
                execution_id="exec-direct",
                trace_id="trace-direct",
                adapter="preview",
                status="blocked_preview_only",
                executes_workers=True,
            )

    def test_route_plan_still_rejects_non_preview_execution_mode(self):
        with pytest.raises(ValueError, match="preview_only"):
            RoutePlan(
                task="coding",
                profile="balanced",
                selected_runtime=None,
                candidates=(),
                execution_mode="execute",
            )
