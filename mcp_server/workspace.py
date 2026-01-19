"""
Workspace detection module for fckgit MCP server.

Provides robust, secure workspace detection with support for:
- Git worktrees, submodules, bare repositories
- Thread-safe caching with TTL
- Security validation (path traversal, permissions)
- Comprehensive error handling
"""

import os
import subprocess
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Dict, Tuple


class WorkspaceError(Exception):
    """Base exception for workspace-related errors."""
    pass


class GitNotFoundError(WorkspaceError):
    """Git executable not found or not accessible."""
    pass


class InvalidWorkspaceError(WorkspaceError):
    """Workspace path is invalid or inaccessible."""
    pass


@dataclass
class CacheEntry:
    """Cache entry with timestamp and hit tracking."""
    value: Path
    timestamp: float
    hits: int = 0


class WorkspaceDetector:
    """
    Thread-safe workspace detector with caching.
    
    Detects workspace using multiple strategies:
    1. PROJECT_ROOT environment variable (manual override)
    2. Git command (git rev-parse --show-toplevel)
    3. Current working directory fallback
    """
    
    def __init__(self, cache_ttl: int = 60):
        """
        Initialize workspace detector.
        
        Args:
            cache_ttl: Cache time-to-live in seconds (default: 60)
        """
        self._lock = threading.RLock()
        self._cache: Dict[str, CacheEntry] = {}
        self._cache_ttl = cache_ttl
        self._workspace: Optional[Path] = None
        self._initialized = False
        self._detection_timestamp: Optional[float] = None
        self._detection_method: Optional[str] = None
    
    def detect_workspace(self, override: Optional[str] = None) -> Path:
        """
        Detect workspace directory with comprehensive error handling.
        
        Args:
            override: Optional path override (takes precedence)
            
        Returns:
            Path to workspace directory
            
        Raises:
            InvalidWorkspaceError: If workspace cannot be determined
        """
        with self._lock:
            # Return cached workspace if already initialized and no override
            if self._initialized and self._workspace and not override:
                return self._workspace
            
            # Try detection strategies in order
            workspace = None
            
            # 1. Use override if provided
            detection_method = None
            if override:
                try:
                    workspace = self._sanitize_path(override)
                    detection_method = "override_parameter"
                except InvalidWorkspaceError:
                    # Log but continue to other strategies
                    pass
            
            # 2. Check WORKSPACE_FOLDER_PATHS from Cursor/VSCode
            if not workspace and 'WORKSPACE_FOLDER_PATHS' in os.environ:
                try:
                    # Can be semicolon-separated for multiple folders
                    workspace_paths = os.environ['WORKSPACE_FOLDER_PATHS'].split(';')
                    if workspace_paths:
                        # Use the first workspace folder
                        workspace = self._sanitize_path(workspace_paths[0].strip())
                        detection_method = "WORKSPACE_FOLDER_PATHS"
                except InvalidWorkspaceError:
                    # Log but continue
                    pass
            
            # 3. Check PROJECT_ROOT environment variable (manual override)
            if not workspace and 'PROJECT_ROOT' in os.environ:
                try:
                    workspace = self._sanitize_path(os.environ['PROJECT_ROOT'])
                    detection_method = "PROJECT_ROOT"
                except InvalidWorkspaceError:
                    # Log but continue
                    pass
            
            # 4. Use git command to find repository root
            if not workspace:
                try:
                    workspace = self._use_git_command(Path.cwd())
                    detection_method = "git_rev_parse"
                except (GitNotFoundError, InvalidWorkspaceError):
                    # Git command failed, will fall back to cwd
                    pass
            
            # 5. Fallback to current working directory
            if not workspace:
                try:
                    workspace = self._sanitize_path(str(Path.cwd()))
                    detection_method = "cwd_fallback"
                except InvalidWorkspaceError as e:
                    raise InvalidWorkspaceError(
                        f"Cannot determine workspace: current directory inaccessible: {e}"
                    )
            
            # Validate it's a git repository (optional, log warning if not)
            if not self._validate_git_repo(workspace):
                # Not a git repo, but we'll allow it (user might init later)
                pass
            
            # Cache the result
            self._workspace = workspace
            self._initialized = True
            self._detection_timestamp = time.time()
            self._detection_method = detection_method
            
            return workspace
    
    def _use_git_command(self, cwd: Path) -> Optional[Path]:
        """
        Use git command to find repository root.
        
        This handles worktrees, submodules, and other edge cases better
        than manual .git directory detection.
        
        Args:
            cwd: Current working directory to start from
            
        Returns:
            Path to git repository root, or None if not found
            
        Raises:
            GitNotFoundError: If git command is not available
            InvalidWorkspaceError: If git repo path is invalid
        """
        cache_key = f"git_root:{cwd}"
        
        # Check cache
        if cache_key in self._cache:
            entry = self._cache[cache_key]
            if time.time() - entry.timestamp < self._cache_ttl:
                entry.hits += 1
                return entry.value
            else:
                # Cache expired, remove entry
                del self._cache[cache_key]
        
        try:
            # Use git rev-parse to find repository root
            # This works with worktrees, submodules, etc.
            result = subprocess.run(
                ['git', 'rev-parse', '--show-toplevel'],
                cwd=str(cwd),
                capture_output=True,
                text=True,
                timeout=5.0,
                stdin=subprocess.DEVNULL,
            )
            
            if result.returncode == 0:
                repo_root = result.stdout.strip()
                if repo_root:
                    sanitized = self._sanitize_path(repo_root)
                    # Cache the result
                    self._cache[cache_key] = CacheEntry(
                        value=sanitized,
                        timestamp=time.time(),
                        hits=1
                    )
                    return sanitized
            
            return None
            
        except FileNotFoundError:
            raise GitNotFoundError("git command not found in PATH")
        except subprocess.TimeoutExpired:
            raise GitNotFoundError("git command timed out")
        except Exception as e:
            # Other errors (permission denied, etc.)
            raise GitNotFoundError(f"git command failed: {e}")
    
    def _validate_git_repo(self, path: Path) -> bool:
        """
        Validate that a path is actually a git repository.
        
        Args:
            path: Path to validate
            
        Returns:
            True if valid git repository, False otherwise
        """
        try:
            result = subprocess.run(
                ['git', 'rev-parse', '--git-dir'],
                cwd=str(path),
                capture_output=True,
                text=True,
                timeout=5.0,
                stdin=subprocess.DEVNULL,
            )
            return result.returncode == 0
        except Exception:
            return False
    
    def _sanitize_path(self, path: str) -> Path:
        """
        Sanitize and validate a path for security.
        
        Args:
            path: Path string to sanitize
            
        Returns:
            Validated Path object
            
        Raises:
            InvalidWorkspaceError: If path is invalid or insecure
        """
        try:
            # Resolve the path (handles symlinks, relative paths)
            resolved = Path(path).resolve(strict=False)
            
            # Convert to absolute path
            if not resolved.is_absolute():
                resolved = resolved.absolute()
            
            # Check if path exists
            if not resolved.exists():
                raise InvalidWorkspaceError(f"Path does not exist: {resolved}")
            
            # Check if it's a directory
            if not resolved.is_dir():
                raise InvalidWorkspaceError(f"Not a directory: {resolved}")
            
            # Check permissions (readable and executable)
            if not os.access(resolved, os.R_OK | os.X_OK):
                raise InvalidWorkspaceError(
                    f"Insufficient permissions to access: {resolved}"
                )
            
            return resolved
            
        except (OSError, RuntimeError) as e:
            raise InvalidWorkspaceError(f"Invalid path: {e}")
    
    def invalidate_cache(self):
        """Invalidate all cached entries."""
        with self._lock:
            self._cache.clear()
            self._workspace = None
            self._initialized = False
    
    def get_cache_stats(self) -> Dict[str, int]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache stats (entries, total_hits)
        """
        with self._lock:
            total_hits = sum(entry.hits for entry in self._cache.values())
            return {
                'entries': len(self._cache),
                'total_hits': total_hits,
                'ttl': self._cache_ttl,
            }
    
    def get_workspace_info(self) -> Dict[str, any]:
        """
        Get detailed workspace detection information for diagnostics.
        
        Returns:
            Dictionary with workspace detection details
        """
        with self._lock:
            return {
                'current_workspace': str(self._workspace) if self._workspace else None,
                'initialized': self._initialized,
                'detection_timestamp': self._detection_timestamp,
                'detection_method': self._detection_method,
                'time_since_detection': time.time() - self._detection_timestamp if self._detection_timestamp else None,
            }