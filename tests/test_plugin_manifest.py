"""Keep .github/plugin/plugin.json aligned with shipped agents and skills."""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
_PLUGIN = REPO_ROOT / ".github" / "plugin" / "plugin.json"


def test_plugin_manifest_lists_every_agent_and_skill() -> None:
    """Plugin paths are repo-relative agents/, matching Copilot CLI plugins."""
    manifest = json.loads(_PLUGIN.read_text(encoding="utf-8"))
    agents = sorted(p.name for p in (REPO_ROOT / "agents").glob("*.agent.md"))
    listed_agents = sorted(Path(p).name for p in manifest["agents"])
    assert listed_agents == agents

    skills = sorted(
        p.name for p in (REPO_ROOT / "agents" / "skills").iterdir() if p.is_dir()
    )
    listed_skills = sorted(Path(p).name for p in manifest["skills"])
    assert listed_skills == skills
