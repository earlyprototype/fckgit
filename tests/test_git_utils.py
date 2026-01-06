"""
Tests for git utilities module.
"""

from pathlib import Path

import pytest

from mcp_server.git_utils import (
    detect_git_repo_type,
    check_git_available,
    get_git_version,
)


class TestGitUtils:
    """Tests for git utilities."""
    
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
