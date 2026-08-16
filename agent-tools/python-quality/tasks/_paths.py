"""Workspace path checks for quality tasks."""

from __future__ import annotations

from pathlib import Path


def require_existing_path(path: str) -> Path:
    """Return ``path`` as a Path, or exit if it does not exist.

    Args:
        path: File or directory relative to /workspace (or cwd).

    Returns:
        The resolved Path.

    Raises:
        SystemExit: The path is missing.
    """
    target = Path(path)
    if not target.exists():
        print(f"ERROR path does not exist: {path}")
        raise SystemExit(1)
    return target
