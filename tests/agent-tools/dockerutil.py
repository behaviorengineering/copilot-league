"""Docker CLI helpers for agent-tool image smoke tests."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURES = Path(__file__).resolve().parent / "fixtures"
CADDYFILE = Path(__file__).resolve().parent / "caddy" / "Caddyfile"


def docker_cli() -> str:
    """Return ``docker`` if the daemon is up, otherwise skip the test.

    Returns:
        The docker executable name.
    """
    if shutil.which("docker") is None:
        pytest.skip("docker binary not on PATH")
    result = subprocess.run(
        ["docker", "info"],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        pytest.skip("docker daemon is not running")
    return "docker"


def run_checked(
    args: list[str], *, cwd: Path | None = None
) -> subprocess.CompletedProcess[str]:
    """Run a command and fail the test with combined output on error.

    Args:
        args: Argument vector.
        cwd: Optional working directory.

    Returns:
        Completed process on exit code 0.

    Raises:
        pytest.fail: Command exited non-zero.
    """
    result = subprocess.run(
        args,
        check=False,
        capture_output=True,
        text=True,
        cwd=cwd,
    )
    if result.returncode != 0:
        combined = (result.stdout or "") + (result.stderr or "")
        pytest.fail(f"{args!r} exited {result.returncode}\n{combined}")
    return result


def run_tool(
    docker: str,
    image: str,
    extra: list[str],
    workspace: Path = FIXTURES,
) -> subprocess.CompletedProcess[str]:
    """Run a one-shot tool image with a directory mounted at /workspace.

    Args:
        docker: Docker CLI name.
        image: Image tag.
        extra: Arguments after the image name.
        workspace: Host directory mounted at ``/workspace``.

    Returns:
        Completed process (caller checks returncode).
    """
    return subprocess.run(
        [
            docker,
            "run",
            "--rm",
            "-v",
            f"{workspace}:/workspace",
            image,
            *extra,
        ],
        check=False,
        capture_output=True,
        text=True,
    )
