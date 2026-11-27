# fckgit MCP Server Setup

Let AI assistants auto-commit your code.

## Quick Start: 3 Steps

### 1. Install

```bash
pip install -e ".[mcp]"
```

### 2. Get Your API Key

Get a free Gemini API key: https://makersuite.google.com/app/apikey

### 3. Configure (Choose Your IDE)

**Using Cursor or VSCode?** → Skip to [Cursor/VSCode Setup](#cursor-ide)
**Using Claude Desktop?** → Skip to [Claude Desktop Setup](#claude-desktop)  
**Using something else?** → Skip to [Other IDEs Setup](#other-ides--mcp-clients)

---

## Configuration by IDE

### Cursor IDE

1. Open Cursor Settings: `File > Preferences > Cursor Settings > MCP`
2. Add this config:

```json
{
  "mcpServers": {
    "fckgit": {
      "command": "python",
      "args": ["-m", "mcp_server"],
      "env": {
        "GEMINI_API_KEY": "paste_your_api_key_here"
      }
    }
  }
}
```

3. Reload Cursor: `Ctrl+Shift+P` → "Developer: Reload Window"

When Cursor keeps the same MCP server after a project switch, pass the new
project's absolute path as `repo_path` on each tool call. The server uses
its own environment and working directory when you omit the argument.
Before committing, call `fckgit_debug` with `{"repo_path": "/projects/my-app"}`
and check that `git_root` matches your intended worktree. Pass that same
`repo_path` to the commit tool.

### VSCode (with MCP Extension)

1. Install an MCP extension for VSCode (if available)
2. Add this to your MCP config:

```json
{
  "mcpServers": {
    "fckgit": {
      "command": "python",
      "args": ["-m", "mcp_server"],
      "env": {
        "GEMINI_API_KEY": "paste_your_api_key_here"
      }
    }
  }
}
```

3. Reload VSCode

After switching projects, use the same `repo_path` and `git_root` check as in Cursor.

### Claude Desktop

**You need to set your project path manually.**

1. Find your Claude config file:
   - **Mac:** `~/Library/Application Support/Claude/claude_desktop_config.json`
   - **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

2. Add this config (replace `/path/to/your/project` with your actual project path):

```json
{
  "mcpServers": {
    "fckgit": {
      "command": "python",
      "args": ["-m", "mcp_server"],
      "cwd": "/path/to/your/project",
      "env": {
        "GEMINI_API_KEY": "paste_your_api_key_here"
      }
    }
  }
}
```

3. Restart Claude Desktop

**Important:** Change the `cwd` path to your actual git repository path. Example:
- Windows: `"cwd": "C:\\Users\\YourName\\Projects\\my-app"`
- Mac/Linux: `"cwd": "/Users/yourname/projects/my-app"`

### Other IDEs / MCP Clients

**For JetBrains (IntelliJ, PyCharm, WebStorm), Neovim, Zed, Emacs, etc.**

Same as Claude Desktop - set your project path manually:

```json
{
  "mcpServers": {
    "fckgit": {
      "command": "python",
      "args": ["-m", "mcp_server"],
      "cwd": "/path/to/your/project",
      "env": {
        "GEMINI_API_KEY": "paste_your_api_key_here"
      }
    }
  }
}
```

**Replace `/path/to/your/project` with your actual project path.**

The server finds your git root automatically from that path, so it works in monorepos and subdirectories.

---

## How to Use fckgit

After setup, tell your AI assistant these commands:

### Basic Commands

| What You Say | What Happens |
|--------------|-------------|
| **"blastoff"** | Starts auto-commit mode. Commits everything forever. |
| **"stop watching"** | Stops auto-commit mode. |
| **"commit these changes"** | One AI commit right now. |
| **"silicon valley mode"** | One FAANG-tier professional commit. |
| **"what's the git status?"** | Shows changed files. |
| **"push to remote"** | Pushes commits to GitHub/GitLab. |

### Advanced Commands

| What You Say | What Happens |
|--------------|-------------|
| **"blastoff with 5 minute cooldown"** | Auto-commits every 5 minutes instead of 30 seconds. |
| **"blastoff in silicon valley mode"** | Auto-commits with FAANG-tier professional messages. |
| **"is fckgit running?"** | Checks if watch mode is active. |

**That's it.** Your AI handles git for you now.

---

## Available Tools

Tell your AI assistant:

**"Blastoff!"** - Start automatic watch mode (auto-commits everything)
- `fckgit_blastoff` - Launch watch mode
  - `cooldown` takes a whole number of seconds between commits and defaults to 30.
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
2. Call `fckgit_debug` with the intended repository's absolute `repo_path`.
3. Check `git_root`, then call `fckgit_status` with the same path to see the changed files.

## Troubleshooting

### Problem: "Not a git repository"

**Solution:**
1. Make sure you're in a git repository
2. Run `git init` if you haven't initialised git yet
3. In Cursor: Open the actual git repository folder, not a parent folder

### Problem: "Wrong repository detected"

Call `fckgit_debug` with the arguments you plan to use for the commit.
Inspect `git_root` and `detection_method`. If the root is wrong or missing,
pass the intended repository's absolute `repo_path` to both the debug call
and the commit. An explicit path applies only to that call.

For calls without `repo_path`, the first folder in `WORKSPACE_FOLDER_PATHS`
takes precedence over `PROJECT_ROOT`. An inaccessible configured folder
produces a tool error. Correct the setting and restart the server to load
it. With both settings absent, the server discovers Git from its working
directory. Git respects discovery limits such as `GIT_CEILING_DIRECTORIES`.
Each call uses the selected Git directory and worktree for every command and
retry. If a project moves during a call, pass its new path on the next call.

### Problem: "GEMINI_API_KEY not set"

**Solution:**
1. Get free API key: https://makersuite.google.com/app/apikey
2. Add it to your MCP config under `env` → `GEMINI_API_KEY`
3. Restart your IDE

### Problem: "No module named 'mcp_server'"

**Solution:**
```bash
cd /path/to/fckgit
pip install -e ".[mcp]"
```

Then restart your IDE.

### Problem: "Tools not showing up"

**Solution:**
1. Restart your IDE completely (not just reload)
2. Check your config JSON is valid (no syntax errors)
3. In Cursor: Check `View > Output > MCP` for errors

### Problem: "fckgit_watch_status not detecting running process"

**Solution:**
This was a bug, fixed in v0.2.2. Update fckgit:
```bash
cd /path/to/fckgit
pip install -e ".[mcp]"
```

Restart your IDE after updating.

## Advanced Configuration

### Manual Workspace Override

To target one call, pass a directory in the repository. For example, call
`fckgit_status` with `{"repo_path": "/projects/my-app", "include_diff": true}`.
Use an absolute path when the editor and server have different working
directories. The next call can select a different repository.

**Using PROJECT_ROOT as a default**

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

Without `repo_path`, the server checks `WORKSPACE_FOLDER_PATHS`, then
`PROJECT_ROOT`, then its working directory. Restart Cursor to load changes
to the server configuration.

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

1. **Workspace selection**: Each call can specify a repository or use workspace detection.
2. **Security first**: Never uses `shell=True`, validates all inputs
3. **Git-native detection**: Uses git commands to handle worktrees, submodules, etc.
4. **Robust error handling**: Clear error messages for easy debugging
5. **Consistent targeting**: A multi-step operation uses one repository from start to finish.
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
