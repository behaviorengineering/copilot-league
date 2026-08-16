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
    _git(["config", "user.name", "test"], cwd=root)
    _git(["config", "user.email", "test@example.com"], cwd=root)
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
                "  origin/HEAD-fix\n"
                "  origin/main"
            )
        raise AssertionError(args)

    monkeypatch.setattr(submodule, "run_git", fake_run_git)
    branches = submodule.get_remote_branches(tmp_path)
    assert branches == ["HEAD-fix", "feature", "main"]
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


def test_cmd_pin_commit_updates_parent_pointer(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Pin commits the parent gitlink after the submodule SHA moves."""
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
    _git(["commit", "-m", "add submodule"], cwd=parent)
    (child / "extra.txt").write_text("x\n", encoding="utf-8")
    _git(["add", "extra.txt"], cwd=child)
    _git(["commit", "-m", "child change"], cwd=child)
    submodule.cmd_pin_commit(child, parent, ".github")
    log = _git(["log", "-1", "--format=%s"], cwd=parent)
    assert log.startswith("Pin .github submodule to commit")
    capsys.readouterr()


def test_push_to_origin_success(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Successful push prints the branch name and does not exit."""

    def fake_run_git(args: list[str], *, cwd: Path, check: bool = True) -> str:
        if args[:2] == ["symbolic-ref", "--short"]:
            return "main"
        if args[:3] == ["push", "origin", "main"]:
            return ""
        raise AssertionError(args)

    monkeypatch.setattr(submodule, "run_git", fake_run_git)
    submodule.push_to_origin(tmp_path)
    assert "Pushed 'main' to origin." in capsys.readouterr().out


def test_push_to_origin_failure_exits(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """git push failure is a fatal SystemExit, not a traceback."""

    def fake_run_git(args: list[str], *, cwd: Path, check: bool = True) -> str:
        if args[:2] == ["symbolic-ref", "--short"]:
            return "main"
        raise subprocess.CalledProcessError(1, ["git", *args])

    monkeypatch.setattr(submodule, "run_git", fake_run_git)
    with pytest.raises(SystemExit) as caught:
        submodule.push_to_origin(tmp_path)
    assert caught.value.code == 1
    assert "git push failed" in capsys.readouterr().out


def test_cmd_update_commits_parent_pointer(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Update pulls, then commits the parent gitlink when SHAs match."""
    parent = tmp_path / "app"
    child = parent / ".github"
    monkeypatch.setattr(submodule, "get_current_branch", lambda _root: "main")
    monkeypatch.setattr(submodule, "_confirm_and_reset", lambda _root: True)
    monkeypatch.setattr(
        submodule, "_pull_with_recovery", lambda _root, _branch: "Already up to date."
    )
    monkeypatch.setattr(
        submodule, "get_remote_tracking_sha", lambda _root, _branch: "abc1234"
    )

    commits: list[list[str]] = []

    def fake_run_git(args: list[str], *, cwd: Path, check: bool = True) -> str:
        if args[:2] == ["rev-parse", "HEAD"]:
            return "abc1234"
        if args[:1] == ["add"]:
            assert args[1] == ".github"
            assert cwd == parent
            return ""
        if args[:1] == ["commit"]:
            commits.append(args)
            return "committed"
        raise AssertionError(args)

    monkeypatch.setattr(submodule, "run_git", fake_run_git)
    submodule.cmd_update(child, parent, ".github")
    assert commits
    assert "Update .github submodule to latest 'main'" in commits[0][-1]
    capsys.readouterr()


def test_cmd_switch_branch_commits_parent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Switch checks out the selected branch and pins .gitmodules on the parent."""
    parent = tmp_path / "app"
    child = parent / ".github"
    git_dir = tmp_path / "gitdir"
    git_dir.mkdir()
    monkeypatch.setattr(submodule, "get_remote_branches", lambda _root: ["main", "dev"])
    monkeypatch.setattr(submodule, "get_current_branch", lambda _root: "main")
    monkeypatch.setattr(submodule, "_select_branch", lambda _branches, _current: "dev")
    monkeypatch.setattr(submodule, "_confirm_and_reset", lambda _root: True)
    monkeypatch.setattr(submodule, "_get_git_dir", lambda _root: git_dir)

    seen: list[list[str]] = []

    def fake_run_git(args: list[str], *, cwd: Path, check: bool = True) -> str:
        seen.append(args)
        return ""

    monkeypatch.setattr(submodule, "run_git", fake_run_git)
    submodule.cmd_switch_branch(child, parent, ".github")
    assert ["checkout", "dev"] in seen
    assert ["reset", "--hard", "origin/dev"] in seen
    assert ["submodule", "set-branch", "--branch", "dev", ".github"] in seen
    assert any(
        args[:1] == ["commit"] and "Pin .github submodule to branch 'dev'" in args[-1]
        for args in seen
    )
    capsys.readouterr()


def test_cmd_update_refuses_detached_head(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Update on detached HEAD is a no-op, not a pull of '(detached HEAD)'."""
    monkeypatch.setattr(
        submodule, "get_current_branch", lambda _root: "(detached HEAD)"
    )
    called: list[str] = []
    monkeypatch.setattr(
        submodule, "_pull_with_recovery", lambda *_a, **_k: called.append("pull")
    )
    assert submodule.cmd_update(tmp_path, None, ".github") is False
    assert called == []
    assert "detached HEAD" in capsys.readouterr().out


def test_interactive_menu_skips_push_when_update_cancelled(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Cancelled update must not prompt to push."""
    parent = tmp_path / "app"
    child = parent / ".github"
    monkeypatch.setattr(submodule, "get_current_branch", lambda _root: "main")
    monkeypatch.setattr(submodule, "_build_menu", lambda *_a, **_k: "menu")
    monkeypatch.setattr(submodule, "cmd_update", lambda *_a, **_k: False)
    pushed: list[str] = []
    monkeypatch.setattr(submodule, "push_to_origin", lambda _p: pushed.append("push"))
    answers = iter(["1", "q"])
    monkeypatch.setattr("builtins.input", lambda _p="": next(answers))
    submodule.interactive_menu(child, parent, ".github")
    assert pushed == []


def test_reset_working_tree_runs_hard_reset_and_clean(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Reset discards tracked and untracked files."""
    seen: list[list[str]] = []

    def fake_run_git(args: list[str], *, cwd: Path, check: bool = True) -> str:
        seen.append(args)
        return ""

    monkeypatch.setattr(submodule, "run_git", fake_run_git)
    submodule.reset_working_tree(tmp_path)
    assert ["reset", "--hard", "HEAD"] in seen
    assert ["clean", "-fd"] in seen


def test_pull_with_recovery_returns_none_when_user_cancels(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Failed pull with no MERGE_HEAD asks to reset; declining aborts."""
    git_dir = tmp_path / "gitdir"
    git_dir.mkdir()
    monkeypatch.setattr(submodule, "_get_git_dir", lambda _root: git_dir)

    def fake_run_git(args: list[str], *, cwd: Path, check: bool = True) -> str:
        raise subprocess.CalledProcessError(1, ["git", *args])

    monkeypatch.setattr(submodule, "run_git", fake_run_git)
    monkeypatch.setattr("builtins.input", lambda _p="": "n")
    assert submodule._pull_with_recovery(tmp_path, "main") is None
    capsys.readouterr()
