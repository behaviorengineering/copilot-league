"""Radon JSON helpers — fail lint on cyclomatic rank C or worse."""

from __future__ import annotations

from typing import Any

FAIL_RANKS = frozenset({"C", "D", "E", "F"})


def rank_failures(report: object) -> list[str]:
    """Collect radon blocks whose rank is C, D, E, or F.

    Args:
        report: Parsed ``radon cc -j`` object (file path → list of blocks).

    Returns:
        Human-readable finding lines. Empty when every block is A or B.
    """
    if not isinstance(report, dict):
        return []
    failures: list[str] = []
    for path, blocks in report.items():
        if not isinstance(blocks, list):
            continue
        for block in blocks:
            if not isinstance(block, dict):
                continue
            item: dict[str, Any] = block
            rank = str(item.get("rank", "")).upper()
            if rank not in FAIL_RANKS:
                continue
            name = item.get("name", "?")
            lineno = item.get("lineno", "?")
            failures.append(f"{path}:{lineno} {name} rank={rank}")
    return failures
