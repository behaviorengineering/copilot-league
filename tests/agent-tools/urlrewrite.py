"""Rewrite PyPI/npm CDN URLs onto the corp Caddy vhost (no host :443)."""

from __future__ import annotations

import os
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Final

_PYPI_PREFIX: Final = "/artifactory/api/pypi/pypi-virtual/simple"
_NPM_PREFIX: Final = "/artifactory/api/npm/npm-virtual/"
_FILES_HOST: Final = "https://files.pythonhosted.org"
_NPM_HOST: Final = "https://registry.npmjs.org"
_PYPI_SIMPLE: Final = "https://pypi.org/simple"
_NPM_REGISTRY: Final = "https://registry.npmjs.org"
_UPSTREAM_UA: Final = "copilot-league-corp-double/1.0"


def rewrite_body(body: str, public_origin: str) -> str:
    """Replace upstream CDN hosts with paths on the corp vhost.

    Args:
        body: Upstream HTML or JSON.
        public_origin: ``https://artifactory.example.com:<port>``.

    Returns:
        Body with file URLs pointed at ``/pypi-files`` or ``/npm-tarballs``.
    """
    rewritten = body.replace(_FILES_HOST, f"{public_origin}/pypi-files")
    rewritten = rewritten.replace(
        "http://registry.npmjs.org", f"{public_origin}/npm-tarballs"
    )
    return rewritten.replace(_NPM_HOST, f"{public_origin}/npm-tarballs")


def upstream_url(path: str) -> str | None:
    """Map a corp-registry path to the public upstream URL.

    Args:
        path: Request path including query string.

    Returns:
        Absolute upstream URL, or None when the path is not proxied.
    """
    if path.startswith(_PYPI_PREFIX):
        rest = path[len(_PYPI_PREFIX) :]
        return f"{_PYPI_SIMPLE}{rest}"
    if path.startswith(_NPM_PREFIX):
        rest = path[len(_NPM_PREFIX) :]
        return f"{_NPM_REGISTRY}/{rest}"
    return None


def _upstream_request(
    url: str, method: str, accept: str | None
) -> urllib.request.Request:
    """Build the public-index request Caddy cannot issue itself.

    Args:
        url: Absolute upstream URL.
        method: HTTP method from the client.
        accept: Optional Accept header from npm/pip.

    Returns:
        Prepared request with a CDN-accepted User-Agent.
    """
    request = urllib.request.Request(url, method=method)
    request.add_header("User-Agent", _UPSTREAM_UA)
    if accept:
        request.add_header("Accept", accept)
    return request


class RewriteHandler(BaseHTTPRequestHandler):
    """Proxy PyPI simple / npm packument GETs and rewrite CDN URLs."""

    def log_message(self, format: str, *args: object) -> None:
        """Stay quiet in pytest output."""

    def do_GET(self) -> None:
        """Proxy GET."""
        self._proxy()

    def do_HEAD(self) -> None:
        """Proxy HEAD."""
        self._proxy()

    def _proxy(self) -> None:
        public_origin = os.environ.get("REWRITE_PUBLIC_ORIGIN", "")
        url = upstream_url(self.path)
        if not url or not public_origin:
            self.send_error(404)
            return
        request = _upstream_request(url, self.command, self.headers.get("Accept"))
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                raw = response.read()
                content_type = response.headers.get("Content-Type", "text/plain")
                status = response.status
        except urllib.error.HTTPError as exc:
            self.send_error(exc.code)
            return
        except (urllib.error.URLError, TimeoutError, OSError):
            self.send_error(502)
            return
        text = rewrite_body(raw.decode("utf-8", errors="replace"), public_origin)
        payload = text.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(payload)


def serve(port: int = 0) -> ThreadingHTTPServer:
    """Bind the rewriter on all interfaces so Docker host-gateway can reach it.

    Args:
        port: TCP port. ``0`` picks an ephemeral port.

    Returns:
        Listening server (caller starts ``serve_forever``).
    """
    return ThreadingHTTPServer(("0.0.0.0", port), RewriteHandler)
