# fckgit

Auto-commit with AI-generated messages using Gemini 2.5 Flash-Lite.

Stop wasting time on git commits. Code, save, done. AI handles the boring stuff.

## ⚠️ Warning: May Cause Horror in Senior Developers

This tool is only for cool kids:
- ❌ No carefully crafted commit messages
- ❌ No logical commit boundaries  
- ❌ No `git rebase -i` to clean up history
- ❌ Commits literally everything you touch
- ✅ Maximum laziness achieved

**"But muh git features!"** - Shut up Nerd. This tool is for:
- Extreme solo vibe-riders only🏄‍♂️ 

If you work on a team (you don't), for the love of git, **use `--once` mode** and review before pushing. Or don't. We're not your parents.

## Features (Yeah, We Got 'Em)

- 🤖 **AI Does Your Commits** - Gemini write your commit messages so you have more time to focus on your prompt engineering course.
- 👀 **Auto-Everything** - Watches files, commits, pushes. You literally don't know whats going on.
- ⚡ **Fast & Cheap** - Uses the cheapest Gemini model. Free teir maxxing.
- 🔧 **Handles Git's BS** - Cleans up lock files automatically because you don't know how to.
- 📝 **Actually Shows Useful Info** - Timestamps, hashes, files. For when you get an intern.
- 🌍 **Works Everywhere** - Windows, Mac, Linux, cafes, hostels, Wetherspoons - We don't discriminate.

## Installation 

```bash
git clone https://github.com/earlyprototype/fckgit.git
cd fckgit
pip install .
```

That's it. No docker containers, no kubernetes, no build scripts. Intern working on MCP - available soon.

## Setup (Takes 30 Seconds)

**Get API key:** [Google AI Studio](https://makersuite.google.com/app/apikey) (it's free, relax)

**Drop it in a .env file:**
```bash
echo "GEMINI_API_KEY=your_key_here" > .env
```

Or export it if you're fancy:
```bash
export GEMINI_API_KEY="your_key_here"  # Mac/Linux
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
- 30 second cooldown so you can actually code
- `Ctrl+C` when you're done being productive

**What you'll see:**
```
👀 fckgit watching | my-project | main branch

🔍 Changes detected at 14:32:15
   Files: README.md, app.py
✓ Committed: feat: Add new authentication feature
  [abc1234] at 14:32:17
📤 Pushed to remote!
```

Clean. Simple. Gets out of your way.

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
Free tier gives you 15/min. With our 30 second cooldown, you'd need to code pretty hard to hit it.

**Using this on a team repo?**  
Stop. Use `--once` mode or your hackathon teammates will hate you.

## What You Need

- Python 3.8+ (you probably have it)
- Git (obviously)
- [Free Gemini API key](https://makersuite.google.com/app/apikey)

Dependencies install automatically. It just works™.

## License

MIT. Do whatever you want with it. Create something actually useful for once. 

## Contributing

Found a bug? Cool, fix it and send a PR. Or don't. I don't know what they are.
