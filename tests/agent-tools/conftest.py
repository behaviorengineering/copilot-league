"""Shared fixtures for agent-tool image smokes."""

from __future__ import annotations

import pytest
from dockerutil import docker_cli


@pytest.fixture(scope="session")
def docker() -> str:
    """Docker CLI when the daemon is available."""
    return docker_cli()
