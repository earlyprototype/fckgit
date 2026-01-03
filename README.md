# fckgit

Because sometimes you just want to commit without thinking about it.

## What is this?

`fckgit` is a lightweight Python CLI tool that streamlines your git workflow by automating commit message generation and pushing changes to your repository. It's designed for developers who want to focus on coding rather than crafting the perfect commit message.

Whether you're prototyping, iterating rapidly, or just tired of writing descriptive commits, `fckgit` has your back. It generates contextually relevant, often sarcastic commit messages using AI, eliminating the friction between "I made changes" and "my changes are pushed."

## Key Features

- **Instant Commits**: Generate commit messages in seconds, not hours of overthinking
- **AI-Powered Messages**: Uses Gemini 2.5 Flash-Lite to craft creative, contextually aware commit messages
- **One-Command Workflow**: Streamline your git process with a single prompt
- **Sardonic Tone**: Because regular commit messages are boring
- **Zero Configuration**: Works out of the box with minimal setup

Auto-commit with AI-generated messages using Gemini 2.5 Flash-Lite. Now with MCP integration so your AI assistant can betray you too.

Stop wasting time on git commits. **Prompt - Accept - Publish to Main.** Even your AI can do it now.

## Getting Started

### Installation

```bash
pip install fckgit
```

### Quick Start

```bash
fckgit
```

That's it. Your changes are now committed and pushed. You're welcome.

## How It Works

1. **Prompt**: Describe what you changed (or let it figure it out)
2. **Accept**: Review the AI-generated commit message
3. **Publish**: Push to your repository with one confirmation

It's like having a developer who actually enjoys writing commit messages.

## Features

- 🚀 **Lightning Fast** - Commits faster than you can say "git push origin main"
- 🧠 **AI-Driven** - Powered by Gemini 2.5 Flash-Lite for witty, accurate messages
- 📝 **Context Aware** - Analyzes your changes to generate relevant commit messages
- 🎯 **Selective Commits** - Choose which files to include in your commit
- 🔄 **Batch Operations** - Commit multiple changes in one go
- 🤖 **MCP Server** - Let AI assistants auto-commit your code. What could go wrong?

## Configuration

Create a `.fckgit.config.json` file in your project root:

```json
{
  "ai_provider": "gemini",
  "model": "gemini-2.5-flash-lite",
  "branch_strategy": "current",
  "auto_push": true,
  "tone": "sardonic"
}
```

## Requirements

- Python 3.8+
- Git 2.0+
- Gemini API key (get one [here](https://aistudio.google.com/))

## License

MIT License - Use at your own risk. Seriously, we're not responsible for your commit messages.

## Contributing

Found a bug? Have a feature request? Feel free to open an issue or submit a pull request. We appreciate contributions almost as much as we appreciate good commit messages (which is to say, not very much).

---

**Disclaimer**: This tool is designed for fun and efficiency. Use responsibly, and maybe actually review your commits before pushing to production. Probably a good idea, honestly.
