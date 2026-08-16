"""Unit tests for bandit argv construction (no Docker)."""

from __future__ import annotations

import importlib.util
from collections.abc import Callable
from pathlib import Path
from typing import cast

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_bandit_args() -> Callable[[str], list[str]]:
    """Load bandit_args without importing the invoke collection."""
    path = REPO_ROOT / "agent-tools" / "python-quality" / "tasks" / "_bandit.py"
    spec = importlib.util.spec_from_file_location("python_quality_bandit", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return cast("Callable[[str], list[str]]", module.bandit_args)


bandit_args = _load_bandit_args()


def test_bandit_args_file_omits_recursive(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A file target is passed as-is, without ``-r``."""
    target = tmp_path / "ok.py"
    target.write_text("x = 1\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    assert bandit_args("ok.py") == ["bandit", "ok.py"]


def test_bandit_args_directory_is_recursive(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A directory target gets ``-r``."""
    (tmp_path / "pkg").mkdir()
    monkeypatch.chdir(tmp_path)
    assert bandit_args("pkg") == ["bandit", "-r", "pkg"]
