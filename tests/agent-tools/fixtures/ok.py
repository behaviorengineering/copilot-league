"""Smoke fixture that must pass ruff, mypy --strict, and radon."""


def add(left: int, right: int) -> int:
    """Return the sum of two integers.

    Args:
        left: First addend.
        right: Second addend.

    Returns:
        Sum of left and right.
    """
    return left + right
