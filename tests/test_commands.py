import subprocess

from shawnroute.commands import CommandRunner


def test_command_runner_converts_missing_binary_to_structured_result(monkeypatch):
    def missing(*args, **kwargs):
        raise FileNotFoundError("binary disappeared")

    monkeypatch.setattr(subprocess, "run", missing)

    result = CommandRunner().run(["missing-agent", "--version"])

    assert result.returncode == 127
    assert result.stdout == ""
    assert result.stderr == "command unavailable"


def test_command_runner_converts_timeout_to_structured_result(monkeypatch):
    def timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd=args[0], timeout=kwargs["timeout"])

    monkeypatch.setattr(subprocess, "run", timeout)

    result = CommandRunner().run(["slow-agent", "--version"], timeout=0.01)

    assert result.returncode == 124
    assert result.stdout == ""
    assert result.stderr == "command timed out"


def test_isolated_probe_uses_ephemeral_home_and_cleans_it(monkeypatch):
    captured_home = None
    captured_env = None
    monkeypatch.setenv("OPENAI_API_KEY", "fake-value-that-must-not-reach-probe")

    def write_cache(*args, **kwargs):
        nonlocal captured_home, captured_env
        captured_env = kwargs["env"]
        captured_home = captured_env["HOME"]
        from pathlib import Path

        marker = Path(captured_home) / ".generated-by-runtime"
        marker.write_text("cache", encoding="utf-8")
        return subprocess.CompletedProcess(args[0], 0, stdout="1.2.3", stderr="")

    monkeypatch.setattr(subprocess, "run", write_cache)

    result = CommandRunner().run(["agent", "--version"], isolate_home=True)

    assert result.returncode == 0
    assert captured_home is not None
    assert captured_env is not None
    assert "OPENAI_API_KEY" not in captured_env
    from pathlib import Path

    assert not Path(captured_home).exists()


def test_sanitized_context_keeps_real_home_but_drops_credentials(monkeypatch):
    captured_env = None
    monkeypatch.setenv("HOME", "/home/example-user")
    monkeypatch.setenv("CODEX_HOME", "/home/example-user/.custom-codex")
    monkeypatch.setenv("OPENAI_API_KEY", "fake-value-that-must-not-reach-status")

    def capture(*args, **kwargs):
        nonlocal captured_env
        captured_env = kwargs["env"]
        return subprocess.CompletedProcess(args[0], 0, stdout="", stderr="Logged in")

    monkeypatch.setattr(subprocess, "run", capture)

    result = CommandRunner().run(["codex", "login", "status"], sanitize_env=True)

    assert result.returncode == 0
    assert captured_env is not None
    assert captured_env["HOME"] == "/home/example-user"
    assert captured_env["CODEX_HOME"] == "/home/example-user/.custom-codex"
    assert "OPENAI_API_KEY" not in captured_env
