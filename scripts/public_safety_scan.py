#!/usr/bin/env python3
"""Fail when public source contains likely private paths or credential values."""

from __future__ import annotations

from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[1]
SKIP_PARTS = {".git", ".venv", "__pycache__", ".pytest_cache", "dist", "build"}
TEXT_SUFFIXES = {".py", ".md", ".toml", ".yaml", ".yml", ".json", ".txt", ""}

PATTERNS = {
    "private-home-path": re.compile(r"/(?:" + "home|Users" + r")/(?!example-user\b|<user>\b)[^/\s]+/"),
    "openai-shaped-secret": re.compile(r"\b" + "sk-" + r"[A-Za-z0-9_-]{8,}\b"),
    "github-shaped-secret": re.compile(r"\b" + "gh[pousr]_" + r"[A-Za-z0-9]{20,}\b"),
    "aws-shaped-key": re.compile(r"\b" + "AKIA" + r"[A-Z0-9]{16}\b"),
    "slack-shaped-secret": re.compile(r"\b" + "xox[baprs]-" + r"[A-Za-z0-9-]{16,}\b"),
    "private-key-block": re.compile(r"BEGIN " + r"(?:RSA |EC |OPENSSH )?PRIVATE KEY"),
    "credential-assignment": re.compile(
        r"(?i)\b(?:api[_-]?key|access[_-]?token|refresh[_-]?token|client[_-]?secret)\s*[=:]\s*[\"']?[A-Za-z0-9+/=_-]{20,}"
    ),
}


def iter_text_files():
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file() or any(part in SKIP_PARTS for part in path.parts):
            continue
        if path.suffix.lower() in TEXT_SUFFIXES:
            yield path


def main() -> int:
    findings = []
    for path in iter_text_files():
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for line_number, line in enumerate(text.splitlines(), start=1):
            for rule, pattern in PATTERNS.items():
                if pattern.search(line):
                    findings.append(f"{path.relative_to(ROOT)}:{line_number}: {rule}")

    if findings:
        print("Public safety scan failed:")
        print("\n".join(findings))
        return 1
    print("Public safety scan passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
