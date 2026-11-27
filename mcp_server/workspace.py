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
from typing import Optional, Dict

from .git_utils import GitTarget, GitUtilsError, discover_git_target


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
    value: GitTarget
    timestamp: float
    hits: int = 0


class WorkspaceDetector:
    """
    Thread-safe workspace detector with caching.
    
    Resolve the explicit path, first editor folder, project root, or current
    directory (in that order) to its Git worktree root when available.
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
        workspace, _ = self.resolve_workspace(override)
        return workspace

    def resolve_workspace(self, override: Optional[str] = None) -> tuple[Path, Optional[GitTarget]]:
        """Select the workspace and capture its repository for this call."""
        with self._lock:
            if override is not None:
                selected = override
                detection_method = "override_parameter"
            elif "WORKSPACE_FOLDER_PATHS" in os.environ:
                selected = os.environ["WORKSPACE_FOLDER_PATHS"].split(";", 1)[0].strip()
                detection_method = "WORKSPACE_FOLDER_PATHS"
            elif "PROJECT_ROOT" in os.environ:
                selected = os.environ["PROJECT_ROOT"]
                detection_method = "PROJECT_ROOT"
            else:
                selected = str(Path.cwd())
                detection_method = "cwd_fallback"

            workspace = self._sanitize_path(selected)
            target = None
            try:
                target = self._use_git_command(workspace)
                if target and target.worktree:
                    workspace = target.worktree
                    if detection_method == "cwd_fallback":
                        detection_method = "git_rev_parse"
            except GitNotFoundError:
                pass
            
            # Record the last detection for diagnostics.
            self._workspace = workspace
            self._initialized = True
            self._detection_timestamp = time.time()
            self._detection_method = detection_method
            
            return workspace, target
    
    def _use_git_command(self, cwd: Path) -> Optional[GitTarget]:
        """
        Use git command to find repository root.
        
        This handles worktrees, submodules, and other edge cases better
        than manual .git directory detection.
        
        Args:
            cwd: Current working directory to start from
            
        Returns:
            Git directory and optional worktree, or None if not found
            
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
            target = discover_git_target(cwd)
            if target is not None:
                if target.worktree:
                    self._sanitize_path(str(target.worktree))
                self._cache[cache_key] = CacheEntry(
                    value=target,
                    timestamp=time.time(),
                    hits=1
                )
                return target
            
            return None
            
        except GitUtilsError as e:
            raise InvalidWorkspaceError(str(e)) from e
        except FileNotFoundError:
            raise GitNotFoundError("git command not found in PATH")
        except subprocess.TimeoutExpired:
            raise GitNotFoundError("git command timed out")
        except OSError as e:
            raise GitNotFoundError(f"git command failed: {e}")
    
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
            if not isinstance(path, str) or not path.strip():
                raise InvalidWorkspaceError("Expected a non-empty directory path")
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
            
        except (OSError, RuntimeError, ValueError) as e:
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
