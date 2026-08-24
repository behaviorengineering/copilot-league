"""Corp-stage image smokes against a Caddy Artifactory-shaped reverse proxy."""

from __future__ import annotations

import base64
import os
import shutil
import ssl
import subprocess
import threading
import time
import urllib.error
import urllib.request
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

import pytest
import urlrewrite
from dockerutil import (
    CADDYFILE,
    REPO_ROOT,
    combined_output,
    published_host_port,
    run_checked,
    run_tool,
    tls_flags,
)

pytestmark = [pytest.mark.image, pytest.mark.corp]

_CADDY_IMAGE = "caddy:2-alpine"
_CADDY_NAME = "corp-proxy-caddy"
_CADDY_PORT = 8443
_REGISTRY_USER = "ci-user"
_REGISTRY_TOKEN = "ci-token"
_BASIC_HASH = "$2a$14$NCsZtKhEJ.3p6i3TSe3gjufBtuCQzuJCvVQu6csxVfvfqe8bpA7ei"
_PACKAGE_NAME = "artifactory.example.com"
_WAIT_SECONDS = 60
_CA_CNF = """\
[req]
distinguished_name = req_dn
x509_extensions = v3_ca
prompt = no

[req_dn]
CN = Copilot League Test CA

[v3_ca]
basicConstraints = critical,CA:TRUE
keyUsage = critical,keyCertSign,cRLSign
subjectKeyIdentifier = hash
"""

_SERVER_CNF = """\
[req]
distinguished_name = req_dn
prompt = no

[req_dn]
CN = artifactory.example.com

[v3_server]
basicConstraints = CA:FALSE
keyUsage = digitalSignature,keyEncipherment
extendedKeyUsage = serverAuth
subjectAltName = DNS:artifactory.example.com
"""

_UNVERIFIED_SSL = ssl.create_default_context()
_UNVERIFIED_SSL.check_hostname = False
_UNVERIFIED_SSL.verify_mode = ssl.CERT_NONE


@dataclass(frozen=True)
class CorpRegistry:
    """Caddy listener plus environment.md-shaped build-args."""

    package_host: str
    listen_base: str
    ca_url: str
    debian_repo_path: str
    pip_index_path: str
    npm_virtual_path: str
    username_file: Path
    token_file: Path


def _write_tls_material(cert_dir: Path) -> None:
    """Write a test CA plus a server cert Caddy presents on :8443.

    Args:
        cert_dir: Directory that receives ca.pem, cert.pem, and key.pem.
    """
    if shutil.which("openssl") is None:
        pytest.fail("openssl is required to mint the Caddy TLS material")
    ca_cnf = cert_dir / "ca.cnf"
    server_cnf = cert_dir / "server.cnf"
    ca_cnf.write_text(_CA_CNF, encoding="utf-8")
    server_cnf.write_text(_SERVER_CNF, encoding="utf-8")
    run_checked(
        [
            "openssl",
            "req",
            "-x509",
            "-newkey",
            "rsa:2048",
            "-keyout",
            str(cert_dir / "ca-key.pem"),
            "-out",
            str(cert_dir / "ca.pem"),
            "-days",
            "2",
            "-nodes",
            "-config",
            str(ca_cnf),
        ]
    )
    run_checked(
        [
            "openssl",
            "req",
            "-newkey",
            "rsa:2048",
            "-keyout",
            str(cert_dir / "key.pem"),
            "-out",
            str(cert_dir / "server.csr"),
            "-nodes",
            "-config",
            str(server_cnf),
        ]
    )
    run_checked(
        [
            "openssl",
            "x509",
            "-req",
            "-in",
            str(cert_dir / "server.csr"),
            "-CA",
            str(cert_dir / "ca.pem"),
            "-CAkey",
            str(cert_dir / "ca-key.pem"),
            "-CAcreateserial",
            "-out",
            str(cert_dir / "cert.pem"),
            "-days",
            "2",
            "-extfile",
            str(server_cnf),
            "-extensions",
            "v3_server",
        ]
    )


def _wait_for_caddy(url: str, docker: str, name: str, timeout_s: int) -> None:
    """Poll Caddy /health until it answers or time runs out.

    Args:
        url: HTTPS health URL on the host.
        docker: Docker CLI name.
        name: Caddy container name.
        timeout_s: Seconds to wait.

    Raises:
        pytest.fail: Caddy did not become ready.
    """
    deadline = time.monotonic() + timeout_s
    last_error = "no attempt"
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(
                url, timeout=3, context=_UNVERIFIED_SSL
            ) as response:
                if response.status == 200:
                    return
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last_error = str(exc)
        time.sleep(1)
    logs = subprocess.run(
        [docker, "logs", name],
        check=False,
        capture_output=True,
        text=True,
    )
    pytest.fail(f"Caddy not ready at {url}: {last_error}\n{logs.stdout}\n{logs.stderr}")


def _caddy_logs(docker: str) -> str:
    """Return combined stdout/stderr from the Caddy container.

    Args:
        docker: Docker CLI name.

    Returns:
        Log text (JSON access logs plus any errors).
    """
    result = subprocess.run(
        [docker, "logs", _CADDY_NAME],
        check=False,
        capture_output=True,
        text=True,
    )
    return (result.stdout or "") + (result.stderr or "")


def _corp_build_flags(docker: str, registry: CorpRegistry) -> list[str]:
    """Docker build flags that point RUN at the Caddy double.

    Args:
        docker: Engine CLI name.
        registry: Live Caddy connection details.

    Returns:
        Argument list to splice after ``docker build``.
    """
    flags = [
        "--no-cache",
        *tls_flags(docker),
        "--add-host",
        f"{_PACKAGE_NAME}:host-gateway",
    ]
    flags.extend(
        [
            "--build-arg",
            f"PACKAGE_REGISTRY_HOST={registry.package_host}",
            "--build-arg",
            f"CORP_CA_CERT_URL={registry.ca_url}",
            "--build-arg",
            f"DEBIAN_REPO_PATH={registry.debian_repo_path}",
            "--build-arg",
            f"PIP_INDEX_PATH={registry.pip_index_path}",
            "--build-arg",
            f"NPM_VIRTUAL_PATH={registry.npm_virtual_path}",
            "--secret",
            f"id=username,src={registry.username_file}",
            "--secret",
            f"id=token,src={registry.token_file}",
        ]
    )
    return flags


@pytest.fixture(scope="session")
def corp_registry(
    docker: str, tmp_path_factory: pytest.TempPathFactory
) -> Iterator[CorpRegistry]:
    """Start Caddy on container :8443 (ephemeral host port) and a URL rewriter."""
    secrets = tmp_path_factory.mktemp("corp-secrets")
    username_file = secrets / "username"
    token_file = secrets / "token"
    username_file.write_text(_REGISTRY_USER, encoding="utf-8")
    token_file.write_text(_REGISTRY_TOKEN, encoding="utf-8")
    cert_dir = tmp_path_factory.mktemp("corp-tls")
    _write_tls_material(cert_dir)

    rewriter = urlrewrite.serve(0)
    rewrite_port = rewriter.server_address[1]
    rewrite_thread = threading.Thread(target=rewriter.serve_forever, daemon=True)
    rewrite_thread.start()

    subprocess.run([docker, "rm", "-f", _CADDY_NAME], check=False, capture_output=True)
    run_checked([docker, "pull", *tls_flags(docker), _CADDY_IMAGE])
    run_checked(
        [
            docker,
            "run",
            "-d",
            "--name",
            _CADDY_NAME,
            "-p",
            str(_CADDY_PORT),
            "--add-host",
            "host.docker.internal:host-gateway",
            "-e",
            f"CORP_BASIC_HASH={_BASIC_HASH}",
            "-e",
            f"REWRITE_UPSTREAM=http://host.docker.internal:{rewrite_port}",
            "-v",
            f"{CADDYFILE}:/etc/caddy/Caddyfile:ro",
            "-v",
            f"{cert_dir}:/certs:ro",
            _CADDY_IMAGE,
        ]
    )
    try:
        host_port = published_host_port(docker, _CADDY_NAME, _CADDY_PORT)
        os.environ["REWRITE_PUBLIC_ORIGIN"] = f"https://{_PACKAGE_NAME}:{host_port}"
        _wait_for_caddy(
            f"https://127.0.0.1:{host_port}/health",
            docker,
            _CADDY_NAME,
            _WAIT_SECONDS,
        )
        package_host = f"{_PACKAGE_NAME}:{host_port}"
        listen_base = f"https://127.0.0.1:{host_port}"
        yield CorpRegistry(
            package_host=package_host,
            listen_base=listen_base,
            ca_url=(
                f"https://{package_host}"
                "/artifactory/generic/security/certificates/corp-ca.pem"
            ),
            debian_repo_path="artifactory/debian-repo",
            pip_index_path="artifactory/api/pypi/pypi-virtual/simple",
            npm_virtual_path="artifactory/api/npm/npm-virtual/",
            username_file=username_file,
            token_file=token_file,
        )
    finally:
        subprocess.run(
            [docker, "rm", "-f", _CADDY_NAME],
            check=False,
            capture_output=True,
        )
        rewriter.shutdown()


@pytest.fixture(scope="session")
def corp_base_image(docker: str, corp_registry: CorpRegistry) -> str:
    """Build local-agent-tool-base through Caddy (CA + apt)."""
    tag = "local-agent-tool-base"
    run_checked(
        [
            docker,
            "build",
            *_corp_build_flags(docker, corp_registry),
            "-t",
            tag,
            str(REPO_ROOT / "agent-tools" / "base"),
        ]
    )
    return tag


def test_corp_base_sets_ca_bundle(docker: str, corp_base_image: str) -> None:
    """Base image exports REQUESTS_CA_BUNDLE after installing the corp CA."""
    result = subprocess.run(
        [
            docker,
            "run",
            "--rm",
            "--entrypoint",
            "printenv",
            corp_base_image,
            "REQUESTS_CA_BUNDLE",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.strip() == "/etc/ssl/certs/ca-certificates.crt"


@pytest.fixture(scope="session")
def python_quality_corp_image(docker: str, corp_registry: CorpRegistry) -> str:
    """Build python-quality --target corp through Caddy (CA + pip)."""
    tag = "python-quality:corp-smoke"
    run_checked(
        [
            docker,
            "build",
            "--target",
            "corp",
            *_corp_build_flags(docker, corp_registry),
            "-t",
            tag,
            str(REPO_ROOT / "agent-tools" / "python-quality"),
        ]
    )
    return tag


@pytest.fixture(scope="session")
def groovy_lint_corp_image(docker: str, corp_registry: CorpRegistry) -> str:
    """Build groovy-lint --target corp through Caddy (CA + apt JRE + npm)."""
    tag = "groovy-lint:corp-smoke"
    run_checked(
        [
            docker,
            "build",
            "--target",
            "corp",
            *_corp_build_flags(docker, corp_registry),
            "-t",
            tag,
            str(REPO_ROOT / "agent-tools" / "groovy-lint"),
        ]
    )
    return tag


def test_corp_proxy_serves_ca_without_auth(corp_registry: CorpRegistry) -> None:
    """CORP_CA_CERT_URL is reachable without basic auth and looks like PEM."""
    url = (
        f"{corp_registry.listen_base}"
        "/artifactory/generic/security/certificates/corp-ca.pem"
    )
    with urllib.request.urlopen(url, timeout=10, context=_UNVERIFIED_SSL) as response:
        body = response.read().decode("utf-8")
    assert "BEGIN CERTIFICATE" in body


def test_corp_proxy_rejects_unauthenticated_pip(corp_registry: CorpRegistry) -> None:
    """The pip simple prefix requires basic auth."""
    url = f"{corp_registry.listen_base}/{corp_registry.pip_index_path}/"
    with pytest.raises(urllib.error.HTTPError) as caught:
        urllib.request.urlopen(url, timeout=10, context=_UNVERIFIED_SSL)
    assert caught.value.code == 401


def test_corp_proxy_accepts_basic_auth(corp_registry: CorpRegistry) -> None:
    """ci-user:ci-token is accepted on a proxied PyPI simple URL."""
    url = f"{corp_registry.listen_base}/{corp_registry.pip_index_path}/invoke/"
    request = urllib.request.Request(url)
    token = base64.b64encode(f"{_REGISTRY_USER}:{_REGISTRY_TOKEN}".encode()).decode(
        "ascii"
    )
    request.add_header("Authorization", f"Basic {token}")
    with urllib.request.urlopen(
        request, timeout=30, context=_UNVERIFIED_SSL
    ) as response:
        assert response.status == 200


def test_python_quality_corp_python_is_3_12(
    docker: str, python_quality_corp_image: str
) -> None:
    """Corp image interpreter is Python 3.12, matching public."""
    result = subprocess.run(
        [
            docker,
            "run",
            "--rm",
            "--entrypoint",
            "python3",
            python_quality_corp_image,
            "--version",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.strip().startswith("Python 3.12")


def test_python_quality_corp_lint_passes(
    docker: str, python_quality_corp_image: str
) -> None:
    """Corp python-quality lint exits 0 on the typed fixture."""
    result = run_tool(
        docker,
        python_quality_corp_image,
        ["lint", "--path", "/workspace/ok.py"],
    )
    assert result.returncode == 0, combined_output(result)


def test_python_quality_corp_format_runs(
    docker: str, python_quality_corp_image: str, tmp_path: Path
) -> None:
    """Corp format rewrites an ugly file."""
    ugly = tmp_path / "ugly.py"
    ugly.write_text("x=1\n", encoding="utf-8")
    result = run_tool(
        docker,
        python_quality_corp_image,
        ["format", "--path", "/workspace/ugly.py"],
        workspace=tmp_path,
    )
    assert result.returncode == 0, combined_output(result)
    assert ugly.read_text(encoding="utf-8") != "x=1\n"


def test_python_quality_corp_sec_code_passes(
    docker: str, python_quality_corp_image: str
) -> None:
    """Corp sec.code exits 0 on the typed fixture."""
    result = run_tool(
        docker,
        python_quality_corp_image,
        ["sec.code", "--path", "/workspace/ok.py"],
    )
    assert result.returncode == 0, combined_output(result)


def test_python_quality_corp_sec_secrets_passes(
    docker: str, python_quality_corp_image: str
) -> None:
    """Corp sec.secrets exits 0 when detect-secrets finds nothing."""
    result = run_tool(
        docker,
        python_quality_corp_image,
        ["sec.secrets", "--path", "/workspace/ok.py"],
    )
    assert result.returncode == 0, combined_output(result)


def test_python_quality_corp_lint_fails_on_untyped_file(
    docker: str, python_quality_corp_image: str
) -> None:
    """Corp lint exits non-zero when mypy --strict fails."""
    result = run_tool(
        docker,
        python_quality_corp_image,
        ["lint", "--path", "/workspace/bad.py"],
    )
    assert result.returncode != 0
    assert "mypy" in combined_output(result).lower()


def test_python_quality_corp_lint_fails_on_complex_fixture(
    docker: str, python_quality_corp_image: str
) -> None:
    """Corp lint exits non-zero when radon reports rank C or worse."""
    result = run_tool(
        docker,
        python_quality_corp_image,
        ["lint", "--path", "/workspace/complex_fail.py"],
    )
    assert result.returncode != 0
    assert "rank=" in combined_output(result)


def test_python_quality_corp_sec_code_fails_on_eval(
    docker: str, python_quality_corp_image: str
) -> None:
    """Corp sec.code exits non-zero when bandit finds HIGH/MEDIUM issues."""
    result = run_tool(
        docker,
        python_quality_corp_image,
        ["sec.code", "--path", "/workspace/bandit_fail.py"],
    )
    assert result.returncode != 0
    assert "Bandit" in combined_output(result)


def test_python_quality_corp_sec_secrets_fails_on_example_key(
    docker: str, python_quality_corp_image: str
) -> None:
    """Corp sec.secrets exits non-zero on AWS's published example access key."""
    result = run_tool(
        docker,
        python_quality_corp_image,
        ["sec.secrets", "--path", "/workspace/secret_fail.py"],
    )
    assert result.returncode != 0
    assert "secret" in combined_output(result).lower()


def test_groovy_lint_corp_runs(docker: str, groovy_lint_corp_image: str) -> None:
    """Corp groovy-lint processes the Groovy fixture."""
    result = run_tool(
        docker,
        groovy_lint_corp_image,
        [
            "/workspace/ok.groovy",
            "--no-insight",
            "--failon",
            "error",
        ],
    )
    output = combined_output(result)
    assert "bad.groovy" not in output, output
    assert result.returncode == 0, output


def test_groovy_lint_corp_fails_on_bad_fixture(
    docker: str, groovy_lint_corp_image: str
) -> None:
    """Corp npm-groovy-lint exits non-zero on a parse error."""
    result = run_tool(
        docker,
        groovy_lint_corp_image,
        [
            "/workspace/bad.groovy",
            "--no-insight",
            "--failon",
            "error",
        ],
    )
    assert result.returncode != 0
    output = combined_output(result).lower()
    assert "error" in output or "fail" in output


def test_python_quality_corp_wheels_go_through_caddy(
    docker: str, python_quality_corp_image: str
) -> None:
    """pip downloaded wheels via /pypi-files on the Caddy vhost."""
    logs = _caddy_logs(docker)
    assert "/pypi-files" in logs or ".whl" in logs, logs


def test_groovy_lint_corp_tarballs_go_through_caddy(
    docker: str, groovy_lint_corp_image: str
) -> None:
    """npm downloaded tarballs via /npm-tarballs on the Caddy vhost."""
    logs = _caddy_logs(docker)
    assert "/npm-tarballs" in logs or ".tgz" in logs, logs
