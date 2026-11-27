"""
Git-specific utilities for handling edge cases.

Provides support for:
- Git worktrees (where .git is a file, not directory)
- Git submodules (nested repositories)
- Bare repositories (no working tree)
- Nested repositories
"""

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


# Clear inherited repository selectors. Git's discovery boundaries still apply.
_REPO_ENV = {
    "GIT_ALTERNATE_OBJECT_DIRECTORIES", "GIT_COMMON_DIR",
    "GIT_CONFIG", "GIT_DIR",
    "GIT_GRAFT_FILE", "GIT_IMPLICIT_WORK_TREE",
    "GIT_INDEX_FILE", "GIT_NAMESPACE", "GIT_NO_REPLACE_OBJECTS", "GIT_OBJECT_DIRECTORY",
    "GIT_PREFIX", "GIT_QUARANTINE_PATH", "GIT_REPLACE_REF_BASE", "GIT_SHALLOW_FILE",
    "GIT_WORK_TREE",
}


def _quote_config_field(value: str) -> str:
    """Single-quote one field for Git's GIT_CONFIG_PARAMETERS encoding."""
    return "'" + value.replace("'", "'\\''") + "'"


def git_environment(*, discovery: bool = False) -> dict[str, str]:
    """Remove inherited repository selectors while preserving other command config."""
    env = {key: value for key, value in os.environ.items() if key not in _REPO_ENV}
    if not env.get("GIT_CONFIG_PARAMETERS") and env.get("GIT_CONFIG_COUNT", "0") == "0":
        return env

    # Let Git decode both command config formats in precedence order. Read
    # only the environment here, without following includes or opening a repo.
    result = subprocess.run(
        ["git", "config", "--null", "--list", "--no-includes"],
        env={**env, "GIT_DIR": os.devnull, "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"},
        capture_output=True, stdin=subprocess.DEVNULL, timeout=5,
    )
    if result.returncode:
        raise ValueError("Invalid inherited Git command configuration")

    kept = []
    for record in result.stdout.split(b"\0")[:-1]:
        entry = os.fsdecode(record)
        key, separator, value = entry.partition("\n")
        if key in ("core.worktree", "core.bare", "extensions.worktreeconfig"):
            continue
        # Includes may also set core.worktree. Restore them in their original
        # position once GIT_DIR and GIT_WORK_TREE control repository selection.
        if discovery and (key == "include.path" or (key.startswith("includeif.") and key.endswith(".path"))):
            continue
        # A missing value is an implicit boolean, distinct from an empty value.
        kept.append(_quote_config_field(key) + "=" + (_quote_config_field(value) if separator else ""))

    env.pop("GIT_CONFIG_COUNT", None)
    for key in list(env):
        if key.startswith(("GIT_CONFIG_KEY_", "GIT_CONFIG_VALUE_")) and key.rpartition("_")[2].isdigit():
            del env[key]
    env["GIT_CONFIG_PARAMETERS"] = " ".join(kept)
    return env


def rev_parse(path: Path, *args: str, env: Optional[dict[str, str]] = None) -> subprocess.CompletedProcess:
    if env is None:
        env = git_environment(discovery=True)
    return subprocess.run(
        ["git", "rev-parse", *args], cwd=path, env=env,
        capture_output=True, timeout=5.0, stdin=subprocess.DEVNULL,
    )


def decode_git_path(output: bytes) -> str:
    """Decode a single rev-parse path, including any whitespace in its name."""
    return os.fsdecode(output.removesuffix(b"\n"))


@dataclass
class GitRepoInfo:
    """Information about a git repository."""
    root: Path
    git_dir: Path
    is_worktree: bool
    is_submodule: bool
    is_bare: bool
    superproject_root: Optional[Path] = None


class GitUtilsError(Exception):
    """Base exception for git utilities errors."""
    pass


@dataclass(frozen=True)
class GitTarget:
    """The absolute Git directory and optional working tree selected together."""
    git_dir: Path
    worktree: Optional[Path]

    @property
    def cwd(self) -> Path:
        return self.worktree or self.git_dir

    def environment(self) -> dict[str, str]:
        env = git_environment()
        env["GIT_DIR"] = str(self.git_dir)
        if self.worktree is None:
            env["GIT_IMPLICIT_WORK_TREE"] = "0"
        else:
            env["GIT_WORK_TREE"] = str(self.worktree)
        return env

    def rev_parse(self, *args: str) -> subprocess.CompletedProcess:
        return rev_parse(self.cwd, *args, env=self.environment())


def _read_git_target(path: Path, env: dict[str, str]) -> Optional[GitTarget]:
    result = rev_parse(path, "--absolute-git-dir", env=env)
    if result.returncode:
        return None
    git_dir = Path(decode_git_path(result.stdout)).resolve()
    top = rev_parse(path, "--show-toplevel", env=env)
    worktree = None if top.returncode else Path(decode_git_path(top.stdout)).resolve()
    return GitTarget(git_dir, worktree)


def discover_git_target(path: Path) -> Optional[GitTarget]:
    """Validate the worktree and retain the Git directory selected at the original path."""
    env = git_environment(discovery=True)
    target = _read_git_target(path, env)
    if target and target.worktree and target.worktree != path:
        at_root = rev_parse(target.worktree, "--absolute-git-dir", env=env)
        if at_root.returncode or Path(decode_git_path(at_root.stdout)).resolve() != target.git_dir:
            raise GitUtilsError(f"Worktree at {target.worktree} does not select the Git directory for {path}")
    return target


def discover_worktree(path: Path) -> Optional[Path]:
    """Find a worktree that selects the same Git directory as the starting path."""
    target = discover_git_target(path)
    return target.worktree if target else None


def external_watcher_target(cwd: Path, process_env: dict[str, str]) -> Optional[GitTarget]:
    """Discover a watcher's target only when we can reproduce its Git context."""
    if os.name == "nt":
        process_env = {key.upper(): value for key, value in process_env.items()}
    selectors = {"GIT_DIR", "GIT_WORK_TREE"}
    if (_REPO_ENV - selectors).intersection(process_env):
        # A separate index, common directory, or object store is a different target.
        return None

    # Use the server's Git executable and configuration. If the watcher uses
    # another context, its cwd alone cannot establish which checkout it owns.
    context_keys = {
        "PATH", "HOME", "HOMEDRIVE", "HOMEPATH", "USERPROFILE", "XDG_CONFIG_HOME",
        "GIT_CEILING_DIRECTORIES", "GIT_DISCOVERY_ACROSS_FILESYSTEM", "GIT_EXEC_PATH",
    }

    def context(env):
        return {k: v for k, v in env.items() if k in context_keys or k.startswith("GIT_CONFIG_")}

    if context(process_env) != context(os.environ):
        return None
    env = {key: value for key, value in os.environ.items() if key not in _REPO_ENV}
    for key in selectors:
        if key in process_env:
            env[key] = process_env[key]
    return _read_git_target(cwd, env)


def detect_git_repo_type(path: Path | GitTarget) -> Optional[GitRepoInfo]:
    """Describe a worktree using the same Git directory for each probe."""
    try:
        target = path if isinstance(path, GitTarget) else discover_git_target(path)
        if not target or not target.worktree:
            return None
        common = target.rev_parse("--git-common-dir")
        common.check_returncode()
        common_dir = (target.cwd / decode_git_path(common.stdout)).resolve()
        superproject = target.rev_parse("--show-superproject-working-tree")
        superproject.check_returncode()
        parent = decode_git_path(superproject.stdout)
        return GitRepoInfo(
            root=target.worktree,
            git_dir=target.git_dir,
            is_worktree=common_dir != target.git_dir,
            is_submodule=bool(parent),
            is_bare=False,
            superproject_root=Path(parent) if parent else None,
        )
    except (OSError, GitUtilsError, subprocess.SubprocessError):
        return None


def check_git_available() -> bool:
    """
    Check if git command is available.
    
    Returns:
        True if git is available, False otherwise
    """
    try:
        result = subprocess.run(
            ['git', '--version'],
            capture_output=True,
            text=True,
            timeout=5.0,
            stdin=subprocess.DEVNULL,
        )
        return result.returncode == 0
    except Exception:
        return False


def get_git_version() -> Optional[str]:
    """
    Get git version string.
    
    Returns:
        Git version string, or None if git not available
    """
    try:
        result = subprocess.run(
            ['git', '--version'],
            capture_output=True,
            text=True,
            timeout=5.0,
            stdin=subprocess.DEVNULL,
        )
        if result.returncode == 0:
            return result.stdout.strip()
        return None
    except Exception:
        return None
