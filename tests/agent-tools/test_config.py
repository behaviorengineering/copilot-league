"""Unit tests for python-quality config resolution (no Docker)."""

from __future__ import annotations

import importlib.util
from collections.abc import Callable
from pathlib import Path
from typing import cast

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_resolve_tool_config() -> Callable[[str], Path]:
    """Load resolve_tool_config without importing the invoke collection."""
    path = REPO_ROOT / "agent-tools" / "python-quality" / "tasks" / "_config.py"
    spec = importlib.util.spec_from_file_location("python_quality_config", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return cast("Callable[[str], Path]", module.resolve_tool_config)


resolve_tool_config = _load_resolve_tool_config()


def test_resolve_tool_config_prefers_workspace_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A ruff.toml in cwd wins over the image default."""
    override = tmp_path / "ruff.toml"
    override.write_text("line-length = 100\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    resolved = resolve_tool_config("ruff.toml")
    assert resolved.resolve() == override.resolve()


def test_resolve_tool_config_falls_back_to_image_default(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Missing workspace file uses the copy next to tasks/."""
    monkeypatch.chdir(tmp_path)
    resolved = resolve_tool_config("ruff.toml")
    expected = REPO_ROOT / "agent-tools" / "python-quality" / "ruff.toml"
    assert resolved.resolve() == expected.resolve()
