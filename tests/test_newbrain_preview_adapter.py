import ast
import json
from pathlib import Path
import sys

import pytest

from shawnroute.adapters.newbrain_preview import NewBrainPreviewAdapter


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "newbrain_execution_plan_preview.json"


def load_fixture() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_newbrain_execution_plan_maps_to_public_preview_without_private_fields():
    payload = load_fixture()
    plan = NewBrainPreviewAdapter().to_route_plan(payload)
    encoded = json.dumps(plan.to_dict(), sort_keys=True)

    assert plan.execution_mode == "preview_only"
    assert plan.task == "coding"
    assert plan.profile == "balanced"
    assert plan.selected_runtime == "codex"
    assert plan.candidates[0].score == 88
    assert "source_status:PASS_WITH_WARN" in plan.candidates[0].reasons
    assert "permission_lane:bounded_write" in plan.candidates[0].reasons
    assert "compat:newbrain_preview" in plan.warnings

    for private_value in (
        payload["command"],
        payload["target_path"],
        payload["route"]["target_repo"],
        payload["route"]["hermes_skill"],
        "private-provider",
        "private-model",
        "/home/",
    ):
        assert private_value not in encoded


def test_adapter_is_byte_deterministic():
    payload = load_fixture()
    payloads = {
        json.dumps(
            NewBrainPreviewAdapter().to_route_plan(payload).to_dict(),
            sort_keys=True,
            separators=(",", ":"),
        )
        for _ in range(100)
    }

    assert len(payloads) == 1


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("execution_mode", "execute"),
        ("executes_workers", True),
        ("executes_workers", "true"),
        ("writes_canonical_state", True),
        ("writes_canonical_state", "true"),
    ],
)
def test_adapter_fails_closed_on_execution_or_write_capability(field, value):
    payload = load_fixture()
    payload[field] = value

    with pytest.raises(ValueError):
        NewBrainPreviewAdapter().to_route_plan(payload)


def test_adapter_fails_closed_when_explicit_boundary_fields_are_missing():
    for field in ("execution_mode", "executes_workers", "writes_canonical_state"):
        payload = load_fixture()
        payload.pop(field)
        with pytest.raises(ValueError, match=field):
            NewBrainPreviewAdapter().to_route_plan(payload)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("execution_mode", "execute"),
        ("writes_canonical_state", True),
        ("writes_canonical_state", "true"),
    ],
)
def test_adapter_fails_closed_on_nested_route_boundary(field, value):
    payload = load_fixture()
    payload["route"][field] = value

    with pytest.raises(ValueError):
        NewBrainPreviewAdapter().to_route_plan(payload)


def test_adapter_requires_nested_route_and_dry_run_manifest_mode():
    payload = load_fixture()
    payload.pop("route")
    with pytest.raises(ValueError, match="route"):
        NewBrainPreviewAdapter().to_route_plan(payload)

    payload = load_fixture()
    payload["execution_mode"] = "preview_only"
    with pytest.raises(ValueError, match="dry_run_manifest_only"):
        NewBrainPreviewAdapter().to_route_plan(payload)


@pytest.mark.parametrize("field", ["execution_mode", "writes_canonical_state"])
def test_adapter_fails_closed_when_nested_route_boundary_is_missing(field):
    payload = load_fixture()
    payload["route"].pop(field)
    with pytest.raises(ValueError, match=field):
        NewBrainPreviewAdapter().to_route_plan(payload)


def test_public_package_has_no_private_import_dependency():
    forbidden_roots = {"projects", "shawn_brain", "shawnroute_shawn"}
    findings = []
    for path in sorted((ROOT / "src" / "shawnroute").rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported = [alias.name.split(".")[0] for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported = [node.module.split(".")[0]]
            else:
                continue
            for root in imported:
                if root in forbidden_roots:
                    findings.append(f"{path.relative_to(ROOT)} imports {root}")

    assert findings == []


def test_adapter_does_not_load_private_modules_at_runtime():
    before = set(sys.modules)
    NewBrainPreviewAdapter().to_route_plan(load_fixture())
    newly_loaded = set(sys.modules) - before

    assert not any(
        name == "projects"
        or name.startswith("projects.")
        or name == "shawn_brain"
        or name.startswith("shawn_brain.")
        or name == "shawnroute_shawn"
        or name.startswith("shawnroute_shawn.")
        for name in newly_loaded
    )
