"""The retained public mock API must stay dry-run and require approval."""
import subprocess
import sys
from pathlib import Path


def test_installed_legacy_package_keeps_safe_decision_contract():
    result = subprocess.run(
        [sys.executable, '-c',
         'import json; from newbrain_router import explain; print(json.dumps(explain("paper search")))'],
        cwd=Path(__file__).parents[1], capture_output=True, text=True, check=True,
    )
    import json
    decision = json.loads(result.stdout)
    assert decision['route'] == 'search-lite'
    assert decision['dry_run'] is True
    assert decision['approval_required'] is True
