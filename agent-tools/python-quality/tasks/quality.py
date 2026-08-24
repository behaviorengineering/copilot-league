"""Quality audit tasks: lint and format."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from invoke import task  # type: ignore[attr-defined]

from tasks._config import resolve_tool_config
from tasks._logger import error, segment, success
from tasks._paths import require_existing_path
from tasks._radon import rank_failures
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
    require_existing_path(path)
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
    require_existing_path(path)
    ruff_cfg = resolve_tool_config("ruff.toml")
    mypy_cfg = resolve_tool_config("mypy.ini")

    segment("Ruff lint")
    run(["ruff", "check", "--config", str(ruff_cfg), path])
    segment("Ruff format check")
    run(["ruff", "format", "--config", str(ruff_cfg), "--check", path])
    segment("Mypy type check")
    run(["mypy", "--config-file", str(mypy_cfg), "--strict", path])
    segment("Radon complexity")
    json_result = run(["radon", "cc", "-j", "-s", path], capture=True)
    if json_result.returncode not in (0, 1):
        error("radon exited with an unexpected status")
        raise SystemExit(json_result.returncode)
    try:
        report = json.loads(json_result.stdout or "{}")
    except json.JSONDecodeError:
        error("radon produced invalid JSON")
        raise SystemExit(1) from None
    failures = rank_failures(report)
    if failures:
        error("Radon rank C+ findings:\n" + "\n".join(failures))
        raise SystemExit(1)
    success("All linting checks passed")
