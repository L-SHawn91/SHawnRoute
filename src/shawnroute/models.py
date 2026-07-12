"""Immutable, secret-resistant public data contracts for SHawnRoute."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import re
from typing import Any


ADAPTER_API_VERSION = "1"
MAX_BROKER_DEPTH = 3


class TransportKind(str, Enum):
    API_KEY = "api_key"
    SUBSCRIPTION_API = "subscription_api"
    SUBSCRIPTION_OAUTH = "subscription_oauth"
    SUBSCRIPTION_CLI = "subscription_cli"
    NATIVE_RUNTIME = "native_runtime"
    LOCAL = "local"


class CapabilityLevel(str, Enum):
    DETECTED = "detected"
    INVENTORIED = "inventoried"
    PLANNABLE = "plannable"


_SECRET_PATTERNS = (
    re.compile(r"authorization\s*:\s*bearer\s+\S+", re.IGNORECASE),
    re.compile(r"\b(?:api[_-]?key|access[_-]?token|refresh[_-]?token|secret)\s*[=:]\s*\S+", re.IGNORECASE),
    re.compile(r"\bsk-[A-Za-z0-9_-]{8,}"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bAKIA[A-Z0-9]{16}\b"),
    re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{16,}\b"),
)
_MACHINE_TOKEN = re.compile(r"[a-z][a-z0-9_]{0,63}")


def _reject_secret_like(values: tuple[str, ...]) -> None:
    for value in values:
        if any(pattern.search(value) for pattern in _SECRET_PATTERNS):
            raise ValueError("secret-like value rejected from public runtime metadata")


@dataclass(frozen=True)
class RuntimeInfo:
    name: str
    display_name: str
    installed: bool
    executable: str | None = None
    version: str | None = None
    capability_level: CapabilityLevel = CapabilityLevel.DETECTED
    transports: tuple[TransportKind, ...] = ()
    capabilities: tuple[str, ...] = ()
    evidence: tuple[str, ...] = ()
    status: str = "unknown"
    adapter_api_version: str = ADAPTER_API_VERSION

    def __post_init__(self) -> None:
        public_values = (
            self.name,
            self.display_name,
            self.executable or "",
            self.version or "",
            self.status,
            self.adapter_api_version,
            *self.capabilities,
            *self.evidence,
        )
        _reject_secret_like(tuple(str(item) for item in public_values))

    def to_dict(self) -> dict[str, Any]:
        return {
            "adapter_api_version": self.adapter_api_version,
            "name": self.name,
            "display_name": self.display_name,
            "installed": self.installed,
            "executable": self.executable,
            "version": self.version,
            "capability_level": self.capability_level.value,
            "transports": sorted({item.value for item in self.transports}),
            "capabilities": sorted(set(self.capabilities)),
            "evidence": list(self.evidence),
            "status": self.status,
        }


@dataclass(frozen=True)
class RouteCandidate:
    runtime: str
    score: int
    reasons: tuple[str, ...]
    transports: tuple[TransportKind, ...] = ()

    def __post_init__(self) -> None:
        _reject_secret_like((self.runtime, *self.reasons))

    def to_dict(self) -> dict[str, Any]:
        return {
            "runtime": self.runtime,
            "score": self.score,
            "reasons": list(self.reasons),
            "transports": sorted({item.value for item in self.transports}),
        }


@dataclass(frozen=True)
class RoutePlan:
    task: str
    profile: str
    selected_runtime: str | None
    candidates: tuple[RouteCandidate, ...]
    warnings: tuple[str, ...] = ()
    execution_mode: str = "preview_only"
    schema_version: str = "1"

    def __post_init__(self) -> None:
        if self.execution_mode != "preview_only":
            raise ValueError("RoutePlan execution_mode must be preview_only")
        _reject_secret_like(
            (
                self.task,
                self.profile,
                self.selected_runtime or "",
                self.execution_mode,
                self.schema_version,
                *self.warnings,
            )
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "task": self.task,
            "profile": self.profile,
            "execution_mode": self.execution_mode,
            "selected_runtime": self.selected_runtime,
            "candidates": [candidate.to_dict() for candidate in self.candidates],
            "warnings": list(self.warnings),
        }


@dataclass(frozen=True)
class TaskRequest:
    """Generic task metadata only; raw prompts belong to private controllers."""

    task: str
    profile: str
    constraints: tuple[str, ...] = ()
    schema_version: str = "1"

    def __post_init__(self) -> None:
        if not _MACHINE_TOKEN.fullmatch(self.task) or not _MACHINE_TOKEN.fullmatch(
            self.profile
        ):
            raise ValueError("task and profile must be lowercase machine tokens")
        _reject_secret_like(
            (self.task, self.profile, self.schema_version, *self.constraints)
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "task": self.task,
            "profile": self.profile,
            "constraints": sorted(set(self.constraints)),
        }


@dataclass(frozen=True)
class ExecutionRequest:
    """A non-executing request envelope for adapter/plugin previews."""

    task: TaskRequest
    plan: RoutePlan
    trace_id: str
    route_owner: str
    idempotency_key: str
    parent_task_id: str | None = None
    broker_depth: int = 0
    execution_mode: str = "preview_only"
    schema_version: str = "1"

    def __post_init__(self) -> None:
        if self.execution_mode != "preview_only":
            raise ValueError("ExecutionRequest execution_mode must be preview_only")
        if (
            isinstance(self.broker_depth, bool)
            or not isinstance(self.broker_depth, int)
            or not 0 <= self.broker_depth <= MAX_BROKER_DEPTH
        ):
            raise ValueError(
                f"broker_depth must be an integer between 0 and {MAX_BROKER_DEPTH}"
            )
        if self.parent_task_id is not None and not self.parent_task_id.strip():
            raise ValueError("parent_task_id must be non-empty when provided")
        identifiers = (
            self.trace_id,
            self.route_owner,
            self.idempotency_key,
            self.parent_task_id or "",
            self.execution_mode,
            self.schema_version,
        )
        if any(not value.strip() for value in identifiers[:3]):
            raise ValueError("trace_id, route_owner, and idempotency_key are required")
        _reject_secret_like(identifiers)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "execution_mode": self.execution_mode,
            "trace_id": self.trace_id,
            "parent_task_id": self.parent_task_id,
            "broker_depth": self.broker_depth,
            "route_owner": self.route_owner,
            "idempotency_key": self.idempotency_key,
            "task": self.task.to_dict(),
            "plan": self.plan.to_dict(),
        }


@dataclass(frozen=True)
class ExecutionHandle:
    """Preview lifecycle evidence; it cannot represent a dispatched worker."""

    execution_id: str
    trace_id: str
    adapter: str
    status: str = "blocked_preview_only"
    executes_workers: bool = False
    warnings: tuple[str, ...] = ()
    schema_version: str = "1"

    def __post_init__(self) -> None:
        if self.executes_workers is not False:
            raise ValueError("ExecutionHandle executes_workers must be False")
        if self.status not in {"preview_only", "blocked_preview_only"}:
            raise ValueError(
                "ExecutionHandle status must be preview_only or blocked_preview_only"
            )
        required = (self.execution_id, self.trace_id, self.adapter)
        if any(not value.strip() for value in required):
            raise ValueError("execution_id, trace_id, and adapter are required")
        _reject_secret_like(
            (*required, self.status, self.schema_version, *self.warnings)
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "execution_id": self.execution_id,
            "trace_id": self.trace_id,
            "adapter": self.adapter,
            "status": self.status,
            "executes_workers": self.executes_workers,
            "warnings": list(self.warnings),
        }


@dataclass(frozen=True)
class VerificationResult:
    """Deterministic verification evidence without verifier execution logic."""

    verifier: str
    passed: bool
    checks: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    schema_version: str = "1"

    def __post_init__(self) -> None:
        if not self.verifier.strip():
            raise ValueError("verifier is required")
        _reject_secret_like(
            (self.verifier, self.schema_version, *self.checks, *self.warnings)
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "verifier": self.verifier,
            "passed": self.passed,
            "checks": sorted(set(self.checks)),
            "warnings": list(self.warnings),
        }
