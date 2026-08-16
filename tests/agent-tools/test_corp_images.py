"""Corp-stage image smokes against a Caddy Artifactory-shaped reverse proxy."""

from __future__ import annotations

import base64
import shutil
import ssl
import subprocess
import time
import urllib.error
import urllib.request
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

import pytest
from dockerutil import CADDYFILE, REPO_ROOT, run_checked, run_tool

pytestmark = [pytest.mark.image, pytest.mark.corp]

_CADDY_IMAGE = "caddy:2-alpine"
_CADDY_NAME = "corp-proxy-caddy"
_LISTEN_PORT = 8443
_REGISTRY_USER = "ci-user"
_REGISTRY_TOKEN = "ci-token"
_BASIC_HASH = "$2a$14$NCsZtKhEJ.3p6i3TSe3gjufBtuCQzuJCvVQu6csxVfvfqe8bpA7ei"
_PACKAGE_NAME = "artifactory.example.com"
_CDN_HOSTS = ("files.pythonhosted.org", "registry.npmjs.org")
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
subjectAltName = DNS:artifactory.example.com, DNS:files.pythonhosted.org, DNS:registry.npmjs.org
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
    """Write a test CA plus a server cert Caddy presents on :8443 and :443.

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


def _corp_build_flags(registry: CorpRegistry) -> list[str]:
    """Docker build flags that point RUN at the Caddy double.

    Args:
        registry: Live Caddy connection details.

    Returns:
        Argument list to splice after ``docker build``.
    """
    flags = [
        "--no-cache",
        "--add-host",
        f"{_PACKAGE_NAME}:host-gateway",
    ]
    for cdn_host in _CDN_HOSTS:
        flags.extend(["--add-host", f"{cdn_host}:host-gateway"])
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
    """Start Caddy on :8443 and yield registry build-args."""
    secrets = tmp_path_factory.mktemp("corp-secrets")
    username_file = secrets / "username"
    token_file = secrets / "token"
    username_file.write_text(_REGISTRY_USER, encoding="utf-8")
    token_file.write_text(_REGISTRY_TOKEN, encoding="utf-8")
    cert_dir = tmp_path_factory.mktemp("corp-tls")
    _write_tls_material(cert_dir)

    subprocess.run([docker, "rm", "-f", _CADDY_NAME], check=False, capture_output=True)
    run_checked([docker, "pull", _CADDY_IMAGE])
    run_checked(
        [
            docker,
            "run",
            "-d",
            "--name",
            _CADDY_NAME,
            "-p",
            f"{_LISTEN_PORT}:{_LISTEN_PORT}",
            "-p",
            "443:443",
            "-e",
            f"CORP_BASIC_HASH={_BASIC_HASH}",
            "-v",
            f"{CADDYFILE}:/etc/caddy/Caddyfile:ro",
            "-v",
            f"{cert_dir}:/certs:ro",
            _CADDY_IMAGE,
        ]
    )
    try:
        _wait_for_caddy(
            f"https://127.0.0.1:{_LISTEN_PORT}/health",
            docker,
            _CADDY_NAME,
            _WAIT_SECONDS,
        )
        package_host = f"{_PACKAGE_NAME}:{_LISTEN_PORT}"
        listen_base = f"https://127.0.0.1:{_LISTEN_PORT}"
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


@pytest.fixture(scope="session")
def corp_base_image(docker: str, corp_registry: CorpRegistry) -> str:
    """Build local-agent-tool-base through Caddy (CA + apt)."""
    tag = "local-agent-tool-base"
    run_checked(
        [
            docker,
            "build",
            *_corp_build_flags(corp_registry),
            "-t",
            tag,
            str(REPO_ROOT / "agent-tools" / "base"),
        ]
    )
    return tag


@pytest.fixture(scope="session")
def python_quality_corp_image(
    docker: str, corp_registry: CorpRegistry, corp_base_image: str
) -> str:
    """Build python-quality --target corp through Caddy (apt + pip)."""
    tag = "python-quality:corp-smoke"
    run_checked(
        [
            docker,
            "build",
            "--target",
            "corp",
            *_corp_build_flags(corp_registry),
            "-t",
            tag,
            str(REPO_ROOT / "agent-tools" / "python-quality"),
        ]
    )
    return tag


@pytest.fixture(scope="session")
def groovy_lint_corp_image(docker: str, corp_registry: CorpRegistry) -> str:
    """Build groovy-lint --target corp through Caddy (CA + npm)."""
    tag = "groovy-lint:corp-smoke"
    run_checked(
        [
            docker,
            "build",
            "--target",
            "corp",
            *_corp_build_flags(corp_registry),
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


def test_python_quality_corp_lint_passes(
    docker: str, python_quality_corp_image: str
) -> None:
    """Corp python-quality lint exits 0 on the typed fixture."""
    result = run_tool(
        docker,
        python_quality_corp_image,
        ["lint", "--path", "/workspace/ok.py"],
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_groovy_lint_corp_runs(docker: str, groovy_lint_corp_image: str) -> None:
    """Corp groovy-lint processes the Groovy fixture."""
    result = run_tool(
        docker,
        groovy_lint_corp_image,
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


def test_python_quality_corp_wheels_go_through_caddy(
    docker: str, python_quality_corp_image: str
) -> None:
    """pip downloaded wheels via the files.pythonhosted.org MITM on :443."""
    logs = _caddy_logs(docker)
    assert python_quality_corp_image
    assert ".whl" in logs, logs


def test_groovy_lint_corp_tarballs_go_through_caddy(
    docker: str, groovy_lint_corp_image: str
) -> None:
    """npm downloaded tarballs via the registry.npmjs.org MITM on :443."""
    logs = _caddy_logs(docker)
    assert groovy_lint_corp_image
    assert ".tgz" in logs, logs
