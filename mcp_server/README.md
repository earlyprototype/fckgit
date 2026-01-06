# fckgit MCP Server - Technical Documentation

## Architecture Overview

The fckgit MCP server provides AI-powered git operations through the Model Context Protocol. This document describes the technical architecture, design decisions, and implementation details.

## Core Components

### 1. Workspace Detection (`workspace.py`)

**Purpose**: Robust, secure detection of git repository workspace.

**Key Features**:
- Thread-safe workspace detection with locking
- LRU cache with configurable TTL (default: 60s)
- Multiple detection strategies with fallback
- Security validation (path traversal, permissions)
- Support for complex git configurations

**Detection Strategy**:
1. WORKSPACE_FOLDER_PATHS environment variable (automatic - provided by Cursor/VSCode)
2. PROJECT_ROOT environment variable (manual override)
3. Git command (`git rev-parse --show-toplevel`)
4. Current working directory (fallback)

**Why this approach?**

**Auto-Detection for Modern IDEs:** Cursor and VSCode automatically provide the workspace path via the `WORKSPACE_FOLDER_PATHS` environment variable. This means the MCP server automatically works with the current project without any configuration!

**Manual Configuration for Others:** For IDEs/clients that don't provide workspace info (Claude Desktop, JetBrains, Neovim, etc.), users set `cwd` in the MCP config, and the server uses `git rev-parse --show-toplevel` to find the actual git root.

**Always Secure:** All paths are validated with security checks (path traversal, permissions, existence) before use.

### 2. Git Utilities (`git_utils.py`)

**Purpose**: Handle git edge cases that manual `.git` detection misses.

**Supported Configurations**:
- **Git Worktrees**: Where `.git` is a file pointing to actual git directory
- **Git Submodules**: Nested repositories within a parent repository
- **Bare Repositories**: Repositories without working tree
- **Nested Repositories**: Multiple git repos in directory tree

**Key Functions**:
- `detect_git_repo_type()`: Comprehensive repository type detection
- `check_git_available()`: Verify git command availability
- `get_git_version()`: Get git version for debugging

### 3. Platform Utilities (`platform_utils.py`)

**Purpose**: Handle platform-specific subprocess execution safely.

**Security Features**:
- **Never uses `shell=True`**: Prevents command injection
- **Command validation**: Checks for shell metacharacters
- **Proper argument handling**: Uses list format, not strings

**Windows-Specific Handling**:
- CREATE_NO_WINDOW flag (prevents console windows)
- CREATE_NEW_PROCESS_GROUP for background processes
- UNC path support (`\\server\share`)
- Long path support (`\\?\` prefix for >260 chars)

**Unix-Specific Handling**:
- `start_new_session` for background processes
- Proper signal handling

### 4. Logging Configuration (`logging_config.py`)

**Purpose**: Structured logging without interfering with MCP stdio protocol.

**Key Points**:
- Logs to **stderr** (stdout is reserved for MCP protocol)
- Structured logging with context (key=value pairs)
- Configurable log levels via LOG_LEVEL env var
- Module-specific log level control

### 5. Git Command Execution

**Improved `run_git_command()` function**:

```python
async def run_git_command(
    cmd: list[str],
    cwd: Optional[Path] = None,
    timeout: float = 15.0,
    retry: int = 1
) -> GitCommandResult
```

**Improvements over old implementation**:
- Removes `shell=True` (security risk)
- Adds retry logic for transient failures
- Returns rich `GitCommandResult` object with timing
- Comprehensive error handling
- Detailed logging for debugging
- Security validation of commands

## Edge Cases Handled

### Git Worktrees

**Problem**: In worktrees, `.git` is a file (not directory) pointing to the actual git directory.

**Solution**: Use `git rev-parse --git-common-dir` to detect worktrees and handle appropriately.

### Git Submodules

**Problem**: Submodules are nested git repositories. Need to determine if user wants to work on submodule or parent.

**Solution**: Use `git rev-parse --show-superproject-working-tree` to detect submodules and provide information about both.

### Bare Repositories

**Problem**: Bare repositories have no working tree, so standard operations might fail.

**Solution**: Use `git rev-parse --is-bare-repository` to detect and handle differently.

### Nested Repositories

**Problem**: Multiple git repositories in directory tree. Which one to use?

**Solution**: Prefer closest repository to current working directory.

### Long Paths on Windows

**Problem**: Windows has 260-character path limit (MAX_PATH).

**Solution**: Add `\\?\` prefix for paths >260 characters.

### UNC Paths

**Problem**: Network paths (`\\server\share`) need special handling on Windows.

**Solution**: Convert to `\\?\UNC\server\share` format for long UNC paths.

## Performance Optimizations

### Caching Strategy

1. **Workspace Detection Cache**:
   - TTL: 60 seconds (configurable)
   - Thread-safe with RLock
   - Tracks cache hits for monitoring

2. **When to Invalidate**:
   - After 60 seconds (TTL)
   - On explicit errors (repo moved/deleted)
   - Manual invalidation via `invalidate_cache()`

3. **Cache Effectiveness**:
   - First call: ~50ms (git command execution)
   - Cached calls: <1ms (memory lookup)

### Git Command Optimization

1. **Use `--no-optional-locks` flag** (when appropriate):
   - Reduces lock contention
   - Faster operations on busy repositories

2. **Batch operations where possible**:
   - Combine multiple checks into single command
   - Use porcelain output for parsing

## Security Considerations

### Path Validation

```python
def _sanitize_path(self, path: str) -> Path:
    # 1. Resolve symlinks
    resolved = Path(path).resolve(strict=False)
    
    # 2. Check for path traversal
    if '..' in resolved.parts:
        raise InvalidWorkspaceError("Path traversal detected")
    
    # 3. Validate exists and is directory
    # 4. Check permissions (readable, executable)
```

### Command Injection Prevention

- **Never use `shell=True`**: All commands use list format
- **Validate command structure**: Check for shell metacharacters
- **Proper escaping**: Let Python handle argument escaping

### Error Handling

- **Don't fail silently**: Always log errors
- **Clear error messages**: Help users diagnose issues
- **Graceful degradation**: Fall back to safe defaults

## Testing Strategy

### Unit Tests

- **workspace.py**: 90%+ coverage
  - Cache functionality
  - Security validation
  - Error cases

- **git_utils.py**: 85%+ coverage
  - All git repository types
  - Edge cases (worktrees, submodules)

- **platform_utils.py**: 80%+ coverage
  - Platform-specific logic
  - Windows/Unix differences

### Integration Tests

- Real git repository operations
- Multi-threaded access
- Cache expiry scenarios

### Test Fixtures

- `git_repo`: Regular git repository
- `git_worktree`: Git worktree
- `git_submodule`: Git submodule
- `bare_repo`: Bare git repository

## Known Limitations

1. **One workspace per MCP server instance**: Can't dynamically switch between projects
   - **Workaround**: Configure multiple MCP server instances with different working directories

2. **Requires git command available**: Won't work without git in PATH
   - **Workaround**: Install git or set PATH appropriately

3. **Cache may become stale**: If repository is moved/deleted while server running
   - **Workaround**: Restart MCP server or invalidate cache

## Configuration

### Environment Variables

- `PROJECT_ROOT`: Override workspace detection (highest priority)
- `GEMINI_API_KEY`: Required for AI commit messages
- `LOG_LEVEL`: Set logging level (DEBUG, INFO, WARNING, ERROR)

### MCP Configuration

```json
{
  "mcpServers": {
    "fckgit": {
      "command": "python",
      "args": ["-m", "mcp_server"],
      "cwd": "/path/to/your/project",  // Sets working directory
      "env": {
        "GEMINI_API_KEY": "your_key",
        "LOG_LEVEL": "INFO"
      }
    }
  }
}
```

## Troubleshooting

### Server starts in wrong directory

**Symptom**: Operations happen in wrong git repository

**Solution**:
1. Check `cwd` in MCP configuration
2. Set `PROJECT_ROOT` environment variable
3. Use `fckgit_debug` tool to see detected workspace

### Git commands fail

**Symptom**: "git not found" or timeout errors

**Solution**:
1. Verify git is in PATH
2. Check file permissions on workspace
3. Review logs in stderr for details

### Performance issues

**Symptom**: Slow git operations

**Solution**:
1. Check cache hit rate via `fckgit_debug`
2. Increase cache TTL if appropriate
3. Check network drive latency (if applicable)

## Future Improvements

1. **Dynamic workspace switching**: Accept workspace path in tool calls
2. **Workspace metadata caching**: Cache more git metadata
3. **Background refresh**: Refresh cache before expiry
4. **Metrics collection**: Track performance and cache effectiveness
5. **Custom git command timeout**: Per-command timeout configuration

## Contributing

When contributing to the MCP server:

1. **Maintain test coverage**: Aim for 90%+ on new code
2. **Add logging**: Use structured logger for debugging
3. **Handle errors gracefully**: Don't fail silently
4. **Document edge cases**: Update this README
5. **Security first**: Never use `shell=True`, validate inputs

## License

MIT License - see LICENSE file for details.
