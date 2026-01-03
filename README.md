# fckgit

Auto-commit with AI-generated messages using Gemini 2.5 Flash-Lite.



## Installation

```bash
pip install .
```

## Setup

Set your Gemini API key:
```bash
export GEMINI_API_KEY="your_key_here"
```

## Usage

### Watch Mode (Default - Auto-commit on save)

```bash
# Start watching for file changes:
fckgit
```

The tool will:
- Monitor all files in your repository
- Automatically detect changes when you save files
- Generate a Conventional Commits message using Gemini
- Stage, commit, and push to remote repository
- 5-second cooldown between commits
- Press `Ctrl+C` to stop watching

### Single Commit Mode

```bash
# Run once for current changes:
fckgit --once
```

This will commit and push current changes once, then exit.

## Requirements

- Python 3.8+
- Git
- Gemini API key
