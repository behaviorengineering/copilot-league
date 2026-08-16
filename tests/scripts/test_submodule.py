"""Unit tests for scripts/submodule.py (no Docker, no live origin push)."""

from __future__ import annotations

import importlib.util
import subprocess
from pathlib import Path
from types import ModuleType

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
_GIT_IDENT = ["-c", "user.name=test", "-c", "user.email=test@example.com"]


def _load_submodule() -> ModuleType:
    """Load scripts/submodule.py as a module without changing sys.path."""
    path = REPO_ROOT / "scripts" / "submodule.py"
    spec = importlib.util.spec_from_file_location("submodule_script", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


submodule = _load_submodule()


def _git(args: list[str], cwd: Path) -> str:
    """Run git in a throwaway repo with a local identity.

    Args:
        args: Git arguments after ``git``.
        cwd: Repository directory.

    Returns:
        Stripped stdout.
    """
    result = subprocess.run(
        ["git", *_GIT_IDENT, *args],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _init_repo(root: Path) -> None:
    """Create a repo with one commit on main.

    Args:
        root: Empty directory to initialize.
    """
    _git(["init", "-b", "main"], cwd=root)
    (root / "README.md").write_text("ok\n", encoding="utf-8")
    _git(["add", "README.md"], cwd=root)
    _git(["commit", "-m", "init"], cwd=root)


def test_build_menu_includes_pin_when_parent_exists() -> None:
    """Pin option is item 3 only when a parent repo is present."""
    with_pin = submodule._build_menu(".github", "main", show_pin=True)
    without = submodule._build_menu(".github", "main", show_pin=False)
    assert "3. Pin to current commit" in with_pin
    assert "3. Pin to current commit" not in without
    assert "Submodule : .github" in with_pin
    assert "Branch    : main" in with_pin


def test_get_submodule_name_uses_directory_when_no_parent(tmp_path: Path) -> None:
    """Standalone clone reports the directory name."""
    root = tmp_path / "copilot-league"
    root.mkdir()
    assert submodule.get_submodule_name(root, None) == "copilot-league"


def test_get_submodule_name_is_relative_to_parent(tmp_path: Path) -> None:
    """Consuming project sees the gitlink path."""
    parent = tmp_path / "app"
    child = parent / ".github"
    child.mkdir(parents=True)
    assert submodule.get_submodule_name(child, parent) == ".github"


def test_select_branch_quit(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """q cancels without picking a branch."""
    monkeypatch.setattr("builtins.input", lambda _: "q")
    assert submodule._select_branch(["main", "dev"], "main") is None
    capsys.readouterr()


def test_select_branch_rejects_non_numeric(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Non-numeric input cancels."""
    monkeypatch.setattr("builtins.input", lambda _: "nope")
    assert submodule._select_branch(["main"], "main") is None
    assert "Invalid input" in capsys.readouterr().out


def test_select_branch_returns_other_branch(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A valid index that is not the current branch is returned."""
    monkeypatch.setattr("builtins.input", lambda _: "2")
    assert submodule._select_branch(["main", "dev"], "main") == "dev"
    capsys.readouterr()


def test_select_branch_skips_already_current(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Selecting the current branch is a no-op."""
    monkeypatch.setattr("builtins.input", lambda _: "1")
    assert submodule._select_branch(["main", "dev"], "main") is None
    assert "Already on" in capsys.readouterr().out


def test_get_current_branch_and_dirty_flag(tmp_path: Path) -> None:
    """Branch name and porcelain dirty detection against a real tmp repo."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_repo(repo)
    assert submodule.get_current_branch(repo) == "main"
    assert submodule.is_working_tree_dirty(repo) is False
    (repo / "extra.txt").write_text("x\n", encoding="utf-8")
    assert submodule.is_working_tree_dirty(repo) is True
    sha = submodule.get_current_sha(repo)
    assert len(sha) == 7


def test_get_current_branch_detached(tmp_path: Path) -> None:
    """Detached HEAD is reported as a fixed label."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_repo(repo)
    sha = _git(["rev-parse", "HEAD"], cwd=repo)
    _git(["checkout", sha], cwd=repo)
    assert submodule.get_current_branch(repo) == "(detached HEAD)"


def test_find_parent_repo_root_none_when_not_a_gitlink(tmp_path: Path) -> None:
    """A nested git repo that is not mode 160000 is not a submodule."""
    parent = tmp_path / "parent"
    child = parent / "nested"
    parent.mkdir()
    child.mkdir()
    _init_repo(parent)
    _init_repo(child)
    assert submodule.find_parent_repo_root(child) is None


def test_find_parent_repo_root_detects_gitlink(tmp_path: Path) -> None:
    """Mode 160000 in the parent index identifies a submodule."""
    parent = tmp_path / "app"
    child = parent / ".github"
    parent.mkdir()
    child.mkdir()
    _init_repo(parent)
    _init_repo(child)
    sha = _git(["rev-parse", "HEAD"], cwd=child)
    _git(
        ["update-index", "--add", "--cacheinfo", f"160000,{sha},.github"],
        cwd=parent,
    )
    assert submodule.find_parent_repo_root(child) == parent.resolve()


def test_get_remote_branches_parses_origin_refs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """HEAD pointer lines are dropped; origin/ prefix is stripped."""

    def fake_run_git(args: list[str], *, cwd: Path, check: bool = True) -> str:
        if args[:1] == ["fetch"]:
            return ""
        if args == ["branch", "-r"]:
            return (
                "  origin/HEAD -> origin/main\n"
                "  origin/main\n"
                "  origin/feature\n"
                "  origin/main"
            )
        raise AssertionError(args)

    monkeypatch.setattr(submodule, "run_git", fake_run_git)
    branches = submodule.get_remote_branches(tmp_path)
    assert branches == ["feature", "main"]
    capsys.readouterr()


def test_find_submodule_root_exits_outside_git(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Not-a-repo is a fatal error, not a traceback."""

    def boom(args: list[str], *, cwd: Path, check: bool = True) -> str:
        raise subprocess.CalledProcessError(128, ["git", *args])

    monkeypatch.setattr(submodule, "run_git", boom)
    with pytest.raises(SystemExit) as caught:
        submodule.find_submodule_root()
    assert caught.value.code == 1
    assert "not inside a git repo" in capsys.readouterr().out
