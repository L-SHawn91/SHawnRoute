"""Safe, one-way compatibility for non-executing NewBrain plan manifests."""

from __future__ import annotations

from collections.abc import Mapping
import re
from typing import Any

from shawnroute.models import RouteCandidate, RoutePlan


_INPUT_MODE = "dry_run_manifest_only"
_KNOWN_RUNTIMES = {
    "claude",
    "codex",
    "cursor",
    "hermes",
    "local",
    "newbrain",
    "ollama",
    "openclaw",
    "opencode",
}
_ACTION_TASKS = {
    "delete": "high_stakes",
    "execute": "high_stakes",
    "review": "review",
    "route": "quick",
    "supervise": "high_stakes",
    "write": "coding",
}
_COST_PROFILES = {
    "cheap": "cost",
    "high_safety": "quality",
    "normal": "balanced",
}
_PERMISSION_CLASSES = {
    "approval_required_execution": "approval_required",
    "approval_required_reversible_delete": "approval_required",
    "bounded_execution": "bounded_execution",
    "bounded_write": "bounded_write",
    "orchestration_preview": "read_only",
    "read_only_review": "read_only",
    "route_preview": "read_only",
}


class NewBrainPreviewAdapter:
    """Normalize an explicit dry-run manifest into a public ``RoutePlan``.

    The adapter intentionally drops raw commands, owner repositories, paths,
    skill names, full provider/model selectors, and private policy blocks.
    It imports no NewBrain or private-plugin code.
    """

    def to_route_plan(self, payload: Mapping[str, Any]) -> RoutePlan:
        if not isinstance(payload, Mapping):
            raise ValueError("payload must be a mapping")
        self._validate_boundary(payload)

        route = payload.get("route")
        if not isinstance(route, Mapping):
            raise ValueError("route must be a mapping")
        if route.get("execution_mode") != "preview_only":
            raise ValueError("route execution_mode must be preview_only")
        if route.get("writes_canonical_state") is not False:
            raise ValueError("route writes_canonical_state must be explicitly False")

        action_class = self._required_string(route, "action_class")
        if action_class not in _ACTION_TASKS:
            raise ValueError(f"unsupported action_class: {action_class}")
        cost_lane = self._required_string(route, "cost_lane")
        if cost_lane not in _COST_PROFILES:
            raise ValueError(f"unsupported cost_lane: {cost_lane}")
        approval_required = route.get("approval_required")
        if not isinstance(approval_required, bool):
            raise ValueError("approval_required must be a boolean")

        model_routing = route.get("model_routing")
        if not isinstance(model_routing, Mapping):
            raise ValueError("model_routing must be a mapping")
        primary_worker = self._required_string(model_routing, "primary_worker")
        runtime = self._public_runtime(primary_worker)
        permission = self._public_permission(
            self._required_string(model_routing, "permission_lane")
        )

        status_summary = payload.get("status_summary")
        if not isinstance(status_summary, Mapping):
            raise ValueError("status_summary must be a mapping")
        score = status_summary.get("score")
        if (
            isinstance(score, bool)
            or not isinstance(score, int)
            or not 0 <= score <= 100
        ):
            raise ValueError("status_summary.score must be an integer from 0 to 100")
        status = self._required_string(status_summary, "status")
        if not re.fullmatch(r"[A-Z][A-Z0-9_]*", status):
            raise ValueError("status_summary.status must be a public status token")

        task = "high_stakes" if approval_required else _ACTION_TASKS[action_class]
        profile = "quality" if approval_required else _COST_PROFILES[cost_lane]
        candidate = RouteCandidate(
            runtime=runtime,
            score=score,
            reasons=(
                "source:newbrain_preview",
                f"source_status:{status}",
                f"action_class:{action_class}",
                f"cost_lane:{cost_lane}",
                f"approval_required:{str(approval_required).lower()}",
                f"permission_lane:{permission}",
            ),
        )
        return RoutePlan(
            task=task,
            profile=profile,
            selected_runtime=runtime,
            candidates=(candidate,),
            warnings=("compat:newbrain_preview",),
            execution_mode="preview_only",
        )

    @staticmethod
    def _validate_boundary(payload: Mapping[str, Any]) -> None:
        for field in (
            "execution_mode",
            "executes_workers",
            "writes_canonical_state",
        ):
            if field not in payload:
                raise ValueError(f"{field} is required")
        if payload["execution_mode"] != _INPUT_MODE:
            raise ValueError("execution_mode must be dry_run_manifest_only")
        if payload["executes_workers"] is not False:
            raise ValueError("executes_workers must be explicitly False")
        if payload["writes_canonical_state"] is not False:
            raise ValueError("writes_canonical_state must be explicitly False")

    @staticmethod
    def _required_string(payload: Mapping[str, Any], field: str) -> str:
        value = payload.get(field)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{field} must be a non-empty string")
        return value.strip()

    @staticmethod
    def _public_runtime(selector: str) -> str:
        runtime = selector.split(":", 1)[0].lower()
        if runtime not in _KNOWN_RUNTIMES:
            return "external"
        return runtime

    @staticmethod
    def _public_permission(permission_lane: str) -> str:
        return _PERMISSION_CLASSES.get(permission_lane, "restricted")
