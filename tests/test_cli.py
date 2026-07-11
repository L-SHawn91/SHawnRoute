import io
import json

from shawnroute.cli import main
from shawnroute.models import CapabilityLevel, RuntimeInfo, TransportKind


class FakeAdapter:
    def __init__(self, runtime):
        self.runtime = runtime

    def detect(self):
        return self.runtime

    def inventory(self):
        return self.runtime


def available(name, capabilities):
    return RuntimeInfo(
        name=name,
        display_name=name.title(),
        installed=True,
        executable=f"/bin/{name}",
        version="1.0.0",
        capability_level=CapabilityLevel.PLANNABLE,
        transports=(TransportKind.NATIVE_RUNTIME,),
        capabilities=tuple(capabilities),
        status="available",
    )


def test_inventory_json_is_valid_and_sorted():
    output = io.StringIO()
    adapters = [
        FakeAdapter(available("codex", ("coding",))),
        FakeAdapter(available("claude", ("coding", "high_stakes"))),
    ]

    code = main(["inventory", "--json"], adapters=adapters, stdout=output)
    payload = json.loads(output.getvalue())

    assert code == 0
    assert [runtime["name"] for runtime in payload["runtimes"]] == ["claude", "codex"]
    assert payload["schema_version"] == "1"


def test_plan_json_uses_inventory_and_returns_preview():
    output = io.StringIO()
    adapters = [
        FakeAdapter(available("codex", ("coding",))),
        FakeAdapter(available("claude", ("coding", "high_stakes"))),
    ]

    code = main(
        ["plan", "--task", "coding", "--profile", "balanced", "--json"],
        adapters=adapters,
        stdout=output,
    )
    payload = json.loads(output.getvalue())

    assert code == 0
    assert payload["execution_mode"] == "preview_only"
    assert payload["selected_runtime"] == "codex"


def test_doctor_reports_missing_runtime_without_failure():
    output = io.StringIO()
    missing = RuntimeInfo(
        name="codex",
        display_name="OpenAI Codex",
        installed=False,
        status="not_installed",
    )

    code = main(["doctor"], adapters=[FakeAdapter(missing)], stdout=output)

    assert code == 0
    assert "codex" in output.getvalue()
    assert "not_installed" in output.getvalue()


def test_doctor_uses_detection_only_and_does_not_run_inventory():
    output = io.StringIO()
    detected = available("codex", ("coding",))

    class DetectOnlyAdapter:
        def detect(self):
            return detected

        def inventory(self):
            raise AssertionError("doctor must not run version/auth inventory probes")

    code = main(["doctor"], adapters=[DetectOnlyAdapter()], stdout=output)

    assert code == 0
    assert "codex" in output.getvalue()


def test_cli_does_not_write_to_home(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    before = sorted(path.relative_to(tmp_path) for path in tmp_path.rglob("*"))
    output = io.StringIO()

    code = main(
        ["plan", "--task", "coding", "--profile", "balanced", "--json"],
        adapters=[FakeAdapter(available("codex", ("coding",)))],
        stdout=output,
    )
    after = sorted(path.relative_to(tmp_path) for path in tmp_path.rglob("*"))

    assert code == 0
    assert before == after == []
