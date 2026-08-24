"""Smoke fixture that must fail bandit (HIGH/MEDIUM)."""


def run(cmd: str) -> None:
    """Execute a string. Bandit flags eval as HIGH.

    Args:
        cmd: Python source to evaluate.
    """
    eval(cmd)
