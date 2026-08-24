"""Unit tests for PyPI/npm CDN URL rewriting (no Docker)."""

from __future__ import annotations

from urlrewrite import rewrite_body, serve, upstream_url


def test_rewrite_body_rewrites_pypi_and_npm_cdns() -> None:
    """files.pythonhosted.org and registry.npmjs.org move onto the vhost."""
    origin = "https://artifactory.example.com:18443"
    body = (
        "https://files.pythonhosted.org/packages/ab/invoke-2.whl "
        "https://registry.npmjs.org/npm-groovy-lint/-/x.tgz"
    )
    out = rewrite_body(body, origin)
    assert f"{origin}/pypi-files/packages/ab/invoke-2.whl" in out
    assert f"{origin}/npm-tarballs/npm-groovy-lint/-/x.tgz" in out
    assert "files.pythonhosted.org" not in out
    assert "registry.npmjs.org" not in out


def test_upstream_url_maps_pypi_simple_and_npm() -> None:
    """Corp paths map to pypi.org/simple and registry.npmjs.org."""
    assert (
        upstream_url("/artifactory/api/pypi/pypi-virtual/simple/invoke/")
        == "https://pypi.org/simple/invoke/"
    )
    assert (
        upstream_url("/artifactory/api/npm/npm-virtual/npm-groovy-lint")
        == "https://registry.npmjs.org/npm-groovy-lint"
    )
    assert upstream_url("/nope") is None


def test_rewrite_body_rewrites_http_npm_registry() -> None:
    """http://registry.npmjs.org packument tarball URLs also move onto the vhost."""
    origin = "https://artifactory.example.com:18443"
    out = rewrite_body("http://registry.npmjs.org/pkg/-/pkg.tgz", origin)
    assert out == f"{origin}/npm-tarballs/pkg/-/pkg.tgz"


def test_serve_listens_on_all_interfaces() -> None:
    """Linux Docker host-gateway cannot reach a 127.0.0.1-only bind."""
    server = serve(0)
    try:
        assert server.server_address[0] == "0.0.0.0"
    finally:
        server.server_close()
