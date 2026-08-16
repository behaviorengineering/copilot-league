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


def rewrite_body(body: str, public_origin: str) -> str:
    """Replace upstream CDN hosts with paths on the corp vhost.

    Args:
        body: Upstream HTML or JSON.
        public_origin: ``https://artifactory.example.com:<port>``.

    Returns:
        Body with file URLs pointed at ``/pypi-files`` or ``/npm-tarballs``.
    """
    rewritten = body.replace(_FILES_HOST, f"{public_origin}/pypi-files")
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
        request = urllib.request.Request(url, method=self.command)
        accept = self.headers.get("Accept")
        if accept:
            request.add_header("Accept", accept)
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
    """Bind the rewriter on localhost.

    Args:
        port: TCP port. ``0`` picks an ephemeral port.

    Returns:
        Started server (daemon thread already serving).
    """
    server = ThreadingHTTPServer(("127.0.0.1", port), RewriteHandler)
    return server
