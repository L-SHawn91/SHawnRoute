import json

from shawnroute.adapters.cli import CliAdapter, RuntimeSpec
from shawnroute.commands import CommandResult
from shawnroute.models import CapabilityLevel, TransportKind


class FakeRunner:
    def __init__(self, responses):
        self.responses = responses
        self.calls = []

    def run(
        self,
        argv,
        timeout=5.0,
        *,
        isolate_home=False,
        sanitize_env=False,
    ):
        key = tuple(argv)
        self.calls.append((key, isolate_home, sanitize_env))
        return self.responses[key]


def test_codex_inventory_classifies_oauth_without_returning_raw_status():
    marker = "sk-" + "THIS_MUST_NEVER_LEAK_123456"
    runner = FakeRunner(
        {
            ("/opt/codex", "--version"): CommandResult(0, "codex-cli 0.144.1\n", ""),
            ("/opt/codex", "login", "status"): CommandResult(
                0, f"Logged in using ChatGPT\ninternal={marker}\n", ""
            ),
        }
    )
    adapter = CliAdapter(
        RuntimeSpec.codex(),
        finder=lambda _: "/opt/codex",
        runner=runner,
    )

    runtime = adapter.inventory()
    payload = json.dumps(runtime.to_dict(), sort_keys=True)

    assert runtime.installed is True
    assert runtime.version == "0.144.1"
    assert runtime.status == "authenticated_oauth"
    assert runtime.capability_level == CapabilityLevel.PLANNABLE
    assert TransportKind.SUBSCRIPTION_OAUTH in runtime.transports
    assert marker not in payload
    assert "Logged in using ChatGPT" not in payload


def test_missing_runtime_returns_structured_unavailable_result():
    adapter = CliAdapter(RuntimeSpec.claude(), finder=lambda _: None, runner=FakeRunner({}))

    runtime = adapter.inventory()

    assert runtime.installed is False
    assert runtime.status == "not_installed"
    assert runtime.executable is None
    assert runtime.evidence == ("binary:claude:not-found",)


def test_failed_version_probe_does_not_expose_stderr():
    marker = "access_token=NEVER_PRINT_THIS"
    runner = FakeRunner(
        {("/opt/claude", "--version"): CommandResult(1, "", marker)}
    )
    adapter = CliAdapter(
        RuntimeSpec.claude(), finder=lambda _: "/opt/claude", runner=runner
    )

    runtime = adapter.inventory()
    payload = json.dumps(runtime.to_dict(), sort_keys=True)

    assert runtime.installed is True
    assert runtime.version is None
    assert runtime.status == "probe_failed"
    assert marker not in payload


def test_builtin_runtime_specs_are_unique_and_include_all_v1_targets():
    specs = RuntimeSpec.builtins()

    assert [spec.name for spec in specs] == [
        "codex",
        "claude",
        "hermes",
        "openclaw",
        "opencode",
        "cursor",
    ]
    assert len({spec.binary for spec in specs}) == len(specs)
    assert RuntimeSpec.cursor().binary == "agent"


def test_codex_auth_status_can_be_classified_from_stderr_without_leak():
    marker = "refresh_" + "token=" + "NEVER_LEAK_FROM_STDERR"
    runner = FakeRunner(
        {
            ("/opt/codex", "--version"): CommandResult(0, "codex-cli 0.144.1", ""),
            ("/opt/codex", "login", "status"): CommandResult(
                0, "", f"Logged in using ChatGPT\n{marker}"
            ),
        }
    )
    adapter = CliAdapter(
        RuntimeSpec.codex(), finder=lambda _: "/opt/codex", runner=runner
    )

    runtime = adapter.inventory()
    payload = json.dumps(runtime.to_dict(), sort_keys=True)

    assert runtime.status == "authenticated_oauth"
    assert marker not in payload


def test_home_prefix_is_redacted_from_public_executable(monkeypatch):
    monkeypatch.setenv("HOME", "/home/example-user")
    runner = FakeRunner(
        {
            ("/home/example-user/bin/claude", "--version"): CommandResult(
                0, "2.1.110", ""
            )
        }
    )
    adapter = CliAdapter(
        RuntimeSpec.claude(),
        finder=lambda _: "/home/example-user/bin/claude",
        runner=runner,
    )

    runtime = adapter.inventory()

    assert runtime.executable == "claude"
    assert "example-user" not in json.dumps(runtime.to_dict())
