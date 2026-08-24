"""Minimal task logging."""

from __future__ import annotations


def segment(title: str) -> None:
    """Print a section header for a tool step.

    Args:
        title: Header text.
    """
    print(f"==> {title}")


def success(message: str) -> None:
    """Print a success line.

    Args:
        message: Success text.
    """
    print(f"OK {message}")


def error(message: str) -> None:
    """Print an error line.

    Args:
        message: Error text.
    """
    print(f"ERROR {message}")
