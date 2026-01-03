# fckgit MCP Server - Complete Summary

Your abomination now has an MCP server. AI assistants can now commit and push your code directly. What could go wrong?

## What Was Created

### Core MCP Server
- **`mcp_server/`** - Complete MCP server package
  - `server.py` - Main MCP server implementation with 6 tools
  - `__init__.py` - Package initialisation
  - `__main__.py` - Module entry point for running as `python -m mcp_server`

### Documentation
- **`MCP_SETUP.md`** - Complete setup guide for Cursor IDE, Claude Desktop, and other MCP clients
- **`CHANGELOG.md`** - Version history and changes
- **`MCP_README.md`** - This file (summary of MCP implementation)

### Configuration Files
- **`mcp_config_example.json`** - Template MCP configuration
- **`.cursorrules`** - Example Cursor IDE configuration
- **`pyproject.toml`** - Updated with MCP dependencies and entry points
- **`setup.py`** - Updated to include mcp_server package
- **`MANIFEST.in`** - Package manifest for distribution

### Installation & Testing
- **`install_mcp.ps1`** - Windows PowerShell installation script
- **`install_mcp.sh`** - iPad/Linux installation script
- **`test_mcp.py`** - Setup verification script

## Available MCP Tools

Your AI assistant can now use these 11 tools:

1. **fckgit_blastoff** - THE NUCLEAR OPTION - Start full automatic watch mode
2. **fckgit_silicon_valley** - SILICON VALLEY MODE - Commit with FAANG-tier professional messages
3. **fckgit_professionalize** - Transform casual messages to enterprise-grade
4. **fckgit_watch_status** - Check if watch mode is running
5. **fckgit_stop_watch** - Stop the watch mode process
6. **fckgit_status** - Get git status and optionally the full diff
7. **fckgit_generate_message** - Generate AI commit messages without committing
8. **fckgit_commit** - Auto-commit with AI-generated message (optional auto-push)
9. **fckgit_commit_with_message** - Commit with a specific message
10. **fckgit_push** - Push to remote with automatic conflict resolution
11. **fckgit_cleanup_lock** - Clean up stale git lock files

## Quick Start

### 1. Install MCP Support

**Windows PowerShell:**
```powershell
.\install_mcp.ps1
```

**Mac/Linux:**
```bash
chmod +x install_mcp.sh
./install_mcp.sh
```

**Or manually:**
```bash
pip install "mcp>=1.0.0"
```

### 2. Configure Your AI Assistant

See `MCP_SETUP.md` for detailed instructions.

**Quick example for Cursor IDE:**

Add to your Cursor MCP settings:
```json
{
  "mcpServers": {
    "fckgit": {
      "command": "python",
      "args": ["-m", "mcp_server"],
      "cwd": "C:\\Users\\Fab2\\Desktop\\AI\\_tools\\_fckgit",
      "env": {
        "GEMINI_API_KEY": "your_api_key_here"
      }
    }
  }
}
```

### 3. Test It

```bash
python test_mcp.py
```

### 4. Restart Your AI Assistant

Restart Cursor/Claude Desktop for the changes to take effect.

### 5. Try It Out

Ask your AI assistant:
- "Blastoff!" (starts automatic watch mode)
- "Commit in Silicon Valley mode" (professional FAANG-tier commit)
- "Professionalize this message: 'fixed stuff'" (transform casual to professional)
- "Is fckgit watching?" (check status)
- "Stop watching" (stops watch mode)
- "What's the git status?"
- "Commit these changes with an AI-generated message"
- "Generate a commit message for my changes"
- "Commit and push everything"

## How It Works

1. **MCP Protocol**: The server communicates with AI assistants using the Model Context Protocol (stdio transport)
2. **Git Operations**: Reuses existing fckgit functionality for all git operations
3. **AI Messages**: Uses Gemini 2.5 Flash-Lite to generate commit messages (same as standalone tool)
4. **Security**: Requires explicit tool calls from the AI - nothing happens automatically

## Architecture

```
Your AI Assistant (Cursor/Claude)
    |
    | MCP Protocol (stdio)
    v
mcp_server/server.py
    |
    | Reuses functions
    v
fckgit.py (git operations + Gemini AI)
    |
    v
Git Repository
```

## Features

- All git operations from the original fckgit tool
- AI-generated commit messages using Gemini
- Automatic push with conflict resolution (rebase)
- Stale lock file cleanup
- Working in any git repository
- No watch mode (tools are called on demand by AI)

## Security Considerations

The MCP server gives your AI assistant the ability to:
- Read repository status and diffs
- Commit changes
- Push to remote repositories
- Clean up lock files

**Use responsibly:**
- Only use in repositories you own
- Review what the AI is doing
- Don't use on production repositories
- The AI can't force push or delete branches (yet)

## Differences from Standalone fckgit

| Feature | Standalone fckgit | MCP Server |
|---------|------------------|------------|
| Watch mode | Yes (default) | No (on-demand) |
| Auto-commit | Yes | Only when AI calls tool |
| Auto-push | Yes | Optional parameter |
| AI messages | Always | Optional (can provide custom) |
| File watching | Yes | No |
| IDE integration | No | Yes (via MCP) |

## Troubleshooting

**"GEMINI_API_KEY not set"**
- Add it to your MCP config or set as environment variable

**"Not a git repository"**
- Navigate to a git repository first

**"mcp not installed"**
- Run: `pip install mcp`

**Tools not appearing in AI assistant**
- Check MCP config path is correct
- Restart your AI assistant
- Check the AI assistant's MCP logs

## Distribution

If you want to publish this:

1. Update version in `setup.py` and `pyproject.toml`
2. Build: `python -m build`
3. Publish: `twine upload dist/*`

Or just keep it local and have your AI commit directly to main like a true vibe warrior.

## Credits

MCP implementation by Claude Sonnet 4.5, under supervision of the fckgit author (who apparently wanted this abomination to have even more capabilities).

## License

MIT. Same as the main tool. Do whatever you want. Not responsible for any AI-generated commit messages that get you fired.
