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

```bash
# Make changes to your files, then:
fckgit
```

The tool will:
1. Detect changes via `git diff`
2. Generate a Conventional Commits message using Gemini
3. Stage and commit all changes

## Requirements

- Python 3.8+
- Git
- Gemini API key
