# fckgit MCP Server - Technical Documentation

## Architecture Overview

The fckgit MCP server provides AI-powered git operations through the Model Context Protocol. This document describes the technical architecture, design decisions, and implementation details.

## Core Components

### 1. Workspace Detection (`workspace.py`)

**Purpose**: Robust, secure detection of git repository workspace.

**Key Features**:
- Thread-safe workspace detection with locking
- Directory-keyed cache for repeated Git root lookups within one detector
- Multiple detection strategies with fallback
- Directory existence and access checks
- Support for complex git configurations

**Detection Strategy**:

1. Optional `repo_path` argument on the tool call
2. First directory in `WORKSPACE_FOLDER_PATHS`
3. `PROJECT_ROOT` environment variable
4. Git root from the server's current working directory, or that directory itself

**Why this approach?**

Each call reads the workspace settings visible to the server. An editor that keeps the server environment fixed can pass `repo_path` when the active project changes.

**Manual Configuration for Others:** For IDEs/clients that don't provide workspace info (Claude Desktop, JetBrains, Neovim, etc.), users set `cwd` in the MCP config, and the server uses `git rev-parse --show-toplevel` to find the actual git root.

The detector resolves symlinks and checks that the selected path is an existing directory with read and search access. When Git reports a different worktree root, both locations must resolve to the same Git directory.

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

Each Git subprocess receives the validated Git directory and worktree.
Discovery discards inherited repository and index selectors and ignores
command-level worktree redirects. After discovery, Git evaluates command-level
config includes against the selected repository, preserving signing and push policy.

The server records the target of each watcher it starts. For an external
watcher, it checks the process environment and asks Git for the effective
Git directory and worktree. After a restart, discovery also recognizes the
command configuration the server passed to the watcher at launch. Status
and stop skip a watcher if its environment is inaccessible or its Git
context cannot be verified.

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
    cwd: Path,
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

**Solution**: Discover the closest repository from the selected directory. Reject a `core.worktree` layout if starting Git from the reported root would select a different Git directory.

### Long Paths on Windows

**Problem**: Windows has 260-character path limit (MAX_PATH).

**Solution**: Add `\\?\` prefix for paths >260 characters.

### UNC Paths

**Problem**: Network paths (`\\server\share`) need special handling on Windows.

**Solution**: Convert to `\\?\UNC\server\share` format for long UNC paths.

## Performance Optimizations

### Caching Strategy

Each MCP call creates its own workspace detector. All steps in that call
reuse the resolved directory. The detector's Git root cache lasts for the
life of the detector and supports a configurable TTL for repeated lookups.

### Git Command Optimization

1. **Use `--no-optional-locks` flag** (when appropriate):
   - Reduces lock contention
   - Faster operations on busy repositories

2. **Batch operations where possible**:
   - Combine multiple checks into single command
   - Use porcelain output for parsing

## Security Considerations

### Path Validation

Relative paths and symlinks resolve from the server's working directory.
Clients can pass an absolute `repo_path` to identify a project independently
of that directory.

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

Git must be available on the server's PATH.

## Configuration

### Environment Variables

- `PROJECT_ROOT` supplies the default directory when `WORKSPACE_FOLDER_PATHS` is unset.
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
Check network drive latency when the repository is on a shared drive.

## Future Improvements

1. **Workspace metadata caching**: Cache more git metadata
2. **Background refresh**: Refresh cache before expiry
3. **Metrics collection**: Track performance and cache effectiveness
4. **Custom git command timeout**: Per-command timeout configuration

## Contributing

When contributing to the MCP server:

1. **Maintain test coverage**: Aim for 90%+ on new code
2. **Add logging**: Use structured logger for debugging
3. **Handle errors gracefully**: Don't fail silently
4. **Document edge cases**: Update this README
5. **Security first**: Never use `shell=True`, validate inputs

## License

MIT License - see LICENSE file for details.
