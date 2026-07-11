"""Deterministic, explainable routing preview."""

from __future__ import annotations

from collections.abc import Iterable

from shawnroute.models import (
    CapabilityLevel,
    RouteCandidate,
    RoutePlan,
    RuntimeInfo,
    TransportKind,
)


TASKS = ("quick", "research", "long_context", "coding", "review", "high_stakes")
PROFILES = ("balanced", "quality", "cost", "quota_saver", "privacy")

_RUNTIME_TASK_BONUS: dict[str, dict[str, int]] = {
    "coding": {"codex": 30, "claude": 25},
    "quick": {"codex": 20, "claude": 10},
    "review": {"claude": 30, "codex": 20},
    "research": {"claude": 20, "codex": 15},
    "long_context": {"claude": 25, "codex": 15},
    "high_stakes": {"claude": 40, "codex": 10},
}


class Router:
    def plan(
        self,
        task: str,
        profile: str,
        runtimes: Iterable[RuntimeInfo],
    ) -> RoutePlan:
        if task not in TASKS:
            raise ValueError(f"unsupported task: {task}")
        if profile not in PROFILES:
            raise ValueError(f"unsupported profile: {profile}")

        candidates = []
        for runtime in runtimes:
            if not runtime.installed or task not in runtime.capabilities:
                continue
            candidate = self._score(runtime, task, profile)
            candidates.append(candidate)

        candidates.sort(key=lambda item: (-item.score, item.runtime))
        selected = candidates[0].runtime if candidates else None
        warnings: list[str] = []
        if not candidates:
            warnings.append("no compatible installed runtime")
        if task == "high_stakes":
            warnings.append(
                "routing preview only; V1 does not dispatch or approve an independent reviewer"
            )

        return RoutePlan(
            task=task,
            profile=profile,
            selected_runtime=selected,
            candidates=tuple(candidates),
            warnings=tuple(warnings),
        )

    def _score(self, runtime: RuntimeInfo, task: str, profile: str) -> RouteCandidate:
        score = 100
        reasons = [f"capability:{task}=100"]

        if runtime.capability_level == CapabilityLevel.PLANNABLE:
            score += 20
            reasons.append("capability_level:plannable=20")
        if runtime.status.startswith("authenticated"):
            score += 10
            reasons.append("authenticated=10")

        runtime_bonus = _RUNTIME_TASK_BONUS.get(task, {}).get(runtime.name, 0)
        if runtime_bonus:
            score += runtime_bonus
            reasons.append(f"task_fit:{runtime.name}={runtime_bonus}")

        profile_score, profile_reasons = self._profile_score(runtime, profile)
        score += profile_score
        reasons.extend(profile_reasons)

        return RouteCandidate(
            runtime=runtime.name,
            score=score,
            reasons=tuple(reasons),
            transports=runtime.transports,
        )

    @staticmethod
    def _profile_score(runtime: RuntimeInfo, profile: str) -> tuple[int, list[str]]:
        transports = set(runtime.transports)
        reasons: list[str] = []
        score = 0
        subscription = {
            TransportKind.SUBSCRIPTION_API,
            TransportKind.SUBSCRIPTION_CLI,
            TransportKind.SUBSCRIPTION_OAUTH,
        }

        if profile == "balanced":
            if transports & subscription:
                score += 10
                reasons.append("profile:balanced:subscription=10")
            if TransportKind.NATIVE_RUNTIME in transports:
                score += 5
                reasons.append("profile:balanced:native=5")
        elif profile == "quality":
            if "high_stakes" in runtime.capabilities:
                score += 15
                reasons.append("profile:quality:high_stakes=15")
            if "review" in runtime.capabilities:
                score += 5
                reasons.append("profile:quality:review=5")
        elif profile == "cost":
            if transports & subscription:
                score += 20
                reasons.append("profile:cost:subscription=20")
            if TransportKind.LOCAL in transports:
                score += 15
                reasons.append("profile:cost:local=15")
        elif profile == "quota_saver":
            if TransportKind.LOCAL in transports:
                score += 25
                reasons.append("profile:quota_saver:local=25")
            if TransportKind.API_KEY in transports:
                score += 10
                reasons.append("profile:quota_saver:api_key=10")
        elif profile == "privacy":
            if TransportKind.LOCAL in transports:
                score += 30
                reasons.append("profile:privacy:local=30")
            if TransportKind.NATIVE_RUNTIME in transports:
                score += 10
                reasons.append("profile:privacy:native=10")
            if TransportKind.API_KEY in transports:
                score -= 5
                reasons.append("profile:privacy:external_api=-5")

        return score, reasons
