"""Resolve tool config files: workspace override, then image defaults."""

from __future__ import annotations

from pathlib import Path

TOOL_DIR = Path(__file__).resolve().parent.parent


def resolve_tool_config(filename: str) -> Path:
    """Return workspace override if present, otherwise the image default.

    Args:
        filename: Config filename to resolve (e.g. ``ruff.toml``).

    Returns:
        Path to the file that should be passed to the tool.
    """
    override = Path(filename)
    if override.exists():
        return override
    return TOOL_DIR / filename
