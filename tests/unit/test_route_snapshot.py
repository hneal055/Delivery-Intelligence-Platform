"""
Route snapshot: every `METHOD /path` the API exposes, compared with
tests/unit/route_snapshot.txt. Fails on any added, removed or moved route
so URL changes are always deliberate and reviewed.

After an intended change, regenerate the snapshot and review the diff:
    UPDATE_ROUTE_SNAPSHOT=1 pytest tests/unit/test_route_snapshot.py
"""
import os
from pathlib import Path

from src.backend.api.main import app

SNAPSHOT = Path(__file__).with_name("route_snapshot.txt")


def _current_routes() -> list[str]:
    paths = app.openapi()["paths"]
    return sorted(f"{method.upper()} {path}" for path, ops in paths.items() for method in ops)


def test_routes_match_snapshot():
    current = _current_routes()

    if os.getenv("UPDATE_ROUTE_SNAPSHOT") == "1":
        SNAPSHOT.write_text("\n".join(current) + "\n", encoding="utf-8")

    lines = SNAPSHOT.read_text(encoding="utf-8").splitlines()
    expected = [line.strip() for line in lines if line.strip()]

    added = sorted(set(current) - set(expected))
    removed = sorted(set(expected) - set(current))
    assert not added and not removed, (
        "API routes changed.\n"
        f"Added:   {added}\n"
        f"Removed: {removed}\n"
        "If intended, regenerate with UPDATE_ROUTE_SNAPSHOT=1 and review the diff."
    )
