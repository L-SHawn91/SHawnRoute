"""Adapter contracts."""

from __future__ import annotations

from typing import Protocol

from shawnroute.models import RuntimeInfo


class RuntimeAdapter(Protocol):
    def detect(self) -> RuntimeInfo: ...

    def inventory(self) -> RuntimeInfo: ...
