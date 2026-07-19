"""Runtime-neutral, criticality-gated AUP recovery decisions.

This module does not execute workers or inspect raw model output. Runtime adapters
classify a completed primary attempt into a sanitized ``FailureKind`` and pass
only public routing metadata here.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from shawnroute.models import _reject_secret_like


class Criticality(str, Enum):
    ROUTINE = "routine"
    HIGH_STAKES = "high_stakes"


class FailureKind(str, Enum):
    AUP_REFUSAL = "aup_refusal"
    TIMEOUT = "timeout"
    SESSION_LOCK = "session_lock"
    CONTEXT_OVERFLOW = "context_overflow"
    AUTH_NETWORK = "auth_network"
    MALFORMED_OUTPUT = "malformed_output"
    OTHER = "other"


@dataclass(frozen=True)
class RecoveryContext:
    primary_route: str
    fallback_route: str
    primary_returncode: int
    failure_kind: FailureKind | str
    criticality: Criticality | str = Criticality.ROUTINE
    escalation_reason: str = ""

    def __post_init__(self) -> None:
        try:
            failure_kind = FailureKind(self.failure_kind)
        except ValueError as exc:
            raise ValueError(f"unsupported failure_kind: {self.failure_kind!r}") from exc
        try:
            criticality = Criticality(self.criticality)
        except ValueError as exc:
            raise ValueError(f"unsupported criticality: {self.criticality!r}") from exc
        if (
            isinstance(self.primary_returncode, bool)
            or not isinstance(self.primary_returncode, int)
        ):
            raise ValueError("primary_returncode must be an integer")
        if not self.primary_route.strip() or not self.fallback_route.strip():
            raise ValueError("primary_route and fallback_route are required")

        reason = self.escalation_reason.strip()
        _reject_secret_like(
            (self.primary_route, self.fallback_route, failure_kind.value, reason)
        )
        object.__setattr__(self, "failure_kind", failure_kind)
        object.__setattr__(self, "criticality", criticality)
        object.__setattr__(self, "escalation_reason", reason)


@dataclass(frozen=True)
class RecoveryDecision:
    attempt: bool
    primary_route: str
    fallback_route: str | None
    criticality: Criticality
    failure_kind: FailureKind
    escalation_reason: str
    reason_code: str
    max_attempts: int = 0
    fresh_process: bool = False
    permanent_affinity: bool = False

    def __post_init__(self) -> None:
        public_values = (
            self.primary_route,
            self.fallback_route or "",
            self.criticality.value,
            self.failure_kind.value,
            self.escalation_reason,
            self.reason_code,
        )
        _reject_secret_like(public_values)
        if self.attempt and self.max_attempts != 1:
            raise ValueError("an approved AUP recovery must be exactly one attempt")
        if not self.attempt and self.max_attempts != 0:
            raise ValueError("a blocked AUP recovery must have zero attempts")

    def to_dict(self) -> dict[str, Any]:
        return {
            "attempt": self.attempt,
            "criticality": self.criticality.value,
            "escalation_reason": self.escalation_reason,
            "failure_kind": self.failure_kind.value,
            "fallback_route": self.fallback_route,
            "fresh_process": self.fresh_process,
            "max_attempts": self.max_attempts,
            "permanent_affinity": self.permanent_affinity,
            "primary_route": self.primary_route,
            "reason_code": self.reason_code,
        }


def decide_aup_recovery(context: RecoveryContext) -> RecoveryDecision:
    """Return a deterministic one-hop recovery decision without dispatching."""

    criticality = Criticality(context.criticality)
    failure_kind = FailureKind(context.failure_kind)

    if context.primary_returncode == 0:
        reason_code = "primary_succeeded"
    elif failure_kind is not FailureKind.AUP_REFUSAL:
        reason_code = f"failure_not_aup:{failure_kind.value}"
    elif criticality is Criticality.ROUTINE:
        reason_code = "routine_no_explicit_fallback"
    elif not context.escalation_reason:
        reason_code = "missing_escalation_reason"
    else:
        return RecoveryDecision(
            attempt=True,
            primary_route=context.primary_route,
            fallback_route=context.fallback_route,
            criticality=criticality,
            failure_kind=failure_kind,
            escalation_reason=context.escalation_reason,
            reason_code="high_stakes_aup_one_hop",
            max_attempts=1,
            fresh_process=True,
            permanent_affinity=False,
        )

    return RecoveryDecision(
        attempt=False,
        primary_route=context.primary_route,
        fallback_route=None,
        criticality=criticality,
        failure_kind=failure_kind,
        escalation_reason=context.escalation_reason,
        reason_code=reason_code,
        max_attempts=0,
        fresh_process=False,
        permanent_affinity=False,
    )
