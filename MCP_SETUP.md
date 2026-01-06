# fckgit MCP Server Setup

Let AI assistants (Cursor, Claude Desktop) auto-commit your code.

## Installation

**Option 1: One Command (Recommended)**

```bash
# Install fckgit with MCP support
pip install -e ".[mcp]"
```

**Option 2: Use Install Script**

```bash
.\scripts\install_mcp.ps1    # Windows
./scripts/install_mcp.sh     # Mac/Linux/iPad
```

**What This Does:**
- Installs fckgit as a package (makes `mcp_server` module available)
- Installs MCP dependencies (`mcp>=1.0.0`, `psutil>=5.9.0`)
- Sets up everything needed for the MCP server to run

## Configuration

### Cursor IDE (Automatic Detection)

The MCP server **automatically detects your Cursor workspace** - just add your API key and go!

Add to your Cursor MCP settings (File > Preferences > Cursor Settings > MCP):

```json
{
  "mcpServers": {
    "fckgit": {
      "command": "python",
      "args": ["-m", "mcp_server"],
      "env": {
        "GEMINI_API_KEY": "your_gemini_api_key_here"
      }
    }
  }
}
```

**That's it!** Switch between Cursor projects and fckgit automatically follows. No `cwd` or `PROJECT_ROOT` configuration needed.

### Claude Desktop

**Mac:** `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "fckgit": {
      "command": "python",
      "args": ["-m", "mcp_server"],
      "cwd": "/path/to/your/project",
      "env": {
        "GEMINI_API_KEY": "your_api_key_here"
      }
    }
  }
}
```

**Note:** Claude Desktop may not auto-detect workspaces like Cursor does, so setting `cwd` is recommended.

## Available Tools

Tell your AI assistant:

**"Blastoff!"** - Start automatic watch mode (auto-commits everything)
- `fckgit_blastoff` - Launch watch mode
  - `cooldown` (optional): Time in seconds between commits (default: 30)
  - `faang_mode` (optional): Enable Silicon Valley professional commits (default: false)
- `fckgit_watch_status` - Check if running
- `fckgit_stop_watch` - Stop watch mode

**"Silicon Valley mode"** - Professional FAANG-tier commits
- `fckgit_silicon_valley` - Commit with professional message
- `fckgit_professionalize` - Transform casual message to professional

**Manual Operations:**
- `fckgit_status` - Get git status
- `fckgit_commit` - Auto-commit with AI message
- `fckgit_commit_with_message` - Commit with specific message
- `fckgit_push` - Push to remote
- `fckgit_cleanup_lock` - Clean up git lock files

## Testing

1. Restart your AI assistant (Cursor/Claude Desktop)
2. In a git repository, ask: "What's the git status?"
3. If it works, you're good to go

## Troubleshooting

**"Not a git repository"**
- Make sure you're working in a git repository
- Run `git init` to initialise your project as a git repository
- In Cursor: Ensure you've opened a git repository as your workspace
- Use `fckgit_debug` tool to see what directory was detected

**"Wrong repository detected" or "Operations happen in wrong project"**
- In Cursor: Just switch to the correct project - it auto-detects!
- In Claude Desktop: Check your `cwd` setting in the config
- Use `fckgit_debug` tool to see what workspace was detected

**"GEMINI_API_KEY environment variable not set"**
- Add API key to your MCP config's `env` section
- Get free key: https://makersuite.google.com/app/apikey

**"No module named 'mcp_server'"**
- Run: `pip install -e ".[mcp]"` from the fckgit directory
- This installs fckgit as a package so Python can find mcp_server
- Make sure you're using the same Python that Cursor/Claude Desktop uses

**"mcp not installed"** or **"psutil not installed"**
- Run: `pip install -e ".[mcp]"` to install all MCP dependencies
- Or manually: `pip install mcp psutil`

**"Git command failed" or "Permission denied"**
- Check file permissions on workspace directory
- Verify git is in PATH: `git --version`
- Check logs in stderr for detailed error messages
- Try cleaning up git lock files: use `fckgit_cleanup_lock` tool

**"Slow performance"**
- Check cache hit rate via `fckgit_debug` tool
- Network drives can be slow - consider using local clone
- Very large repositories may need longer timeouts
- Check Windows Defender exclusions for project directory

**Tools not appearing in Cursor/Claude**
- Restart Cursor or Claude Desktop after changing config
- Check the MCP logs for errors (View > Output > MCP in Cursor)
- Verify your config JSON syntax is valid
- Try running test: `python scripts/test_mcp.py`

**"Command injection" or "Security check failed"**
- This is a protection feature - commands are validated
- Don't use shell metacharacters in commit messages
- Contact maintainers if false positive

## Advanced Configuration

### Manual Workspace Override

If you need to force a specific project path (e.g., for testing or unusual setups):

**Using PROJECT_ROOT (recommended):**

```json
{
  "mcpServers": {
    "fckgit": {
      "command": "python",
      "args": ["-m", "mcp_server"],
      "env": {
        "GEMINI_API_KEY": "your_api_key_here",
        "PROJECT_ROOT": "C:\\path\\to\\specific\\project"
      }
    }
  }
}
```

**Using cwd:**

```json
{
  "mcpServers": {
    "fckgit": {
      "command": "python",
      "args": ["-m", "mcp_server"],
      "cwd": "C:\\path\\to\\your\\project",
      "env": {
        "GEMINI_API_KEY": "your_api_key_here"
      }
    }
  }
}
```

Both methods override automatic detection. Restart Cursor after changing these settings.

### Debug Logging

Enable detailed logging for troubleshooting:

```json
{
  "mcpServers": {
    "fckgit": {
      "command": "python",
      "args": ["-m", "mcp_server"],
      "cwd": "C:\\path\\to\\project",
      "env": {
        "GEMINI_API_KEY": "your_key",
        "LOG_LEVEL": "DEBUG"
      }
    }
  }
}
```

Check stderr output for logs.

### Git Worktrees

fckgit automatically detects and handles git worktrees. No special configuration needed.

### Git Submodules

fckgit detects submodules. The server operates on the submodule if started within it, or the parent repository if started in parent.

### Monorepos

For monorepos, set `cwd` to the subdirectory you want to work on. The server will find the git root and operate there.

## Architecture

For technical details about the implementation, see [mcp_server/README.md](mcp_server/README.md).

**Key Features:**

1. **Automatic workspace detection**: Works out of the box in Cursor - just switch projects!
2. **Security first**: Never uses `shell=True`, validates all inputs
3. **Git-native detection**: Uses git commands to handle worktrees, submodules, etc.
4. **Robust error handling**: Clear error messages for easy debugging
5. **Performance**: Thread-safe caching with 60s TTL, <1ms cached lookups
6. **Cross-platform**: Windows, Mac, Linux support with platform-specific optimisations

## Examples

```
You: "Blastoff!"
AI: BLASTOFF! fckgit watch mode started (PID: 12345)
    30 second cooldown between commits

You: "Blastoff with 5 minute cooldown"
AI: BLASTOFF! fckgit watch mode started (PID: 12345)
    300 second cooldown between commits

You: "Blastoff in Silicon Valley mode"
AI: BLASTOFF! fckgit watch mode started (PID: 12345)
    SILICON VALLEY MODE - FAANG-tier professional commits enabled

You: "Commit in Silicon Valley mode"
AI: Committed [abc1234]: refactor: Optimize system architecture
    Enhanced maintainability and scalability...

You: "Stop watching"
AI: Stopped fckgit watch process (PID: 12345)
```

## See Also

- [SILICON_VALLEY.md](SILICON_VALLEY.md) - Full Silicon Valley mode guide
- [README.md](README.md) - Main documentation

---

MIT License. Not responsible for AI commits to main.
