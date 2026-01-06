# fckgit

<p align="center">
  <img src="assets/banner.gif" alt="fckgit - ZERO COMMITS GIVEN" width="100%"/>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/commits-automatic-ff69b4?style=for-the-badge" alt="Automatic Commits"/>
  <img src="https://img.shields.io/badge/AI-powered-00d4ff?style=for-the-badge" alt="AI Powered"/>
  <img src="https://img.shields.io/badge/vibes-extreme-00ff00?style=for-the-badge" alt="Extreme Vibes"/>
  <img src="https://img.shields.io/badge/accountability-zero-red?style=for-the-badge" alt="Zero Accountability"/>
</p>

Rapid-fire auto-commit with AI-generated messages using Gemini 2.5 Flash-Lite.

Stop wasting time on git commits. **Prompt - Accept - Publish to Main.** 

---
### 2026 Update: MCP server drop!
fckgit now includes an MCP (Model Context Protocol) server so AI assistants can auto-commit your code directly.

**New MCP-only Exclusive Tools**
- **SILICON VALLEY** - Make commits sound FAANG professional (`fckgit_silicon_valley`)
- **PROFESSIONALIZE** - Transform casual messages to enterprise-grade (`fckgit_professionalize`)

---
_AI to the core, with almost zero visibility._
---

## Features 

- 🤖 **AI Does Your Commits** - Gemini writes your commit messages so you have more time to focus on your Newsletter.
- 👀 **Auto-Everything** - Watches files, commits, pushes. You literally don't know whats going on.
- ⚡ **Fast & Cheap** - Uses the cheapest Gemini model. Free teir maxxing.
- 🔧 **Handles Git's BS** - Mercifully cleans up lock files automatically.
- 📝 **Actually Shows Useful Info** - Timestamps, hashes, files for Product Managers.
- 🌍 **Works Everywhere** - Windows, iPad, Linux

## fckgit unlocks:
- Up to 3x vibes 🏄‍♂️ 
- Increased token spend at zero cost to you
- FAANG adjaceny
- Founder mode
- Growth Mindset
  
## ⚠️ Warning 

- ❌ No carefully crafted commit messages
- ❌ No logical commit boundaries  
- ❌ No `git rebase -i` to clean up history
- ❌ Commits literally everything you touch
- ✅ Needlessly bloated MCP server
- ✅ Maximum speed 



## Installation 

**Option 1: Automated Install (Click and Collect - Recommended)**

```bash
# iPad/Linux
git clone https://github.com/earlyprototype/fckgit.git
cd fckgit
chmod +x scripts/install.sh
./scripts/install.sh

# Windows PowerShell
git clone https://github.com/earlyprototype/fckgit.git
cd fckgit
.\scripts\install.ps1
```

**Option 2: Difficult and Boring Manual Install**

```bash
git clone https://github.com/earlyprototype/fckgit.git
cd fckgit
pip install .
```

That's it. No docker containers, no kubernetes, no viruses. 

## MCP Server

fckgit now includes an MCP (Model Context Protocol) server so AI assistants can auto-commit your code directly.

**Quick Setup:**

```bash
# Install fckgit with MCP support
pip install -e ".[mcp]"

# Or use the install script
.\scripts\install_mcp.ps1    # Windows
./scripts/install_mcp.sh     # Mac/Linux/iPad
```

**Configuration:**

See [MCP_SETUP.md](MCP_SETUP.md) for complete setup instructions for:
- Cursor IDE
- Claude Desktop
- Other MCP clients

**Available Tools:**

Your AI assistant can now:
- **BLASTOFF** - Launch full auto mode with custom cooldown and optional FAANG mode (`fckgit_blastoff`)
- **SILICON VALLEY** - Make commits sound FAANG professional (`fckgit_silicon_valley`)
- **PROFESSIONALIZE** - Transform casual messages to enterprise-grade (`fckgit_professionalize`)
- Check watch status (`fckgit_watch_status`)
- Stop watch mode (`fckgit_stop_watch`)
- Check git status (`fckgit_status`)
- Generate commit messages (`fckgit_generate_message`)
- Auto-commit with AI messages (`fckgit_commit`)
- Commit with custom messages (`fckgit_commit_with_message`)
- Push to remote (`fckgit_push`)
- Clean up lock files (`fckgit_cleanup_lock`)

Tell your AI "blastoff" for auto mode, "blastoff in Silicon Valley mode" for professional commits, or just "Silicon Valley mode" for a single FAANG-tier commit. What could possibly go wrong?

## Setup (Takes 30 Seconds)

**Get your free API key:** [Google AI Studio](https://makersuite.google.com/app/apikey) (or pick from one of your 5 existing accounts)

**Drop it in a .env file:**
```bash
cp .env.example .env
# Edit .env and add your actual API key
```

Or just:
```bash
echo "GEMINI_API_KEY=your_key_here" > .env
```

Or export it if you're fancy:
```bash
export GEMINI_API_KEY="your_key_here"  # iPad/Linux
$env:GEMINI_API_KEY="your_key_here"    # Windows
```

## Usage

### Watch Mode (Default - Auto-commit on save)

```bash
# Start watching for file changes:
python -m fckgit

# Silicon Valley mode (FAANG-tier professional commits):
python -m fckgit --faang

# Custom cooldown (default is 30 seconds):
python -m fckgit --cooldown 60

# Combine options:
python -m fckgit --faang --cooldown 120
```

It literally just works:
- Watches everything
- You code, it commits
- AI writes the message
- Auto-pushes to GitHub
- Configurable cooldown (default: 30s)
- `Ctrl+C` when you're done being productive

**What you'll see:**
```
👀 fckgit watching | my-project | main branch

🔍 Changes detected at 14:32:15
   Files: README.md, app.py
✓ Committed: feat: Add Revolutionary RAG Pipeline
  [abc1234] at 14:32:17
📤 Pushed to remote!
```

Clean. Simple. Gets out of your prompts' way.

### Silicon Valley Mode (FAANG Professional)

```bash
# Watch mode with professional commits:
python -m fckgit --faang

# Single commit with professional message:
python -m fckgit --once --faang
```

Makes every commit sound like it came from a Staff Engineer at Google.

### Single Commit Mode 

```bash
python -m fckgit --once
```

Use this when you graduate university.

## How It Works 

File changes → AI reads diff → Main

## When Stuff Breaks

**Git lock file errors during clone/install?**  
Windows moment. Just hit 'y' for victory.

**Git lock file errors during commits?**  
We auto-delete them. You're welcome.

**Multiple fckgit instances running?**  
Don't do that/ask your AI to kill the extra processes with Task Manager.

**Hit API rate limits?**  
Free tier gives you 15/min. With a 30 second cooldown, you should still be tripping that 4/5 times a session. Switch acccount and grab new API key.

**Using this on a team repo?**  
Stop that immediately. `--once` mode only permitted during hackathons.

## What You Need

- Python 3.8+ (you probably have it)
- Git (don't ask)
- [Free Gemini API key](https://makersuite.google.com/app/apikey)

Dependencies install automatically. It just works™.

## License

MIT. Do whatever you want with it. Create something actually useful even. 

## Contributing

Found a bug? Cool, fix it and send a PR. Or don't. I don't know what they are.

---

## Star History

<p align="center">
  <a href="https://star-history.com/#earlyprototype/fckgit&Date">
    <picture>
      <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=earlyprototype/fckgit&type=Date&theme=dark" />
      <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=earlyprototype/fckgit&type=Date" />
      <img alt="Star History Chart" src="https://api.star-history.com/svg?repos=earlyprototype/fckgit&type=Date" />
    </picture>
  </a>
</p>

<p align="center">
  <a href="https://github.com/earlyprototype/fckgit/stargazers">
    <img src="https://img.shields.io/github/stars/earlyprototype/fckgit?style=social" alt="GitHub stars"/>
  </a>
  <a href="https://github.com/earlyprototype/fckgit/network/members">
    <img src="https://img.shields.io/github/forks/earlyprototype/fckgit?style=social" alt="GitHub forks"/>
  </a>
  <a href="https://github.com/earlyprototype/fckgit/issues">
    <img src="https://img.shields.io/github/issues/earlyprototype/fckgit" alt="GitHub issues"/>
  </a>
</p>

<p align="center">
  <strong>Be a vibe warrior and smash that star button ⭐</strong>
</p>
