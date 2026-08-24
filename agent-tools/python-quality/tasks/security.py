"""Security audit tasks: bandit and detect-secrets."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from invoke import task  # type: ignore[attr-defined]

from tasks._bandit import bandit_args
from tasks._bandit_report import bandit_has_errors
from tasks._logger import error, segment, success
from tasks._paths import require_existing_path
from tasks._run import run
from tasks._secrets import DETECT_SECRETS_EXCLUDE

if TYPE_CHECKING:
    from invoke.context import Context

_BANDIT_OK_CODES = frozenset({0, 1})


@task
def security_code(_ctx: Context, path: str = ".") -> None:
    """Run bandit. Fail on HIGH or MEDIUM findings.

    Args:
        _ctx: Invoke context (unused).
        path: File or directory relative to /workspace (default: entire workspace).
    """
    require_existing_path(path)
    segment("Bandit")
    result = run([*bandit_args(path), "-f", "json"], capture=True)
    if result.returncode not in _BANDIT_OK_CODES:
        error("bandit exited with an unexpected status")
        raise SystemExit(result.returncode or 1)
    try:
        data = json.loads(result.stdout or "{}")
    except json.JSONDecodeError:
        error("bandit produced invalid JSON")
        raise SystemExit(1) from None

    if bandit_has_errors(data):
        error(f"Bandit errors: {data.get('errors')}")
        raise SystemExit(1)

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
    require_existing_path(path)
    segment("detect-secrets")
    result = run(
        [
            "detect-secrets",
            "scan",
            path,
            "--exclude-files",
            DETECT_SECRETS_EXCLUDE,
        ],
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
