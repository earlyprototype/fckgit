"""
Tests for workspace detection module.
"""

import os
import time
from pathlib import Path

import pytest

from mcp_server.workspace import (
    WorkspaceDetector,
    WorkspaceError,
    InvalidWorkspaceError,
    GitNotFoundError,
)


class TestWorkspaceDetector:
    """Tests for WorkspaceDetector class."""
    
    def test_detect_from_env_var(self, git_repo, mock_env):
        """Test workspace detection from PROJECT_ROOT environment variable."""
        mock_env.set('PROJECT_ROOT', str(git_repo))
        
        detector = WorkspaceDetector()
        workspace = detector.detect_workspace()
        
        assert workspace == git_repo
    
    def test_detect_from_git_command(self, git_repo):
        """Test workspace detection using git command."""
        # Change to git repo directory
        original_cwd = Path.cwd()
        try:
            os.chdir(git_repo)
            
            detector = WorkspaceDetector()
            workspace = detector.detect_workspace()
            
            assert workspace == git_repo
        finally:
            os.chdir(original_cwd)
    
    def test_detect_from_subdirectory(self, git_repo):
        """Test workspace detection from subdirectory."""
        # Create subdirectory
        subdir = git_repo / 'src' / 'nested'
        subdir.mkdir(parents=True)
        
        original_cwd = Path.cwd()
        try:
            os.chdir(subdir)
            
            detector = WorkspaceDetector()
            workspace = detector.detect_workspace()
            
            # Should detect git root, not subdirectory
            assert workspace == git_repo
        finally:
            os.chdir(original_cwd)
    
    def test_detect_worktree(self, git_worktree):
        """Test workspace detection in git worktree."""
        original_cwd = Path.cwd()
        try:
            os.chdir(git_worktree)
            
            detector = WorkspaceDetector()
            workspace = detector.detect_workspace()
            
            assert workspace == git_worktree
        finally:
            os.chdir(original_cwd)
    
    def test_detect_bare_repo(self, bare_repo):
        """Test workspace detection with bare repository."""
        original_cwd = Path.cwd()
        try:
            os.chdir(bare_repo)
            
            detector = WorkspaceDetector()
            workspace = detector.detect_workspace()
            
            assert workspace == bare_repo
        finally:
            os.chdir(original_cwd)
    
    def test_security_path_traversal(self, temp_dir):
        """Test that path traversal is prevented."""
        detector = WorkspaceDetector()
        
        # Attempt to use path traversal
        with pytest.raises(InvalidWorkspaceError):
            detector._sanitize_path(str(temp_dir / '..' / '..' / 'etc' / 'passwd'))
    
    def test_invalid_path(self):
        """Test handling of non-existent path."""
        detector = WorkspaceDetector()
        
        with pytest.raises(InvalidWorkspaceError):
            detector._sanitize_path('/nonexistent/path/that/does/not/exist')
    
    def test_path_is_file_not_directory(self, temp_dir):
        """Test that files are rejected (must be directory)."""
        test_file = temp_dir / 'test.txt'
        test_file.write_text('content')
        
        detector = WorkspaceDetector()
        
        with pytest.raises(InvalidWorkspaceError):
            detector._sanitize_path(str(test_file))
    
    def test_cache_functionality(self, git_repo):
        """Test that caching works correctly."""
        original_cwd = Path.cwd()
        try:
            os.chdir(git_repo)
            
            detector = WorkspaceDetector(cache_ttl=60)
            
            # First call should populate cache
            workspace1 = detector.detect_workspace()
            stats1 = detector.get_cache_stats()
            
            # Second call should hit cache
            workspace2 = detector.detect_workspace()
            stats2 = detector.get_cache_stats()
            
            assert workspace1 == workspace2
            # Cache hits should increase
            assert stats2['total_hits'] >= stats1['total_hits']
        finally:
            os.chdir(original_cwd)
    
    def test_cache_expiry(self, git_repo):
        """Test that cache expires after TTL."""
        original_cwd = Path.cwd()
        try:
            os.chdir(git_repo)
            
            # Very short TTL for testing
            detector = WorkspaceDetector(cache_ttl=1)
            
            # Populate cache
            detector._use_git_command(git_repo)
            
            # Wait for cache to expire
            time.sleep(1.1)
            
            # Should re-detect after expiry
            workspace = detector._use_git_command(git_repo)
            assert workspace == git_repo
        finally:
            os.chdir(original_cwd)
    
    def test_cache_invalidation(self, git_repo):
        """Test manual cache invalidation."""
        original_cwd = Path.cwd()
        try:
            os.chdir(git_repo)
            
            detector = WorkspaceDetector()
            
            # Populate cache
            detector.detect_workspace()
            assert detector._initialized
            
            # Invalidate cache
            detector.invalidate_cache()
            assert not detector._initialized
            
            # Should re-detect
            workspace = detector.detect_workspace()
            assert workspace == git_repo
        finally:
            os.chdir(original_cwd)
    
    def test_override_parameter(self, git_repo, temp_dir):
        """Test that override parameter takes precedence."""
        detector = WorkspaceDetector()
        
        # Use override
        workspace = detector.detect_workspace(override=str(git_repo))
        
        assert workspace == git_repo
    
    def test_fallback_to_cwd(self, temp_dir):
        """Test fallback to current working directory when not in git repo."""
        # Create directory that's not a git repo
        non_git_dir = temp_dir / 'not_git'
        non_git_dir.mkdir()
        
        original_cwd = Path.cwd()
        try:
            os.chdir(non_git_dir)
            
            detector = WorkspaceDetector()
            workspace = detector.detect_workspace()
            
            assert workspace == non_git_dir
        finally:
            os.chdir(original_cwd)
    
    def test_cache_stats(self, git_repo):
        """Test cache statistics."""
        detector = WorkspaceDetector(cache_ttl=60)
        
        stats = detector.get_cache_stats()
        
        assert 'entries' in stats
        assert 'total_hits' in stats
        assert 'ttl' in stats
        assert stats['ttl'] == 60
