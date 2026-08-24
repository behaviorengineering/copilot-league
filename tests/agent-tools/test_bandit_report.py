"""Unit tests for bandit JSON error detection (no Docker)."""

from __future__ import annotations

import importlib.util
from collections.abc import Callable
from pathlib import Path
from typing import cast

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_bandit_has_errors() -> Callable[[object], bool]:
    """Load bandit_has_errors without importing invoke."""
    path = REPO_ROOT / "agent-tools" / "python-quality" / "tasks" / "_bandit_report.py"
    spec = importlib.util.spec_from_file_location("python_quality_bandit_report", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return cast("Callable[[object], bool]", module.bandit_has_errors)


bandit_has_errors = _load_bandit_has_errors()


def test_bandit_has_errors_false_on_clean_results() -> None:
    """Empty errors with empty results is not a tool failure."""
    assert bandit_has_errors({"results": [], "errors": []}) is False


def test_bandit_has_errors_true_on_filesystem_error() -> None:
    """Missing-path errors must not look like a clean scan."""
    assert (
        bandit_has_errors({"results": [], "errors": [{"filename": "nope.py"}]}) is True
    )


def test_bandit_has_errors_ignores_malformed() -> None:
    """Non-dict reports have no errors list."""
    assert bandit_has_errors([]) is False
    assert bandit_has_errors({"results": []}) is False
