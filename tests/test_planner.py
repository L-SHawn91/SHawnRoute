import json

from shawnroute.models import CapabilityLevel, RuntimeInfo, TransportKind
from shawnroute.planner import Router


def runtime(name, capabilities, transports=(), installed=True, status="available"):
    return RuntimeInfo(
        name=name,
        display_name=name.title(),
        installed=installed,
        executable=f"/bin/{name}" if installed else None,
        version="1.0.0" if installed else None,
        capability_level=CapabilityLevel.PLANNABLE if installed else CapabilityLevel.DETECTED,
        transports=tuple(transports),
        capabilities=tuple(capabilities),
        status=status,
    )


def test_balanced_coding_prefers_codex_and_explains_score():
    codex = runtime(
        "codex",
        ("coding", "quick", "review"),
        (TransportKind.SUBSCRIPTION_OAUTH, TransportKind.NATIVE_RUNTIME),
        status="authenticated_oauth",
    )
    claude = runtime(
        "claude",
        ("coding", "review", "high_stakes"),
        (TransportKind.SUBSCRIPTION_CLI, TransportKind.NATIVE_RUNTIME),
    )

    plan = Router().plan("coding", "balanced", [claude, codex])

    assert plan.selected_runtime == "codex"
    assert plan.candidates[0].runtime == "codex"
    assert any(
        reason.startswith("capability:coding=")
        for reason in plan.candidates[0].reasons
    )
    assert plan.execution_mode == "preview_only"


def test_high_stakes_prefers_claude_and_warns_that_review_is_not_dispatched():
    codex = runtime("codex", ("coding", "review"))
    claude = runtime("claude", ("review", "high_stakes"))

    plan = Router().plan("high_stakes", "quality", [codex, claude])

    assert plan.selected_runtime == "claude"
    assert any("does not dispatch" in warning for warning in plan.warnings)


def test_unavailable_runtime_is_excluded_and_plan_is_byte_deterministic():
    missing = runtime("codex", ("coding",), installed=False)
    claude = runtime("claude", ("coding",), (TransportKind.SUBSCRIPTION_CLI,))
    router = Router()

    payloads = {
        json.dumps(
            router.plan("coding", "balanced", [missing, claude]).to_dict(),
            sort_keys=True,
            separators=(",", ":"),
        )
        for _ in range(100)
    }

    assert len(payloads) == 1
    payload = json.loads(payloads.pop())
    assert payload["selected_runtime"] == "claude"
    assert [candidate["runtime"] for candidate in payload["candidates"]] == ["claude"]


def test_no_matching_capability_returns_no_route():
    plan = Router().plan("research", "balanced", [runtime("codex", ("coding",))])

    assert plan.selected_runtime is None
    assert plan.candidates == ()
    assert "no compatible installed runtime" in plan.warnings
