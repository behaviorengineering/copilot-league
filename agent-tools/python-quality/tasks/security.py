"""Security audit tasks: bandit and detect-secrets."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

from invoke import task  # type: ignore[attr-defined]

from tasks._logger import error, segment, success
from tasks._run import run

if TYPE_CHECKING:
    from invoke.context import Context


def _bandit_args(path: str) -> list[str]:
    """Build bandit argv for a file or directory.

    Args:
        path: Workspace-relative file or directory.

    Returns:
        Argument list starting with ``bandit``.
    """
    target = Path(path)
    if target.is_file():
        return ["bandit", str(target)]
    return ["bandit", "-r", str(target)]


@task
def security_code(_ctx: Context, path: str = ".") -> None:
    """Run bandit. Fail on HIGH or MEDIUM findings.

    Args:
        _ctx: Invoke context (unused).
        path: File or directory relative to /workspace (default: entire workspace).
    """
    segment("Bandit")
    result = run([*_bandit_args(path), "-f", "json"], capture=True)
    try:
        data = json.loads(result.stdout or "{}")
    except json.JSONDecodeError:
        error("bandit produced invalid JSON")
        raise SystemExit(1) from None

    counts = {"high": 0, "medium": 0, "low": 0}
    for finding in data.get("results", []):
        sev = str(finding.get("issue_severity", "")).lower()
        if sev in counts:
            counts[sev] += 1

    high = counts["high"]
    medium = counts["medium"]
    low = counts["low"]
    if high or medium:
        error(f"Bandit HIGH={high} MEDIUM={medium} LOW={low}")
        raise SystemExit(1)
    success(f"Bandit clean (LOW={low})")


@task
def security_secrets(_ctx: Context, path: str = ".") -> None:
    """Run detect-secrets. Fail when any candidate is found.

    Args:
        _ctx: Invoke context (unused).
        path: File or directory relative to /workspace (default: entire workspace).
    """
    segment("detect-secrets")
    result = run(
        ["detect-secrets", "scan", path, "--exclude-files", r"\.venv|build|dist|\.egg-info"],
        capture=True,
    )
    try:
        data = json.loads(result.stdout or "{}")
    except json.JSONDecodeError:
        error("detect-secrets produced invalid JSON")
        raise SystemExit(1) from None

    count = sum(len(v) for v in data.get("results", {}).values())
    if count:
        error(f"Potential secrets: {count} finding(s)")
        raise SystemExit(1)
    success("No hardcoded secrets detected")
