from __future__ import annotations
from dataclasses import dataclass, asdict

@dataclass
class RouteDecision:
    task: str
    route: str
    dry_run: bool = True
    approval_required: bool = True
    reason: str = "public mock route"

def explain(task: str) -> dict:
    t=task.lower()
    route = "search-lite" if "search" in t or "paper" in t else "sync-lite" if "manifest" in t else "human-approval"
    return asdict(RouteDecision(task=task, route=route))
