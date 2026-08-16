"""Build public agent-tool images and smoke-run each tool."""

from __future__ import annotations

import subprocess
import time
import urllib.error
import urllib.request
from collections.abc import Iterator
from pathlib import Path

import pytest
from dockerutil import FIXTURES, REPO_ROOT, run_checked, run_tool

pytestmark = pytest.mark.image

_JENKINS_CONTAINER_PORT = 8080
_JENKINS_WAIT_SECONDS = 300


@pytest.fixture(scope="session")
def python_quality_image(docker: str) -> str:
    """Build the public python-quality image."""
    tag = "python-quality:smoke"
    run_checked(
        [
            docker,
            "build",
            "--target",
            "public",
            "-t",
            tag,
            str(REPO_ROOT / "agent-tools" / "python-quality"),
        ]
    )
    return tag


@pytest.fixture(scope="session")
def groovy_lint_image(docker: str) -> str:
    """Build the public groovy-lint image."""
    tag = "groovy-lint:smoke"
    run_checked(
        [
            docker,
            "build",
            "--target",
            "public",
            "-t",
            tag,
            str(REPO_ROOT / "agent-tools" / "groovy-lint"),
        ]
    )
    return tag


@pytest.fixture(scope="session")
def jenkins_validator_image(docker: str) -> str:
    """Build the jenkins-validator image from Docker Hub Jenkins."""
    tag = "jenkins-validator:smoke"
    run_checked(
        [
            docker,
            "build",
            "-t",
            tag,
            str(REPO_ROOT / "agent-tools" / "jenkins-validator"),
        ]
    )
    return tag


def test_python_quality_lint_passes_on_ok_file(
    docker: str, python_quality_image: str
) -> None:
    """lint exits 0 on a fully typed fixture."""
    result = run_tool(
        docker,
        python_quality_image,
        ["lint", "--path", "/workspace/ok.py"],
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_python_quality_lint_fails_on_untyped_file(
    docker: str, python_quality_image: str
) -> None:
    """lint exits non-zero when mypy --strict fails."""
    result = run_tool(
        docker,
        python_quality_image,
        ["lint", "--path", "/workspace/bad.py"],
    )
    assert result.returncode != 0


def test_python_quality_format_runs(
    docker: str, python_quality_image: str, tmp_path: Path
) -> None:
    """format starts ruff fix/format on a copy so fixtures stay unchanged."""
    (tmp_path / "ok.py").write_text(
        (FIXTURES / "ok.py").read_text(encoding="utf-8"), encoding="utf-8"
    )
    result = run_tool(
        docker,
        python_quality_image,
        ["format", "--path", "/workspace/ok.py"],
        workspace=tmp_path,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_python_quality_sec_code_passes_on_ok_file(
    docker: str, python_quality_image: str
) -> None:
    """sec.code exits 0 when bandit finds no HIGH/MEDIUM issues."""
    result = run_tool(
        docker,
        python_quality_image,
        ["sec.code", "--path", "/workspace/ok.py"],
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_python_quality_sec_secrets_passes_on_ok_file(
    docker: str, python_quality_image: str
) -> None:
    """sec.secrets exits 0 when detect-secrets finds nothing."""
    result = run_tool(
        docker,
        python_quality_image,
        ["sec.secrets", "--path", "/workspace/ok.py"],
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_groovy_lint_runs_on_fixture(docker: str, groovy_lint_image: str) -> None:
    """npm-groovy-lint starts and processes a tiny Groovy file."""
    result = run_tool(
        docker,
        groovy_lint_image,
        [
            "--path",
            "/workspace",
            "--files",
            "ok.groovy",
            "--no-insight",
            "--failon",
            "error",
        ],
    )
    assert result.returncode == 0, result.stdout + result.stderr


def _jenkins_api_ready(url: str) -> bool:
    """Return True when Jenkins ``/api/json`` returns JSON, not the boot page.

    Args:
        url: Absolute ``/api/json`` URL.

    Returns:
        True if Jenkins has finished booting.
    """
    try:
        with urllib.request.urlopen(url, timeout=3) as response:
            body = response.read(500).decode("utf-8", errors="replace")
    except (urllib.error.URLError, TimeoutError, OSError):
        return False
    return body.lstrip().startswith("{")


def _published_host_port(docker: str, name: str, container_port: int) -> int:
    """Return the host port Docker published for a container port.

    Args:
        docker: Docker CLI name.
        name: Running container name.
        container_port: Port inside the container.

    Returns:
        Host port number.
    """
    result = run_checked([docker, "port", name, str(container_port)])
    line = result.stdout.strip().splitlines()[0]
    return int(line.rsplit(":", 1)[-1])


def _wait_for_jenkins(docker: str, name: str, host_port: int, timeout_s: int) -> None:
    """Poll until Jenkins ``/api/json`` returns JSON.

    Args:
        docker: Docker CLI name.
        name: Running container name (for logs on timeout).
        host_port: Published host port for Jenkins HTTP.
        timeout_s: Seconds to wait.

    Raises:
        pytest.fail: Jenkins did not become ready.
    """
    url = f"http://127.0.0.1:{host_port}/api/json"
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if _jenkins_api_ready(url):
            return
        time.sleep(3)
    logs = subprocess.run(
        [docker, "logs", name],
        check=False,
        capture_output=True,
        text=True,
    )
    pytest.fail(f"Jenkins not ready at {url}\n{logs.stdout}\n{logs.stderr}")


def _validate_jenkinsfile(jenkinsfile: Path, host_port: int) -> str:
    """POST a Jenkinsfile to the local validator.

    Args:
        jenkinsfile: Path to the Jenkinsfile on the host.
        host_port: Published host port for Jenkins HTTP.

    Returns:
        Response body text.
    """
    result = subprocess.run(
        [
            "curl",
            "-sS",
            "-X",
            "POST",
            f"http://127.0.0.1:{host_port}/pipeline-model-converter/validate",
            "-F",
            f"jenkinsfile=<{jenkinsfile}",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        pytest.fail(result.stdout + result.stderr)
    return result.stdout


@pytest.fixture(scope="session")
def jenkins_validator_up(docker: str, jenkins_validator_image: str) -> Iterator[int]:
    """Start jenkins-validator once and yield its published host port."""
    name = "jenkins-validator-smoke"
    subprocess.run([docker, "rm", "-f", name], check=False, capture_output=True)
    try:
        run_checked(
            [
                docker,
                "run",
                "-d",
                "--rm",
                "--name",
                name,
                "-p",
                str(_JENKINS_CONTAINER_PORT),
                jenkins_validator_image,
            ]
        )
        host_port = _published_host_port(docker, name, _JENKINS_CONTAINER_PORT)
        _wait_for_jenkins(docker, name, host_port, _JENKINS_WAIT_SECONDS)
        yield host_port
    finally:
        subprocess.run([docker, "rm", "-f", name], check=False, capture_output=True)


def _converter_result(body: str) -> str:
    """Classify converter output from JSON or plain-text plugin responses.

    Args:
        body: HTTP response text.

    Returns:
        ``success`` or ``failure``.
    """
    compact = body.replace(" ", "").replace("\n", "")
    if '"result":"success"' in compact:
        return "success"
    if '"result":"failure"' in compact:
        return "failure"
    lower = body.lower()
    if "successfully validated" in lower:
        return "success"
    if "errors encountered" in lower:
        return "failure"
    pytest.fail(f"unexpected converter body: {body}")


def test_jenkins_validator_accepts_valid_pipeline(
    jenkins_validator_up: int,
) -> None:
    """Declarative converter reports success for a valid Jenkinsfile."""
    body = _validate_jenkinsfile(FIXTURES / "ok.Jenkinsfile", jenkins_validator_up)
    assert _converter_result(body) == "success"


def test_jenkins_validator_rejects_invalid_pipeline(
    jenkins_validator_up: int,
) -> None:
    """Missing agent fails structural validation."""
    body = _validate_jenkinsfile(FIXTURES / "bad.Jenkinsfile", jenkins_validator_up)
    assert _converter_result(body) == "failure"
