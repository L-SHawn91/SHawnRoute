#!/usr/bin/env python3
from __future__ import annotations
import re, sys
from pathlib import Path

# Hard scanner: fail on concrete secret-looking assignments, private absolute paths, and live DB filenames.
# Boundary policy docs may mention forbidden categories in prose; that should not fail the scan.
HARD_PATTERNS = [
    re.compile(r"(?i)(api[_-]?key|secret|token)\s*[=:]\s*['\"]?[A-Za-z0-9_\-]{20,}"),
    re.compile(r"/(home|Users)/[^\s]+/(SHawn|SHide|OneDrive|Clouds)/"),
    re.compile(r"(?i)corpus\.db"),
]
SKIP_PARTS = {'.git', '.venv', 'node_modules', '__pycache__', 'dist', 'build'}

def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else '.')
    findings = []
    for path in root.rglob('*'):
        if not path.is_file() or SKIP_PARTS.intersection(path.parts):
            continue
        if path.stat().st_size > 500_000:
            continue
        text = path.read_text(errors='ignore')
        for pat in HARD_PATTERNS:
            if pat.search(text):
                findings.append((str(path.relative_to(root)), pat.pattern))
    if findings:
        for file, pattern in findings:
            print(f"PUBLIC_SAFETY_FAIL	{file}	{pattern}")
        return 1
    print('PUBLIC_SAFETY_OK')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
