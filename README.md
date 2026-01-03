# fckgit

<p align="center">
  <img src="assets/banner.jpg" alt="fckgit - ZERO COMMITS GIVEN" width="100%"/>
</p>

Auto-commit with AI-generated messages using Gemini 2.5 Flash-Lite.

Stop wasting time on git commits. Prompt - Accept - Publish. AI to the core, with almost zero visibility

## ⚠️ Warning

This tool is for cool kids only:
- ❌ No carefully crafted commit messages
- ❌ No logical commit boundaries  
- ❌ No `git rebase -i` to clean up history
- ❌ Commits literally everything you touch
- ✅ Maximum speed 

**"But muh git features!"** - Nerd. 

fckgit unlocks:
- 2x vibes 🏄‍♂️ 
- Increased token spend
- Unlimited IP
- Founder mode


## Features 

- 🤖 **AI Does Your Commits** - Gemini writes your commit messages so you have more time to focus on your Newsletter.
- 👀 **Auto-Everything** - Watches files, commits, pushes. You literally don't know whats going on.
- ⚡ **Fast & Cheap** - Uses the cheapest Gemini model. Free teir maxxing.
- 🔧 **Handles Git's BS** - Cleans up lock files automatically because you don't know how to.
- 📝 **Actually Shows Useful Info** - Timestamps, hashes, files. For when you get an intern.
- 🌍 **Works Everywhere** - Windows, iPad, Linux

## Installation (One Click - It's Safe!)

**Option 1: Automated Install (Recommended)**

```bash
# Mac/Linux
git clone https://github.com/earlyprototype/fckgit.git
cd fckgit
chmod +x install.sh
./install.sh

# Windows PowerShell
git clone https://github.com/earlyprototype/fckgit.git
cd fckgit
.\install.ps1
```

**Option 2: Slow and Boring Manual Install**

```bash
git clone https://github.com/earlyprototype/fckgit.git
cd fckgit
pip install .
```

That's it. No docker containers, no kubernetes, no build scripts. Intern working on MCP (available soon).

## Setup (Takes 30 Seconds)

**Get your free API key:** [Google AI Studio](https://makersuite.google.com/app/apikey) (or pick from one of your 5 existing accounts)

**Drop it in a .env file:**
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
```

It literally just works:
- Watches everything
- You code, it commits
- AI writes the message
- Auto-pushes to GitHub
- 30 second cooldown
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

### Single Commit Mode 

```bash
python -m fckgit --once
```

Use this when you graduate university.

## How It Works (If You Care)

File changes → AI reads diff → Generates message → Commits → Pushes. 


## When Stuff Breaks

**Git lock file errors?**  
We auto-delete them. You're welcome.

**Multiple fckgit instances running?**  
Don't do that or ask your AI to kill the extras with Task Manager.

**Hit API rate limits?**  
Free tier gives you 15/min. With a 30 second cooldown, you should still be tripping that 4/5 times a session.

**Using this on a team repo?**  
Stop that immediately. Use `--once` mode or your hackathon teammates will hate you.

## What You Need

- Python 3.8+ (you probably have it)
- Git (don't ask)
- [Free Gemini API key](https://makersuite.google.com/app/apikey)

Dependencies install automatically. It just works™ (unlike you).

## License

MIT. Do whatever you want with it. Create something actually useful even. 

## Contributing

Found a bug? Cool, fix it and send a PR. Or don't. I don't know what they are.
