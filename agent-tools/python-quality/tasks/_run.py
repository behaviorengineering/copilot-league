"""Run PATH tools and fail the task on non-zero exit."""

from __future__ import annotations

import subprocess
import sys


def run(cmd: list[str], *, capture: bool = False) -> subprocess.CompletedProcess[str]:
    """Run ``cmd`` and exit the process if the tool fails.

    Args:
        cmd: Argument vector (no shell).
        capture: When True, capture stdout/stderr instead of inheriting.

    Returns:
        Completed process when the tool exits 0 (or when capture is True even on
        non-zero, so callers can inspect output).

    Raises:
        SystemExit: Tool exited non-zero and capture is False.
    """
    result = subprocess.run(
        cmd,
        check=False,
        capture_output=capture,
        text=True,
    )
    if capture:
        if result.stdout:
            sys.stdout.write(result.stdout)
        if result.stderr:
            sys.stderr.write(result.stderr)
        return result
    if result.returncode != 0:
        raise SystemExit(result.returncode)
    return result
