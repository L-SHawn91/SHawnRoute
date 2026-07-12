import json

import pytest

from shawnroute.models import (
    ExecutionHandle,
    ExecutionRequest,
    RoutePlan,
    TaskRequest,
    VerificationResult,
)


def empty_plan() -> RoutePlan:
    return RoutePlan(
        task="coding",
        profile="balanced",
        selected_runtime=None,
        candidates=(),
    )


def test_task_request_is_immutable_secret_resistant_and_deterministic():
    request = TaskRequest(
        task="coding",
        profile="balanced",
        constraints=("read_only", "deterministic", "read_only"),
    )

    assert request.to_dict() == {
        "schema_version": "1",
        "task": "coding",
        "profile": "balanced",
        "constraints": ["deterministic", "read_only"],
    }
    assert json.dumps(request.to_dict(), sort_keys=True) == json.dumps(
        request.to_dict(), sort_keys=True
    )

    marker = "api_" + "key=" + "NOT_PUBLIC_123456789"
    with pytest.raises(ValueError, match="secret-like"):
        TaskRequest(task="coding", profile="balanced", constraints=(marker,))

    with pytest.raises(ValueError, match="machine token"):
        TaskRequest(task="raw prompt with spaces", profile="balanced")
    with pytest.raises(ValueError, match="machine token"):
        TaskRequest(task="coding", profile="품질")


def test_execution_request_is_preview_only_and_bounds_broker_depth():
    request = ExecutionRequest(
        task=TaskRequest(task="coding", profile="balanced"),
        plan=empty_plan(),
        trace_id="trace-001",
        route_owner="controller",
        idempotency_key="idem-001",
        broker_depth=0,
    )

    assert request.to_dict()["execution_mode"] == "preview_only"
    assert request.to_dict()["broker_depth"] == 0
    assert request.to_dict()["plan"]["execution_mode"] == "preview_only"

    with pytest.raises(ValueError, match="preview_only"):
        ExecutionRequest(
            task=request.task,
            plan=request.plan,
            trace_id="trace-002",
            route_owner="controller",
            idempotency_key="idem-002",
            execution_mode="execute",
        )

    for invalid_depth in (-1, 4, True):
        with pytest.raises(ValueError, match="broker_depth"):
            ExecutionRequest(
                task=request.task,
                plan=request.plan,
                trace_id=f"trace-{invalid_depth}",
                route_owner="controller",
                idempotency_key=f"idem-{invalid_depth}",
                broker_depth=invalid_depth,
            )

    with pytest.raises(ValueError, match="parent_task_id"):
        ExecutionRequest(
            task=request.task,
            plan=request.plan,
            trace_id="trace-parent",
            route_owner="controller",
            idempotency_key="idem-parent",
            parent_task_id=" ",
        )


def test_execution_handle_cannot_claim_worker_dispatch():
    handle = ExecutionHandle(
        execution_id="exec-001",
        trace_id="trace-001",
        adapter="preview",
        status="blocked_preview_only",
    )

    assert handle.executes_workers is False
    assert handle.to_dict()["status"] == "blocked_preview_only"

    with pytest.raises(ValueError, match="executes_workers"):
        ExecutionHandle(
            execution_id="exec-002",
            trace_id="trace-002",
            adapter="preview",
            status="blocked_preview_only",
            executes_workers=True,
        )


def test_verification_result_is_a_result_container_not_an_executor():
    result = VerificationResult(
        verifier="schema",
        passed=True,
        checks=("secret_scan", "schema", "secret_scan"),
        warnings=("preview_only",),
    )

    assert result.to_dict() == {
        "schema_version": "1",
        "verifier": "schema",
        "passed": True,
        "checks": ["schema", "secret_scan"],
        "warnings": ["preview_only"],
    }


def test_route_plan_rejects_non_preview_execution_modes():
    with pytest.raises(ValueError, match="preview_only"):
        RoutePlan(
            task="coding",
            profile="balanced",
            selected_runtime=None,
            candidates=(),
            execution_mode="execute",
        )
