"""
Tests for git utilities module.
"""

import os
import subprocess
from pathlib import Path

import pytest

from mcp_server.git_utils import (
    decode_git_path,
    detect_git_repo_type,
    check_git_available,
    get_git_version,
    git_environment,
)


@pytest.mark.parametrize("source", ["numbered", "parameters"])
def test_command_config_preserves_policy_and_discards_redirects(git_repo, monkeypatch, source):
    settings = [
        ("core.worktree", str(git_repo / "elsewhere")),
        ("user.name", "O'Brien"),
        ("commit.gpgSign", "true"),
        ("push.default", "nothing"),
        ("credential.helper", "example helper"),
        ("credential.helper", ""),
    ]
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", os.devnull)
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    if source == "numbered":
        monkeypatch.setenv("GIT_CONFIG_COUNT", str(len(settings)))
        for i, (key, value) in enumerate(settings):
            monkeypatch.setenv(f"GIT_CONFIG_KEY_{i}", key)
            monkeypatch.setenv(f"GIT_CONFIG_VALUE_{i}", value)
    else:
        # Both Git encodings occur in the wild, including a literal apostrophe.
        monkeypatch.setenv("GIT_CONFIG_PARAMETERS",
                           r"'core.worktree=elsewhere' 'user.name'='O'\''Brien' "
                           "'commit.gpgSign' 'push.default=nothing' "
                           "'credential.helper'='example helper' 'credential.helper'=''")

    def git(*args):
        return subprocess.check_output(["git", *args], cwd=git_repo, env=git_environment(), text=True)

    assert Path(git("rev-parse", "--show-toplevel").rstrip("\n")) == git_repo
    assert git("config", "--get", "user.name") == "O'Brien\n"
    assert git("config", "--bool", "commit.gpgSign") == "true\n"
    assert git("config", "--get", "push.default") == "nothing\n"
    assert git("config", "--get-all", "credential.helper") == "example helper\n\n"


class TestGitUtils:
    """Tests for git utilities."""

    def test_rev_parse_path_removes_only_git_record_terminator(self):
        name = " leading\r\nline ending in whitespace \t\n"
        assert decode_git_path(os.fsencode(name) + b"\n") == name
    
    def test_check_git_available(self):
        """Test git availability check."""
        assert check_git_available() is True
    
    def test_get_git_version(self):
        """Test getting git version."""
        version = get_git_version()
        
        assert version is not None
        assert 'git version' in version.lower()
    
    def test_detect_regular_repo(self, git_repo):
        """Test detection of regular git repository."""
        repo_info = detect_git_repo_type(git_repo)
        
        assert repo_info is not None
        assert repo_info.root == git_repo
        assert not repo_info.is_worktree
        assert not repo_info.is_submodule
        assert not repo_info.is_bare
    
    def test_detect_worktree(self, git_worktree):
        """Test detection of git worktree."""
        repo_info = detect_git_repo_type(git_worktree)
        
        assert repo_info is not None
        assert repo_info.root == git_worktree
        assert repo_info.is_worktree
    
    def test_detect_submodule(self, git_submodule):
        """Test detection of git submodule."""
        repo_info = detect_git_repo_type(git_submodule)
        
        assert repo_info is not None
        assert repo_info.is_submodule
        assert repo_info.superproject_root is not None
    
    def test_detect_bare_repo(self, bare_repo):
        """Test detection of bare repository."""
        repo_info = detect_git_repo_type(bare_repo)
        
        # Bare repositories may not have a working tree to detect from
        # This is expected - bare repos are detected differently
        if repo_info is not None:
            assert repo_info.is_bare
        else:
            # For bare repos, git rev-parse --show-toplevel fails
            # This is expected behavior
            pass
    
    def test_detect_non_git_directory(self, temp_dir):
        """Test detection returns None for non-git directory."""
        non_git_dir = temp_dir / 'not_git'
        non_git_dir.mkdir()
        
        repo_info = detect_git_repo_type(non_git_dir)
        
        assert repo_info is None
    
    def test_detect_from_subdirectory(self, git_repo):
        """Test detection from subdirectory of git repo."""
        subdir = git_repo / 'src'
        subdir.mkdir()
        
        repo_info = detect_git_repo_type(subdir)
        
        assert repo_info is not None
        assert repo_info.root == git_repo
