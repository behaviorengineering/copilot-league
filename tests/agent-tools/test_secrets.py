"""Unit tests for detect-secrets exclude regex (no Docker)."""

from __future__ import annotations

import importlib.util
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_exclude() -> str:
    """Load DETECT_SECRETS_EXCLUDE without importing invoke."""
    path = REPO_ROOT / "agent-tools" / "python-quality" / "tasks" / "_secrets.py"
    spec = importlib.util.spec_from_file_location("python_quality_secrets", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return str(module.DETECT_SECRETS_EXCLUDE)


DETECT_SECRETS_EXCLUDE = _load_exclude()
_PATTERN = re.compile(DETECT_SECRETS_EXCLUDE)


def test_exclude_skips_venv_build_dist_git() -> None:
    """Anchored segments match real tool dirs."""
    assert _PATTERN.search(".venv/lib/x.py")
    assert _PATTERN.search("src/build/out.py")
    assert _PATTERN.search("dist/pkg.whl")
    assert _PATTERN.search(".git/objects/ab")
    assert _PATTERN.search("pkg.egg-info/PKG-INFO")


def test_exclude_does_not_match_rebuild_or_distribute() -> None:
    """Bare build/dist must not match rebuild.py or distribute.py."""
    assert not _PATTERN.search("rebuild.py")
    assert not _PATTERN.search("src/rebuild.py")
    assert not _PATTERN.search("distribute.py")
