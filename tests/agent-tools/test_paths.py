"""Unit tests for require_existing_path (no Docker)."""

from __future__ import annotations

import importlib.util
from collections.abc import Callable
from pathlib import Path
from typing import cast

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_require_existing_path() -> Callable[[str], Path]:
    """Load require_existing_path without importing the invoke collection."""
    path = REPO_ROOT / "agent-tools" / "python-quality" / "tasks" / "_paths.py"
    spec = importlib.util.spec_from_file_location("python_quality_paths", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return cast("Callable[[str], Path]", module.require_existing_path)


require_existing_path = _load_require_existing_path()


def test_require_existing_path_returns_file(tmp_path: Path) -> None:
    """An existing file is returned as a Path."""
    target = tmp_path / "ok.py"
    target.write_text("x = 1\n", encoding="utf-8")
    assert require_existing_path(str(target)) == target


def test_require_existing_path_missing_exits(tmp_path: Path) -> None:
    """A missing path is a fatal SystemExit."""
    missing = tmp_path / "nope.py"
    with pytest.raises(SystemExit) as caught:
        require_existing_path(str(missing))
    assert caught.value.code == 1
