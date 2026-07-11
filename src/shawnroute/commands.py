"""Safe argv-only subprocess execution primitives."""

from __future__ import annotations

from dataclasses import dataclass
import os
import subprocess
import tempfile
from typing import Mapping, Sequence


@dataclass(frozen=True)
class CommandResult:
    returncode: int
    stdout: str
    stderr: str


_SAFE_ENV_KEYS = {
    "PATH",
    "LANG",
    "LC_ALL",
    "LC_CTYPE",
    "TERM",
    "TMPDIR",
    "SYSTEMROOT",
    "WINDIR",
    "PATHEXT",
}
_PATH_CONTEXT_KEYS = {
    "HOME",
    "USERPROFILE",
    "XDG_CONFIG_HOME",
    "XDG_CACHE_HOME",
    "XDG_DATA_HOME",
    "XDG_STATE_HOME",
    "CODEX_HOME",
}


def _sanitized_environment(*, home: str, keep_path_context: bool) -> dict[str, str]:
    allowed = set(_SAFE_ENV_KEYS)
    if keep_path_context:
        allowed.update(_PATH_CONTEXT_KEYS)
    env = {
        key: value
        for key, value in os.environ.items()
        if key in allowed or key.startswith("LC_")
    }
    env.setdefault("PATH", os.defpath)
    env["HOME"] = home
    env["USERPROFILE"] = home
    if not keep_path_context:
        env.update(
            {
                "XDG_CONFIG_HOME": os.path.join(home, ".config"),
                "XDG_CACHE_HOME": os.path.join(home, ".cache"),
                "XDG_DATA_HOME": os.path.join(home, ".local", "share"),
                "XDG_STATE_HOME": os.path.join(home, ".local", "state"),
            }
        )
    return env


class CommandRunner:
    """Run bounded local commands without a shell.

    Raw output is returned only to the adapter that invoked it. Public models must
    contain classified metadata rather than command output. Version-only probes
    can run in an ephemeral HOME/XDG environment. Authentication status probes
    can retain path context while dropping API-key and token environment values.
    """

    def run(
        self,
        argv: Sequence[str],
        timeout: float = 5.0,
        *,
        isolate_home: bool = False,
        sanitize_env: bool = False,
    ) -> CommandResult:
        if isolate_home and sanitize_env:
            raise ValueError("isolate_home and sanitize_env are mutually exclusive")
        if isolate_home:
            with tempfile.TemporaryDirectory(prefix="shawnroute-probe-") as root:
                env = _sanitized_environment(home=root, keep_path_context=False)
                return self._run(argv, timeout, env)
        if sanitize_env:
            home = os.path.expanduser("~")
            env = _sanitized_environment(home=home, keep_path_context=True)
            return self._run(argv, timeout, env)
        return self._run(argv, timeout, None)

    @staticmethod
    def _run(
        argv: Sequence[str],
        timeout: float,
        env: Mapping[str, str] | None,
    ) -> CommandResult:
        try:
            completed = subprocess.run(
                list(argv),
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
                shell=False,
                env=env,
            )
        except subprocess.TimeoutExpired:
            return CommandResult(124, "", "command timed out")
        except OSError:
            return CommandResult(127, "", "command unavailable")
        return CommandResult(
            returncode=completed.returncode,
            stdout=completed.stdout[:65536],
            stderr=completed.stderr[:65536],
        )
