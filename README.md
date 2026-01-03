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
- Extreme solo vibe-riders 🏄‍♂️ 

If you work on a team, for the love of git, **use `--once` mode** and review before pushing. Or don't. We're not your parents.

## Features (Yeah, We Got 'Em)

- 🤖 **AI Does Your Commits** - Gemini actually writes good messages. Better than your "fix stuff" commits.
- 👀 **Auto-Everything** - Watches files, commits, pushes. You literally just save and it's done.
- ⚡ **Fast & Cheap** - Uses the cheapest Gemini model. Your free tier goes far.
- 🔧 **Handles Git's BS** - Cleans up lock files automatically because git is moody.
- 📝 **Actually Shows Useful Info** - Timestamps, hashes, files. For when you inevitably need to debug.
- 🌍 **Works Everywhere** - Windows, Mac, Linux. We don't discriminate.

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

It literally just works:
- Watches everything
- You save, it commits
- AI writes the message
- Auto-pushes to GitHub
- 5 second cooldown so you don't spam
- `Ctrl+C` when you're done being productive

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

### Single Commit Mode (For Control Freaks)

```bash
python -m fckgit --once
```

One commit, then it gets out of your way. Use this when you actually want to use git commands yourself.

## How It Works (If You Care)

File changes → AI reads diff → Generates message → Commits → Pushes. 

That's it. It's not rocket science.

## When Stuff Breaks

**Git lock file errors?**  
We auto-delete them. You're welcome.

**Multiple fckgit instances running?**  
Yeah, don't do that. Kill the extras with Task Manager.

**Hit API rate limits?**  
Free tier gives you 15/min. Take a break, touch grass, come back in 60 seconds.

**Using this on a team repo?**  
Stop. Use `--once` mode or your coworkers will hate you.

## What You Need

- Python 3.8+ (you probably have it)
- Git (obviously)
- [Free Gemini API key](https://makersuite.google.com/app/apikey)

Dependencies install automatically. It just works™.

## License

MIT. Do whatever you want with it.

## Contributing

Found a bug? Cool, fix it and send a PR. Or don't. We're all adults here.
