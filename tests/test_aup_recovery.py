"""Criticality-gated AUP recovery policy tests."""

from __future__ import annotations

import pytest

from shawnroute.recovery import (
    Criticality,
    FailureKind,
    RecoveryContext,
    decide_aup_recovery,
)


def _context(**overrides) -> RecoveryContext:
    values = {
        "primary_route": "claude_fable_strategy",
        "fallback_route": "claude_opus",
        "primary_returncode": 1,
        "failure_kind": FailureKind.AUP_REFUSAL,
        "criticality": Criticality.ROUTINE,
        "escalation_reason": "",
    }
    values.update(overrides)
    return RecoveryContext(**values)


def test_routine_aup_fails_closed_without_fallback() -> None:
    decision = decide_aup_recovery(_context())

    assert decision.attempt is False
    assert decision.reason_code == "routine_no_explicit_fallback"
    assert decision.max_attempts == 0


def test_high_stakes_aup_requires_non_empty_reason() -> None:
    decision = decide_aup_recovery(
        _context(criticality=Criticality.HIGH_STAKES, escalation_reason="   ")
    )

    assert decision.attempt is False
    assert decision.reason_code == "missing_escalation_reason"


def test_failed_high_stakes_aup_allows_one_fresh_non_affine_fallback() -> None:
    decision = decide_aup_recovery(
        _context(
            criticality=Criticality.HIGH_STAKES,
            escalation_reason="durable routing policy final review",
        )
    )

    assert decision.attempt is True
    assert decision.fallback_route == "claude_opus"
    assert decision.max_attempts == 1
    assert decision.fresh_process is True
    assert decision.permanent_affinity is False
    assert decision.escalation_reason == "durable routing policy final review"


def test_successful_primary_never_falls_back_even_if_output_classifier_says_aup() -> None:
    decision = decide_aup_recovery(
        _context(
            primary_returncode=0,
            criticality=Criticality.HIGH_STAKES,
            escalation_reason="durable routing policy final review",
        )
    )

    assert decision.attempt is False
    assert decision.reason_code == "primary_succeeded"


@pytest.mark.parametrize(
    "failure_kind",
    [
        FailureKind.TIMEOUT,
        FailureKind.SESSION_LOCK,
        FailureKind.CONTEXT_OVERFLOW,
        FailureKind.AUTH_NETWORK,
        FailureKind.MALFORMED_OUTPUT,
        FailureKind.OTHER,
    ],
)
def test_non_aup_failures_never_use_model_fallback(failure_kind: FailureKind) -> None:
    decision = decide_aup_recovery(
        _context(
            failure_kind=failure_kind,
            criticality=Criticality.HIGH_STAKES,
            escalation_reason="durable routing policy final review",
        )
    )

    assert decision.attempt is False
    assert decision.reason_code == f"failure_not_aup:{failure_kind.value}"


def test_decision_serialization_is_explicit_and_stable() -> None:
    decision = decide_aup_recovery(
        _context(
            criticality=Criticality.HIGH_STAKES,
            escalation_reason="durable routing policy final review",
        )
    )

    assert decision.to_dict() == {
        "attempt": True,
        "criticality": "high_stakes",
        "escalation_reason": "durable routing policy final review",
        "failure_kind": "aup_refusal",
        "fallback_route": "claude_opus",
        "fresh_process": True,
        "max_attempts": 1,
        "permanent_affinity": False,
        "primary_route": "claude_fable_strategy",
        "reason_code": "high_stakes_aup_one_hop",
    }


def test_secret_like_escalation_reason_is_rejected() -> None:
    with pytest.raises(ValueError, match="secret-like"):
        _context(
            criticality=Criticality.HIGH_STAKES,
            escalation_reason="api_key=FAKE_SECRET_VALUE",
        )
