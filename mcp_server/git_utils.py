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
    "GIT_CONFIG", "GIT_CONFIG_PARAMETERS", "GIT_DIR",
    "GIT_GRAFT_FILE", "GIT_IMPLICIT_WORK_TREE",
    "GIT_INDEX_FILE", "GIT_NAMESPACE", "GIT_NO_REPLACE_OBJECTS", "GIT_OBJECT_DIRECTORY",
    "GIT_PREFIX", "GIT_QUARANTINE_PATH", "GIT_REPLACE_REF_BASE", "GIT_SHALLOW_FILE",
    "GIT_WORK_TREE",
}

_IDENTITY_CONFIG = {
    "user.name", "user.email", "user.useconfigonly", "user.signingkey",
    "author.name", "author.email", "committer.name", "committer.email",
}


def git_environment() -> dict[str, str]:
    """Let Git discover the target from cwd, preserving user identity and credentials."""
    env = {key: value for key, value in os.environ.items() if key not in _REPO_ENV}
    # Numbered config can mix identity with redirects such as core.worktree.
    count = int(env.pop("GIT_CONFIG_COUNT", "0") or 0)
    kept = 0
    for index in range(count):
        key = env.pop(f"GIT_CONFIG_KEY_{index}")
        value = env.pop(f"GIT_CONFIG_VALUE_{index}")
        if key.lower() in _IDENTITY_CONFIG:
            env[f"GIT_CONFIG_KEY_{kept}"] = key
            env[f"GIT_CONFIG_VALUE_{kept}"] = value
            kept += 1
    if kept:
        env["GIT_CONFIG_COUNT"] = str(kept)
    return env


def rev_parse(path: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "rev-parse", *args], cwd=path, env=git_environment(),
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


def detect_git_repo_type(path: Path) -> Optional[GitRepoInfo]:
    """
    Detect the type of git repository at the given path.
    
    Handles:
    - Regular git repositories
    - Git worktrees (where .git is a file)
    - Git submodules
    - Bare repositories
    
    Args:
        path: Path to check
        
    Returns:
        GitRepoInfo if path is in a git repository, None otherwise
    """
    try:
        # Get repository root
        result = rev_parse(path, '--show-toplevel')
        
        if result.returncode != 0:
            return None
        
        root = Path(decode_git_path(result.stdout))
        
        # Get git directory
        result = rev_parse(path, '--git-dir')
        
        if result.returncode != 0:
            return None
        
        git_dir = Path(decode_git_path(result.stdout))
        if not git_dir.is_absolute():
            git_dir = (path / git_dir).resolve()
        
        # Check if it's a worktree
        is_worktree = _is_worktree(path)
        
        # Check if it's a submodule
        is_submodule = _is_submodule(path)
        
        # Check if it's a bare repository
        is_bare = _is_bare_repository(path)
        
        # Get superproject root if in submodule
        superproject_root = None
        if is_submodule:
            superproject_root = _get_superproject_root(path)
        
        return GitRepoInfo(
            root=root,
            git_dir=git_dir,
            is_worktree=is_worktree,
            is_submodule=is_submodule,
            is_bare=is_bare,
            superproject_root=superproject_root,
        )
        
    except Exception:
        return None


def _is_worktree(path: Path) -> bool:
    """
    Check if path is in a git worktree.
    
    In worktrees, .git is a file (not directory) that points to the
    actual git directory.
    
    Args:
        path: Path to check
        
    Returns:
        True if path is in a worktree
    """
    try:
        result = rev_parse(path, '--git-common-dir')
        
        if result.returncode != 0:
            return False
        
        common_dir = result.stdout
        
        # In a worktree, --git-common-dir points to the main repo's .git dir
        # In a regular repo, it points to .git (same as --git-dir)
        result2 = rev_parse(path, '--git-dir')
        
        if result2.returncode != 0:
            return False
        
        git_dir = result2.stdout
        
        # If they're different, it's a worktree
        return common_dir != git_dir
        
    except Exception:
        return False


def _is_submodule(path: Path) -> bool:
    """
    Check if path is in a git submodule.
    
    Args:
        path: Path to check
        
    Returns:
        True if path is in a submodule
    """
    try:
        result = rev_parse(path, '--show-superproject-working-tree')
        
        # If there's a superproject, this is a submodule
        return result.returncode == 0 and bool(decode_git_path(result.stdout))
        
    except Exception:
        return False


def _is_bare_repository(path: Path) -> bool:
    """
    Check if path is a bare git repository.
    
    Bare repositories don't have a working tree.
    
    Args:
        path: Path to check
        
    Returns:
        True if path is a bare repository
    """
    try:
        result = rev_parse(path, '--is-bare-repository')
        
        return result.returncode == 0 and result.stdout.strip() == b'true'
        
    except Exception:
        return False


def _get_superproject_root(path: Path) -> Optional[Path]:
    """
    Get the root of the superproject if path is in a submodule.
    
    Args:
        path: Path to check
        
    Returns:
        Path to superproject root, or None if not in submodule
    """
    try:
        result = rev_parse(path, '--show-superproject-working-tree')
        
        if result.returncode == 0 and result.stdout:
            return Path(decode_git_path(result.stdout))
        
        return None
        
    except Exception:
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
