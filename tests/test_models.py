import json

from shawnroute.models import (
    CapabilityLevel,
    RouteCandidate,
    RoutePlan,
    RuntimeInfo,
    TransportKind,
)


def test_runtime_info_serializes_transports_and_capabilities_deterministically():
    runtime = RuntimeInfo(
        name="codex",
        display_name="OpenAI Codex",
        installed=True,
        executable="/usr/bin/codex",
        version="0.144.1",
        capability_level=CapabilityLevel.INVENTORIED,
        transports=(TransportKind.SUBSCRIPTION_OAUTH, TransportKind.API_KEY),
        capabilities=("coding", "quick", "coding"),
        evidence=("binary:codex", "version-command"),
    )

    first = json.dumps(runtime.to_dict(), sort_keys=True, separators=(",", ":"))
    second = json.dumps(runtime.to_dict(), sort_keys=True, separators=(",", ":"))

    assert first == second
    assert runtime.to_dict()["transports"] == ["api_key", "subscription_oauth"]
    assert runtime.to_dict()["capabilities"] == ["coding", "quick"]
    assert runtime.to_dict()["adapter_api_version"] == "1"


def test_runtime_info_rejects_secret_like_evidence():
    try:
        RuntimeInfo(
            name="codex",
            display_name="OpenAI Codex",
            installed=True,
            evidence=("Authorization: Bearer fake-secret-value",),
        )
    except ValueError as exc:
        assert "secret-like" in str(exc)
    else:
        raise AssertionError("secret-like evidence must be rejected")


def test_runtime_info_rejects_secret_like_values_in_any_public_field():
    marker = "api_" + "key=" + "THIS_VALUE_MUST_NOT_ESCAPE_123"
    try:
        RuntimeInfo(
            name="codex",
            display_name="OpenAI Codex",
            installed=True,
            version=marker,
        )
    except ValueError as exc:
        assert "secret-like" in str(exc)
    else:
        raise AssertionError("secret-like public fields must be rejected")


def test_runtime_info_rejects_common_provider_token_shapes():
    markers = (
        "ghp_" + "A" * 24,
        "AKIA" + "B" * 16,
        "xoxb-" + "1234567890-ABCDEFGHIJ",
    )

    for marker in markers:
        try:
            RuntimeInfo(
                name="codex",
                display_name="OpenAI Codex",
                installed=True,
                status=marker,
            )
        except ValueError as exc:
            assert "secret-like" in str(exc)
        else:
            raise AssertionError("provider-shaped token must be rejected")


def test_route_models_reject_secret_like_reasons_and_warnings():
    marker = "access_" + "token=" + "THIS_VALUE_MUST_NOT_ESCAPE_123"

    for build in (
        lambda: RouteCandidate(runtime="codex", score=1, reasons=(marker,)),
        lambda: RoutePlan(
            task="coding",
            profile="balanced",
            selected_runtime=None,
            candidates=(),
            warnings=(marker,),
        ),
    ):
        try:
            build()
        except ValueError as exc:
            assert "secret-like" in str(exc)
        else:
            raise AssertionError("secret-like route metadata must be rejected")
