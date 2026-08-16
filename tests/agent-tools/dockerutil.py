"""Docker/Podman CLI helpers for agent-tool image smoke tests."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURES = Path(__file__).resolve().parent / "fixtures"
CADDYFILE = Path(__file__).resolve().parent / "caddy" / "Caddyfile"


def docker_cli() -> str:
    """Return podman or docker when a daemon is up, otherwise skip.

    Returns:
        The engine executable name.
    """
    for binary in ("podman", "docker"):
        if shutil.which(binary) is None:
            continue
        result = subprocess.run(
            [binary, "info"],
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            return binary
    pytest.skip("neither podman nor docker daemon is running")


def tls_flags(engine: str) -> list[str]:
    """Return ``--tls-verify=false`` for Podman, else nothing.

    Args:
        engine: ``podman`` or ``docker``.

    Returns:
        Extra argv for pull/build.
    """
    if engine == "podman":
        return ["--tls-verify=false"]
    return []


def published_host_port(engine: str, name: str, container_port: int) -> int:
    """Return the host port published for a container port.

    Args:
        engine: Engine CLI name.
        name: Running container name.
        container_port: Port inside the container.

    Returns:
        Host port number.
    """
    result = run_checked([engine, "port", name, str(container_port)])
    line = result.stdout.strip().splitlines()[0]
    return int(line.rsplit(":", 1)[-1])


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
    engine: str,
    image: str,
    extra: list[str],
    workspace: Path = FIXTURES,
) -> subprocess.CompletedProcess[str]:
    """Run a one-shot tool image with a directory mounted at /workspace.

    Args:
        engine: Engine CLI name.
        image: Image tag.
        extra: Arguments after the image name.
        workspace: Host directory mounted at ``/workspace``.

    Returns:
        Completed process (caller checks returncode).
    """
    return subprocess.run(
        [
            engine,
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


def combined_output(result: subprocess.CompletedProcess[str]) -> str:
    """Join stdout and stderr for assertions.

    Args:
        result: Completed process.

    Returns:
        Combined text.
    """
    return (result.stdout or "") + (result.stderr or "")
