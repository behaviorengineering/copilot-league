"""Unit tests for radon rank-C+ failure collection (no Docker)."""

from __future__ import annotations

import importlib.util
from collections.abc import Callable
from pathlib import Path
from typing import cast

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_rank_failures() -> Callable[[object], list[str]]:
    """Load rank_failures without importing the invoke collection."""
    path = REPO_ROOT / "agent-tools" / "python-quality" / "tasks" / "_radon.py"
    spec = importlib.util.spec_from_file_location("python_quality_radon", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return cast("Callable[[object], list[str]]", module.rank_failures)


rank_failures = _load_rank_failures()


def test_rank_failures_empty_on_a_and_b() -> None:
    """Ranks A and B are allowed."""
    report = {
        "ok.py": [
            {"name": "ping", "lineno": 1, "rank": "A"},
            {"name": "pong", "lineno": 8, "rank": "B"},
        ]
    }
    assert rank_failures(report) == []


def test_rank_failures_collects_c_and_worse() -> None:
    """Ranks C-F become finding lines."""
    report = {
        "a.py": [{"name": "big", "lineno": 4, "rank": "C"}],
        "b.py": [{"name": "huge", "lineno": 12, "rank": "F"}],
    }
    findings = rank_failures(report)
    assert "a.py:4 big rank=C" in findings
    assert "b.py:12 huge rank=F" in findings


def test_rank_failures_ignores_malformed_report() -> None:
    """Non-dict JSON and non-list values produce no findings."""
    assert rank_failures([]) == []
    assert rank_failures({"x.py": "nope"}) == []
    assert rank_failures({"x.py": [{"name": "z"}]}) == []
