"""Immutable, secret-resistant public data contracts for SHawnRoute."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import re
from typing import Any


ADAPTER_API_VERSION = "1"


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
