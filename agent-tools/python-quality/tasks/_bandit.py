"""Bandit argv helpers — file vs recursive directory."""

from __future__ import annotations

from pathlib import Path


def bandit_args(path: str) -> list[str]:
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
