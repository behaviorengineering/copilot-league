"""Fail if agent/skill load tables use bare agents/skills or agents/references paths."""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
_BARE = re.compile(r"(?<!\.github/)(?<!/)agents/(skills|references)/")
_WRONG_LABEL = re.compile(r"WRONG|PROHIBITED|incorrect|not bare", re.IGNORECASE)


def _is_allowed(line: str) -> bool:
    """Return True when a bare path is a labeled counterexample.

    Args:
        line: Source line that matched the bare-path regex.

    Returns:
        True if the line is an allowed exception.
    """
    if "plugin.json" in line or '"agents":' in line or '"skills":' in line:
        return True
    if _WRONG_LABEL.search(line):
        return True
    return "drop the `.github/`" in line or "drop `.github/`" in line


def test_agent_and_skill_load_paths_use_github_prefix() -> None:
    """Consuming projects resolve skills at .github/agents/skills/."""
    roots = [REPO_ROOT / "agents", REPO_ROOT / "instructions"]
    offenders: list[str] = []
    for root in roots:
        for path in root.rglob("*"):
            if path.suffix not in {".md"} or path.name == "README.md":
                continue
            if "templates" in path.parts:
                continue
            text = path.read_text(encoding="utf-8")
            for lineno, line in enumerate(text.splitlines(), start=1):
                if not _BARE.search(line):
                    continue
                if _is_allowed(line):
                    continue
                rel = path.relative_to(REPO_ROOT)
                offenders.append(f"{rel}:{lineno}:{line.strip()}")
    assert not offenders, (
        "bare agents/skills or agents/references paths:\n" + "\n".join(offenders)
    )
