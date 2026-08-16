"""Guard GitHub Actions path filters so image smokes stay off docs-only PRs."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
_SMOKE = REPO_ROOT / ".github" / "workflows" / "agent-tools-smoke.yml"
_LINT = REPO_ROOT / ".github" / "workflows" / "lint-and-unit.yml"


def test_image_workflow_omits_agents_and_instructions() -> None:
    """Markdown-only PRs must not start the 45-minute image job."""
    text = _SMOKE.read_text(encoding="utf-8")
    assert "agents/**" not in text
    assert "instructions/**" not in text
    assert "agent-tools/**" in text
    assert "tests/agent-tools/**" in text


def test_lint_workflow_covers_agents_and_instructions() -> None:
    """Agent and instruction edits still run ruff, mypy, and unit tests."""
    text = _LINT.read_text(encoding="utf-8")
    assert "agents/**" in text
    assert "instructions/**" in text
    assert "scripts/**" in text
    assert 'pytest tests -m "not image"' in text
