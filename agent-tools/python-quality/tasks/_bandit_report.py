"""Helpers for asserting bandit JSON error handling (no Docker)."""

from __future__ import annotations


def bandit_has_errors(report: object) -> bool:
    """Return True when bandit JSON lists filesystem or parse errors.

    Args:
        report: Parsed ``bandit -f json`` object.

    Returns:
        True when ``errors`` is a non-empty list.
    """
    if not isinstance(report, dict):
        return False
    errors = report.get("errors")
    return bool(errors)
