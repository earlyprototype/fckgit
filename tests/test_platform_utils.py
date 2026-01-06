"""
Tests for platform utilities module.
"""

import subprocess
import sys
from pathlib import Path

import pytest

from mcp_server.platform_utils import (
    get_subprocess_kwargs,
    normalize_path,
    is_unc_path,
    check_subprocess_security,
    get_platform_info,
)


class TestPlatformUtils:
    """Tests for platform utilities."""
    
    def test_get_subprocess_kwargs_basic(self):
        """Test basic subprocess kwargs."""
        kwargs = get_subprocess_kwargs()
        
        assert 'stdin' in kwargs
        assert kwargs['stdin'] == subprocess.DEVNULL
        assert kwargs['shell'] is False
        assert kwargs['text'] is True
    
    def test_get_subprocess_kwargs_windows(self):
        """Test Windows-specific subprocess kwargs."""
        kwargs = get_subprocess_kwargs()
        
        if sys.platform == 'win32':
            assert 'creationflags' in kwargs
        else:
            # On Unix, different handling
            assert True
    
    def test_get_subprocess_kwargs_background(self):
        """Test background process kwargs."""
        kwargs = get_subprocess_kwargs(is_background=True)
        
        assert kwargs['shell'] is False
        
        if sys.platform == 'win32':
            assert 'creationflags' in kwargs
        else:
            assert 'start_new_session' in kwargs
    
    def test_normalize_path(self, temp_dir):
        """Test path normalization."""
        test_path = temp_dir / 'test'
        test_path.mkdir()
        
        normalized = normalize_path(str(test_path))
        
        assert isinstance(normalized, Path)
        assert normalized.exists()
        assert normalized.is_absolute()
    
    def test_is_unc_path_windows(self):
        """Test UNC path detection on Windows."""
        if sys.platform == 'win32':
            assert is_unc_path(Path('\\\\server\\share'))
            assert not is_unc_path(Path('C:\\Users'))
        else:
            # On Unix, always returns False
            assert not is_unc_path(Path('/home/user'))
    
    def test_check_subprocess_security_valid(self):
        """Test subprocess security check with valid command."""
        cmd = ['git', 'status']
        
        # Should not raise
        check_subprocess_security(cmd)
    
    def test_check_subprocess_security_empty(self):
        """Test subprocess security check with empty command."""
        with pytest.raises(ValueError):
            check_subprocess_security([])
    
    def test_check_subprocess_security_not_list(self):
        """Test subprocess security check with non-list command."""
        with pytest.raises(ValueError):
            check_subprocess_security('git status')
    
    def test_get_platform_info(self):
        """Test getting platform information."""
        info = get_platform_info()
        
        assert 'system' in info
        assert 'python_version' in info
        assert isinstance(info['system'], str)
