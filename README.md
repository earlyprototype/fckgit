# fckgit

Auto-commit with AI-generated messages using Gemini 2.5 Flash-Lite.

Stop thinking about git commits. Just code, and let AI handle the rest.

## ⚠️ Warning: May Cause Horror in Senior Developers

This tool is only for cool kids:
- ❌ No carefully crafted commit messages
- ❌ No logical commit boundaries  
- ❌ No `git rebase -i` to clean up history
- ❌ Commits literally everything you save
- ✅ Maximum laziness achieved

**"But muh git features!"** - Shut up Nerd. This tool is for:
- solo

If you work on a team, for the love of git, **use `--once` mode** and review before pushing. Or don't. We're not your parents.

## Features

- 🤖 **AI-Powered Commits** - Gemini generates conventional commit messages automatically
- 👀 **Watch Mode** - Auto-commits and pushes on every file save (default)
- ⚡ **Fast & Cheap** - Uses Gemini 2.5 Flash-Lite for speed and low cost
- 🔧 **Smart Error Handling** - Auto-cleanup of git lock files and detailed error messages
- 📝 **Detailed Logging** - Timestamps, commit hashes, and file tracking for easy debugging
- 🌍 **Cross-Platform** - Works on Windows, macOS, and Linux

## Installation

```bash
# Clone the repo
git clone https://github.com/earlyprototype/fckgit.git
cd fckgit

# Install with pip
pip install .
```

## Setup

### 1. Get a Gemini API Key

Get your free API key from [Google AI Studio](https://makersuite.google.com/app/apikey)

### 2. Configure the API Key

**Option A: Using .env file (recommended)**
```bash
# Create a .env file in your project
echo "GEMINI_API_KEY=your_key_here" > .env
```

**Option B: Environment variable**
```bash
# Windows PowerShell
$env:GEMINI_API_KEY="your_key_here"

# macOS/Linux
export GEMINI_API_KEY="your_key_here"
```

## Usage

### Watch Mode (Default - Auto-commit on save)

```bash
# Start watching for file changes:
python -m fckgit
```

What happens:
- 👀 Watches all files in your repository
- 💾 Detects changes when you save files
- 🤖 Generates smart commit messages with AI
- ✅ Stages, commits, and pushes automatically
- ⏱️ 5-second cooldown between commits
- 📊 Shows timestamps, commit hashes, and changed files
- 🛑 Press `Ctrl+C` to stop watching

**Example output:**
```
==================================================
👀 fckgit - Auto-commit watcher started
   Repository: my-project
   Branch: main
   Started: 2026-01-03 14:30:00
   Press Ctrl+C to stop
==================================================

==================================================
🔍 Changes detected at 2026-01-03 14:32:15
   Files: README.md, src/app.py
   Analyzing with AI...
✓ Committed: feat: Add new authentication feature
  [abc1234] at 14:32:17
📤 Pushing to remote... (14:32:17)
✓ Pushed to remote!
==================================================
```

### Single Commit Mode

```bash
# Run once for current changes:
python -m fckgit --once
```

Use this when you want manual control or need to run other git commands between commits.

## How It Works

1. **Detects Changes** - Watches file system events or checks git status
2. **Analyzes Diff** - Reads `git diff` output
3. **Generates Message** - Sends diff to Gemini 2.5 Flash-Lite
4. **Commits** - Stages all changes and commits with AI message
5. **Pushes** - Automatically pushes to remote repository

## Troubleshooting

### Git Lock File Issues

If you see `fatal: Unable to create '.git/index.lock'`:
- **Auto-fixed!** fckgit now automatically removes stale lock files
- Or manually: `rm .git/index.lock` (macOS/Linux) or `del .git\index.lock` (Windows)

### Avoiding Lock Files

- Don't run multiple git commands while fckgit is running
- Use `--once` mode if you need to run other git commands
- Stop fckgit (Ctrl+C) before running `git pull`, `git rebase`, etc.

### API Rate Limits

- Gemini 2.5 Flash-Lite free tier: 15 requests/minute
- The 5-second cooldown prevents hitting limits
- If you hit limits, just wait a minute and continue

## Requirements

- Python 3.8+
- Git
- [Gemini API key](https://makersuite.google.com/app/apikey) (free tier available)

## Dependencies

- `google-generativeai` - Gemini AI SDK
- `python-dotenv` - .env file support
- `watchdog` - File system monitoring

## License

MIT License - See [LICENSE](LICENSE) file for details

## Contributing

Issues and pull requests welcome! Feel free to improve fckgit.
