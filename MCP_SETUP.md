# fckgit MCP Server Setup Guide

The fckgit MCP server lets AI assistants directly commit and push your code. Maximum automation, minimum accountability.

## Prerequisites

- Python 3.8+
- fckgit installed (`pip install .` from the fckgit directory)
- MCP Python SDK: `pip install mcp`
- Gemini API key (get one from [Google AI Studio](https://makersuite.google.com/app/apikey))

## Quick Install

```bash
# From the fckgit directory
pip install "mcp>=1.0.0"
```

## Configuration

### Option 1: Cursor IDE (Recommended)

Add this to your Cursor MCP settings file (usually at `~/.cursor/config.json` or similar):

```json
{
  "mcpServers": {
    "fckgit": {
      "command": "python",
      "args": ["-m", "mcp_server"],
      "cwd": "C:\\Users\\YourUser\\path\\to\\fckgit",
      "env": {
        "GEMINI_API_KEY": "your_gemini_api_key_here"
      }
    }
  }
}
```

**Windows PowerShell path example:**
```json
"cwd": "C:\\Users\\Fab2\\Desktop\\AI\\_tools\\_fckgit"
```

**Mac/Linux path example:**
```json
"cwd": "/home/user/projects/fckgit"
```

### Option 2: Claude Desktop

Edit your Claude Desktop config file:

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

### Option 3: Environment Variable

Instead of putting the API key in the config, you can set it as an environment variable:

**Windows PowerShell:**
```powershell
$env:GEMINI_API_KEY="your_api_key_here"
```

**Mac/Linux:**
```bash
export GEMINI_API_KEY="your_api_key_here"
```

Then your config becomes:
```json
{
  "mcpServers": {
    "fckgit": {
      "command": "python",
      "args": ["-m", "mcp_server"],
      "cwd": "/path/to/fckgit"
    }
  }
}
```

## Available Tools

Once configured, your AI assistant can use these tools:

### `fckgit_status`
Get current git status and optionally the full diff.

**Parameters:**
- `include_diff` (boolean, optional): Include the full diff output (default: false)

**Example usage:**
> "Check the git status of this repo"

### `fckgit_generate_message`
Generate an AI commit message without actually committing.

**Parameters:**
- `use_staged` (boolean, optional): Use only staged changes (default: false, uses all changes)

**Example usage:**
> "What commit message would you suggest for these changes?"

### `fckgit_commit`
Auto-commit with an AI-generated message.

**Parameters:**
- `push` (boolean, optional): Auto-push after committing (default: false)
- `stage_all` (boolean, optional): Stage all changes first (default: true)

**Example usage:**
> "Commit these changes with an AI-generated message"
> "Commit and push everything"

### `fckgit_commit_with_message`
Commit with a specific message (no AI generation).

**Parameters:**
- `message` (string, required): The commit message
- `push` (boolean, optional): Auto-push after committing (default: false)
- `stage_all` (boolean, optional): Stage all changes first (default: true)

**Example usage:**
> "Commit with message 'fix: resolve merge conflicts'"

### `fckgit_push`
Push commits to remote (handles conflicts with auto-rebase).

**Example usage:**
> "Push my commits"

### `fckgit_cleanup_lock`
Clean up stale git lock files.

**Example usage:**
> "Clean up git lock files"

## Testing the Setup

1. Restart your AI assistant (Cursor/Claude Desktop)
2. In a git repository, ask: "What's the git status?"
3. If it works, the AI will use the fckgit_status tool

## Troubleshooting

### "GEMINI_API_KEY environment variable not set"
- Make sure your API key is in the config or set as an environment variable
- Restart your AI assistant after updating the config

### "Not a git repository"
- The MCP server only works when you're in a git repository
- Navigate to a git repo and try again

### "mcp not found"
- Install the MCP SDK: `pip install mcp`

### "google-genai not installed"
- Install it: `pip install google-genai`

### Path issues on Windows
- Use double backslashes in JSON: `"C:\\Users\\..."`
- Or use forward slashes: `"C:/Users/..."`

## Security Warning

This gives your AI assistant the ability to:
- Commit code
- Push to remote repositories
- Delete stale lock files

Use with caution. Don't use this on production repositories unless you're absolutely certain of what you're doing (you're not).

## License

MIT. Do whatever you want. I'm not responsible for any force pushes to main.
