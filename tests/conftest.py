"""
Pytest configuration and fixtures for fckgit tests.
"""

import os
import subprocess
import tempfile
from pathlib import Path
from typing import Generator

import pytest


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def git_repo(temp_dir: Path) -> Path:
    """Create a temporary git repository for testing."""
    # Initialize git repo
    subprocess.run(
        ['git', 'init'],
        cwd=str(temp_dir),
        check=True,
        capture_output=True
    )
    
    # Configure git
    subprocess.run(
        ['git', 'config', 'user.email', 'test@example.com'],
        cwd=str(temp_dir),
        check=True,
        capture_output=True
    )
    subprocess.run(
        ['git', 'config', 'user.name', 'Test User'],
        cwd=str(temp_dir),
        check=True,
        capture_output=True
    )
    
    # Create initial commit
    (temp_dir / 'README.md').write_text('# Test Repo\n')
    subprocess.run(
        ['git', 'add', 'README.md'],
        cwd=str(temp_dir),
        check=True,
        capture_output=True
    )
    subprocess.run(
        ['git', 'commit', '-m', 'Initial commit'],
        cwd=str(temp_dir),
        check=True,
        capture_output=True
    )
    
    return temp_dir


@pytest.fixture
def git_worktree(git_repo: Path, temp_dir: Path) -> Path:
    """Create a git worktree for testing."""
    worktree_path = temp_dir / 'worktree'
    
    # Create worktree
    subprocess.run(
        ['git', 'worktree', 'add', str(worktree_path), 'HEAD'],
        cwd=str(git_repo),
        check=True,
        capture_output=True
    )
    
    return worktree_path


@pytest.fixture
def git_submodule(git_repo: Path, temp_dir: Path) -> Path:
    """Create a git submodule for testing."""
    # Create another git repo to use as submodule
    submodule_source = temp_dir / 'submodule_source'
    submodule_source.mkdir()
    
    subprocess.run(
        ['git', 'init'],
        cwd=str(submodule_source),
        check=True,
        capture_output=True
    )
    subprocess.run(
        ['git', 'config', 'user.email', 'test@example.com'],
        cwd=str(submodule_source),
        check=True,
        capture_output=True
    )
    subprocess.run(
        ['git', 'config', 'user.name', 'Test User'],
        cwd=str(submodule_source),
        check=True,
        capture_output=True
    )
    
    (submodule_source / 'file.txt').write_text('submodule content')
    subprocess.run(
        ['git', 'add', 'file.txt'],
        cwd=str(submodule_source),
        check=True,
        capture_output=True
    )
    subprocess.run(
        ['git', 'commit', '-m', 'Submodule commit'],
        cwd=str(submodule_source),
        check=True,
        capture_output=True
    )
    
    # Add as submodule
    # Configure git to allow file:// protocol (needed for testing)
    subprocess.run(
        ['git', 'config', '--global', 'protocol.file.allow', 'always'],
        check=False,
        capture_output=True
    )
    
    submodule_path = git_repo / 'submodule'
    result = subprocess.run(
        ['git', 'submodule', 'add', str(submodule_source), 'submodule'],
        cwd=str(git_repo),
        capture_output=True
    )
    
    # If submodule add failed (e.g., security policy), skip this test
    if result.returncode != 0:
        pytest.skip("Cannot create submodule (git security policy)")
    
    subprocess.run(
        ['git', 'commit', '-m', 'Add submodule'],
        cwd=str(git_repo),
        check=True,
        capture_output=True
    )
    
    return submodule_path


@pytest.fixture
def bare_repo(temp_dir: Path) -> Path:
    """Create a bare git repository for testing."""
    bare_path = temp_dir / 'bare.git'
    
    subprocess.run(
        ['git', 'init', '--bare', str(bare_path)],
        check=True,
        capture_output=True
    )
    
    return bare_path


@pytest.fixture
def mock_env(monkeypatch):
    """Fixture for mocking environment variables."""
    class MockEnv:
        def set(self, key: str, value: str):
            monkeypatch.setenv(key, value)
        
        def clear(self, key: str):
            monkeypatch.delenv(key, raising=False)
    
    return MockEnv()
