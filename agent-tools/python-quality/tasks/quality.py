"""Quality audit tasks: lint and format."""

from __future__ import annotations

from typing import TYPE_CHECKING

from invoke import task  # type: ignore[attr-defined]

from tasks._config import resolve_tool_config
from tasks._logger import segment, success
from tasks._run import run

if TYPE_CHECKING:
    from invoke.context import Context


@task
def format(_ctx: Context, path: str = ".") -> None:
    """Auto-fix lint issues and format with ruff.

    Args:
        _ctx: Invoke context (unused).
        path: File or directory relative to /workspace (default: entire workspace).
    """
    ruff_cfg = resolve_tool_config("ruff.toml")
    segment("Fix lint issues")
    run(["ruff", "check", "--config", str(ruff_cfg), "--fix", path])
    segment("Format code")
    run(["ruff", "format", "--config", str(ruff_cfg), path])
    success("Code formatted")


@task
def lint(_ctx: Context, path: str = ".") -> None:
    """Run ruff check, ruff format --check, mypy --strict, and radon.

    Args:
        _ctx: Invoke context (unused).
        path: File or directory relative to /workspace (default: entire workspace).
    """
    ruff_cfg = resolve_tool_config("ruff.toml")
    mypy_cfg = resolve_tool_config("mypy.ini")

    segment("Ruff lint")
    run(["ruff", "check", "--config", str(ruff_cfg), path])
    segment("Ruff format check")
    run(["ruff", "format", "--config", str(ruff_cfg), "--check", path])
    segment("Mypy type check")
    run(["mypy", "--config-file", str(mypy_cfg), "--strict", path])
    segment("Radon complexity")
    run(["radon", "cc", "-s", path])
    success("All linting checks passed")
