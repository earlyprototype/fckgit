"""
Platform-specific utilities for handling OS differences.

Provides:
- Secure subprocess configuration (no shell=True)
- Windows-specific handling (UNC paths, long paths, process flags)
- Cross-platform path normalization
"""

import subprocess
import sys
from pathlib import Path
from typing import Dict, Any


def get_subprocess_kwargs(
    is_background: bool = False,
    timeout: float = 15.0,
    capture_output: bool = True,
) -> Dict[str, Any]:
    """
    Get platform-specific subprocess kwargs.
    
    IMPORTANT: Never uses shell=True for security.
    Always passes commands as lists, not strings.
    
    Args:
        is_background: Whether process should run in background
        timeout: Command timeout in seconds
        capture_output: Whether to capture stdout/stderr
        
    Returns:
        Dictionary of kwargs for subprocess.run/Popen
    """
    kwargs: Dict[str, Any] = {
        'stdin': subprocess.DEVNULL,
        'timeout': timeout,
        'text': True,
        'shell': False,  # NEVER use shell=True (security risk)
    }
    
    if capture_output:
        kwargs['stdout'] = subprocess.PIPE
        kwargs['stderr'] = subprocess.PIPE
    
    # Windows-specific configuration
    if sys.platform == 'win32':
        # CREATE_NO_WINDOW = 0x08000000
        # Prevents console window from appearing
        flags = 0x08000000
        
        if is_background:
            # CREATE_NEW_PROCESS_GROUP = 0x00000200
            # Allows process to run independently
            flags |= 0x00000200
        
        kwargs['creationflags'] = flags
    elif is_background:
        # Unix: use start_new_session for background processes
        kwargs['start_new_session'] = True
    
    return kwargs


def normalize_path(path: str) -> Path:
    r"""
    Normalize path for current platform.
    
    Handles:
    - Windows UNC paths (\\server\\share)
    - Windows long paths (>260 chars with \\?\\prefix)
    - Forward/backward slash conversion
    - Symlink resolution
    
    Args:
        path: Path string to normalize
        
    Returns:
        Normalized Path object
    """
    path_obj = Path(path)
    
    # Resolve symlinks and make absolute
    try:
        resolved = path_obj.resolve(strict=False)
    except (OSError, RuntimeError):
        # If resolution fails, just make it absolute
        resolved = path_obj.absolute()
    
    # On Windows, handle long paths
    if sys.platform == 'win32':
        path_str = str(resolved)
        
        # If path is longer than 260 chars and not already prefixed
        if len(path_str) > 260 and not path_str.startswith('\\\\?\\'):
            # Add long path prefix
            if path_str.startswith('\\\\'):
                # UNC path: \\server\share -> \\?\UNC\server\share
                resolved = Path('\\\\?\\UNC\\' + path_str[2:])
            else:
                # Regular path: C:\... -> \\?\C:\...
                resolved = Path('\\\\?\\' + path_str)
    
    return resolved


def is_unc_path(path: Path) -> bool:
    r"""
    Check if path is a Windows UNC path.
    
    Args:
        path: Path to check
        
    Returns:
        True if UNC path (\\server\\share format)
    """
    if sys.platform != 'win32':
        return False
    
    path_str = str(path)
    return path_str.startswith('\\\\') and not path_str.startswith('\\\\?\\')


def escape_command_arg(arg: str) -> str:
    """
    Escape command argument for safe subprocess execution.
    
    Note: This should rarely be needed since we use shell=False.
    Mainly for logging/debugging purposes.
    
    Args:
        arg: Argument to escape
        
    Returns:
        Escaped argument
    """
    # For shell=False, Python handles escaping automatically
    # This is mainly for display/logging
    if sys.platform == 'win32':
        # Windows: quote if contains space or special chars
        if any(c in arg for c in ' \t\n"'):
            # Escape quotes and wrap in quotes
            escaped = arg.replace('"', '\\"')
            return f'"{escaped}"'
    else:
        # Unix: use shlex for display
        import shlex
        return shlex.quote(arg)
    
    return arg


def get_platform_info() -> Dict[str, Any]:
    """
    Get platform information for debugging.
    
    Returns:
        Dictionary with platform details
    """
    import platform
    
    info = {
        'system': platform.system(),
        'release': platform.release(),
        'version': platform.version(),
        'machine': platform.machine(),
        'python_version': platform.python_version(),
    }
    
    # Windows-specific info
    if sys.platform == 'win32':
        try:
            import winreg
            # Get Windows version from registry
            key = winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r'SOFTWARE\Microsoft\Windows NT\CurrentVersion'
            )
            info['windows_product_name'] = winreg.QueryValueEx(key, 'ProductName')[0]
            info['windows_build'] = winreg.QueryValueEx(key, 'CurrentBuild')[0]
            winreg.CloseKey(key)
        except Exception:
            pass
    
    return info


def check_subprocess_security(cmd: list) -> None:
    """
    Validate subprocess command for security issues.
    
    Raises ValueError if command appears unsafe.
    
    Args:
        cmd: Command list to validate
        
    Raises:
        ValueError: If command has security issues
    """
    if not cmd:
        raise ValueError("Empty command")
    
    if not isinstance(cmd, list):
        raise ValueError("Command must be a list, not string (shell injection risk)")
    
    # Check for shell metacharacters that might indicate
    # someone is trying to use shell=True patterns
    dangerous_patterns = ['&&', '||', ';', '|', '>', '<', '`', '$']
    
    for arg in cmd:
        if not isinstance(arg, str):
            raise ValueError(f"Command arg must be string, got {type(arg)}")
        
        # Warn if shell metacharacters found (might be accidental)
        for pattern in dangerous_patterns:
            if pattern in arg:
                # This isn't necessarily dangerous with shell=False,
                # but might indicate a mistake
                import logging
                logging.warning(
                    f"Command argument contains shell metacharacter '{pattern}': {arg}. "
                    "This is safe with shell=False but might not work as expected."
                )
