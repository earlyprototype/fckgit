# fckgit Quick Start

Zero fucks. Maximum automation.

## Install

```bash
# Windows
.\scripts\install.ps1

# Mac/Linux/iPad
chmod +x scripts/install.sh && ./scripts/install.sh
```

## Setup API Key

Get free key: https://makersuite.google.com/app/apikey

```bash
echo "GEMINI_API_KEY=your_key_here" > .env
```

## Use

```bash
# Watch mode (auto-commit everything)
python -m fckgit

# Silicon Valley mode (sound professional)
python -m fckgit --faang

# Single commit
python -m fckgit --once

# Single professional commit
python -m fckgit --once --faang
```

## MCP Server (AI Assistants)

```bash
# Install MCP
.\scripts\install_mcp.ps1    # Windows
./scripts/install_mcp.sh     # Mac/Linux

# Configure
See: docs/mcp/MCP_SETUP.md
```

Tell your AI:
- "Blastoff!" - Start auto mode
- "Commit in Silicon Valley mode" - Professional commits
- "Stop watching" - Stop auto mode

## Docs

- **Full README**: [README.md](README.md)
- **All Docs**: [docs/](docs/)
- **MCP Setup**: [docs/mcp/MCP_SETUP.md](docs/mcp/MCP_SETUP.md)
- **Silicon Valley**: [docs/guides/SILICON_VALLEY.md](docs/guides/SILICON_VALLEY.md)

## Structure

```
fckgit/
├── README.md               - Full documentation
├── QUICK_START.md         - This file
├── CHANGELOG.md           - Version history
├── fckgit.py              - Main tool
├── mcp_server/            - MCP server
├── docs/                  - All documentation
│   ├── mcp/              - MCP guides
│   └── guides/           - Feature guides
├── scripts/               - Installation scripts
└── examples/              - Configuration examples
```

That's it. Stop thinking. Start shipping to main.
