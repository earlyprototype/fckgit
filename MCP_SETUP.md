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

### Cursor IDE

Add to your Cursor MCP settings:

```json
{
  "mcpServers": {
    "fckgit": {
      "command": "python",
      "args": ["-m", "mcp_server"],
      "cwd": "C:\\path\\to\\fckgit",
      "env": {
        "GEMINI_API_KEY": "your_gemini_api_key_here"
      }
    }
  }
}
```

### Claude Desktop

**Mac:** `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "fckgit": {
      "command": "python",
      "args": ["-m", "mcp_server"],
      "cwd": "/path/to/fckgit",
      "env": {
        "GEMINI_API_KEY": "your_api_key_here"
      }
    }
  }
}
```

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

**"GEMINI_API_KEY environment variable not set"**
- Add API key to your MCP config
- Get free key: https://makersuite.google.com/app/apikey

**"Not a git repository"**
- MCP server only works in git repositories
- Navigate to a git repo first

**"No module named 'mcp_server'"**
- Run: `pip install -e ".[mcp]"` from the fckgit directory
- This installs fckgit as a package so Python can find mcp_server

**"mcp not installed"**
- Run: `pip install mcp psutil`

**Tools not appearing**
- Check config path is correct (use absolute paths)
- Restart AI assistant
- Check AI assistant's MCP logs

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
