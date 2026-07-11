"""Built-in read-only CLI runtime adapters."""

from __future__ import annotations

from dataclasses import dataclass
import os
import re
import shutil
from typing import Callable, Sequence

from shawnroute.commands import CommandRunner
from shawnroute.models import CapabilityLevel, RuntimeInfo, TransportKind


Finder = Callable[[str], str | None]
_VERSION_PATTERN = re.compile(r"(?<!\d)(\d+\.\d+(?:\.\d+)?(?:[-+][A-Za-z0-9.-]+)?)")


def _public_executable(path: str) -> str:
    return os.path.basename(path)


@dataclass(frozen=True)
class RuntimeSpec:
    name: str
    display_name: str
    binary: str
    version_args: tuple[str, ...]
    capabilities: tuple[str, ...]
    transports: tuple[TransportKind, ...]
    auth_status_args: tuple[str, ...] | None = None

    @classmethod
    def codex(cls) -> "RuntimeSpec":
        return cls(
            name="codex",
            display_name="OpenAI Codex",
            binary="codex",
            version_args=("--version",),
            auth_status_args=("login", "status"),
            capabilities=("coding", "quick", "review", "research", "long_context"),
            transports=(
                TransportKind.API_KEY,
                TransportKind.SUBSCRIPTION_OAUTH,
                TransportKind.NATIVE_RUNTIME,
            ),
        )

    @classmethod
    def claude(cls) -> "RuntimeSpec":
        return cls(
            name="claude",
            display_name="Claude Code",
            binary="claude",
            version_args=("--version",),
            capabilities=("coding", "review", "research", "long_context", "high_stakes"),
            transports=(
                TransportKind.API_KEY,
                TransportKind.SUBSCRIPTION_CLI,
                TransportKind.NATIVE_RUNTIME,
            ),
        )

    @classmethod
    def hermes(cls) -> "RuntimeSpec":
        return cls(
            name="hermes",
            display_name="Hermes Agent",
            binary="hermes",
            version_args=("--version",),
            capabilities=("quick", "research", "coding", "review", "long_context"),
            transports=(TransportKind.NATIVE_RUNTIME,),
        )

    @classmethod
    def openclaw(cls) -> "RuntimeSpec":
        return cls(
            name="openclaw",
            display_name="OpenClaw",
            binary="openclaw",
            version_args=("--version",),
            capabilities=("quick", "research", "coding", "review", "long_context"),
            transports=(TransportKind.NATIVE_RUNTIME,),
        )

    @classmethod
    def opencode(cls) -> "RuntimeSpec":
        return cls(
            name="opencode",
            display_name="OpenCode",
            binary="opencode",
            version_args=("--version",),
            capabilities=("quick", "research", "coding", "review", "long_context"),
            transports=(
                TransportKind.SUBSCRIPTION_API,
                TransportKind.NATIVE_RUNTIME,
            ),
        )

    @classmethod
    def cursor(cls) -> "RuntimeSpec":
        return cls(
            name="cursor",
            display_name="Cursor Agent",
            binary="agent",
            version_args=("--version",),
            capabilities=("coding", "review", "research", "long_context"),
            transports=(
                TransportKind.SUBSCRIPTION_CLI,
                TransportKind.NATIVE_RUNTIME,
            ),
        )

    @classmethod
    def builtins(cls) -> tuple["RuntimeSpec", ...]:
        return (
            cls.codex(),
            cls.claude(),
            cls.hermes(),
            cls.openclaw(),
            cls.opencode(),
            cls.cursor(),
        )


class CliAdapter:
    def __init__(
        self,
        spec: RuntimeSpec,
        *,
        finder: Finder = shutil.which,
        runner: CommandRunner | None = None,
    ) -> None:
        self.spec = spec
        self.finder = finder
        self.runner = runner or CommandRunner()

    def detect(self) -> RuntimeInfo:
        executable = self.finder(self.spec.binary)
        if executable is None:
            return self._not_installed()
        return RuntimeInfo(
            name=self.spec.name,
            display_name=self.spec.display_name,
            installed=True,
            executable=_public_executable(executable),
            capability_level=CapabilityLevel.DETECTED,
            transports=self.spec.transports,
            capabilities=self.spec.capabilities,
            evidence=(f"binary:{self.spec.binary}:found",),
            status="detected",
        )

    def inventory(self) -> RuntimeInfo:
        executable = self.finder(self.spec.binary)
        if executable is None:
            return self._not_installed()

        version_result = self.runner.run(
            (executable, *self.spec.version_args),
            isolate_home=True,
        )
        if version_result.returncode != 0:
            return RuntimeInfo(
                name=self.spec.name,
                display_name=self.spec.display_name,
                installed=True,
                executable=_public_executable(executable),
                capability_level=CapabilityLevel.DETECTED,
                transports=self.spec.transports,
                capabilities=self.spec.capabilities,
                evidence=(f"binary:{self.spec.binary}:found", "version-probe:failed"),
                status="probe_failed",
            )

        version = self._parse_version(version_result.stdout)
        status = "available"
        evidence = [f"binary:{self.spec.binary}:found", "version-probe:ok"]
        level = CapabilityLevel.PLANNABLE

        if self.spec.auth_status_args is not None:
            auth = self.runner.run(
                (executable, *self.spec.auth_status_args),
                sanitize_env=True,
            )
            evidence.append("auth-status-probe:ok" if auth.returncode == 0 else "auth-status-probe:failed")
            status = self._classify_auth(
                auth.returncode,
                f"{auth.stdout}\n{auth.stderr}",
            )
            if auth.returncode != 0:
                level = CapabilityLevel.INVENTORIED

        return RuntimeInfo(
            name=self.spec.name,
            display_name=self.spec.display_name,
            installed=True,
            executable=_public_executable(executable),
            version=version,
            capability_level=level,
            transports=self.spec.transports,
            capabilities=self.spec.capabilities,
            evidence=tuple(evidence),
            status=status,
        )

    def _not_installed(self) -> RuntimeInfo:
        return RuntimeInfo(
            name=self.spec.name,
            display_name=self.spec.display_name,
            installed=False,
            evidence=(f"binary:{self.spec.binary}:not-found",),
            status="not_installed",
        )

    @staticmethod
    def _parse_version(output: str) -> str | None:
        match = _VERSION_PATTERN.search(output)
        return match.group(1) if match else None

    @staticmethod
    def _classify_auth(returncode: int, output: str) -> str:
        if returncode != 0:
            return "authentication_unknown"
        lowered = output.lower()
        if "chatgpt" in lowered or "oauth" in lowered:
            return "authenticated_oauth"
        if "api key" in lowered or "api-key" in lowered:
            return "authenticated_api_key"
        if "logged in" in lowered or "authenticated" in lowered:
            return "authenticated"
        return "authentication_unknown"
