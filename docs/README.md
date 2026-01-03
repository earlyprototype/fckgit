# fckgit Documentation

Complete documentation for fckgit - the auto-commit tool that gives zero fucks.

## Quick Start

- **[Main README](../README.md)** - Installation and basic usage
- **[CHANGELOG](../CHANGELOG.md)** - Version history and changes

## MCP Server Documentation

Everything about the Model Context Protocol server:

- **[MCP Setup Guide](mcp/MCP_SETUP.md)** - Complete setup instructions for Cursor/Claude Desktop
- **[MCP Technical Overview](mcp/MCP_README.md)** - Architecture and tool reference
- **[Installation Complete](mcp/MCP_INSTALLATION_COMPLETE.txt)** - Quick reference after install

## Usage Guides

Detailed guides for specific features:

- **[Silicon Valley Mode](guides/SILICON_VALLEY.md)** - Make commits sound FAANG professional
- **[FAANG Flag Usage](guides/FAANG_FLAG_USAGE.md)** - Using --faang in standalone tool
- **[Blastoff Mode](guides/BLASTOFF.md)** - Full automatic watch mode via MCP
- **[Silicon Valley Summary](guides/SILICON_VALLEY_SUMMARY.txt)** - Quick reference
- **[FAANG Flag Complete](guides/FAANG_FLAG_COMPLETE.txt)** - Technical details

## Installation Scripts

Located in `../scripts/`:

- `install.ps1` / `install.sh` - Main installation scripts
- `install_mcp.ps1` / `install_mcp.sh` - MCP server installation
- `test_mcp.py` - Test MCP setup

## Configuration Examples

Located in `../examples/`:

- `mcp_config_example.json` - MCP server configuration template
- `cursor_config_example.mdc` - Cursor IDE configuration example

## Structure

```
docs/
├── README.md (this file)
├── mcp/
│   ├── MCP_SETUP.md
│   ├── MCP_README.md
│   └── MCP_INSTALLATION_COMPLETE.txt
└── guides/
    ├── SILICON_VALLEY.md
    ├── FAANG_FLAG_USAGE.md
    ├── BLASTOFF.md
    ├── SILICON_VALLEY_SUMMARY.txt
    └── FAANG_FLAG_COMPLETE.txt
```

## Quick Links

### For Users
- [Basic Usage](../README.md#usage)
- [Setup API Key](../README.md#setup-takes-30-seconds)
- [Watch Mode](../README.md#watch-mode-default---auto-commit-on-save)
- [Silicon Valley Mode](guides/SILICON_VALLEY.md)

### For Developers
- [MCP Architecture](mcp/MCP_README.md)
- [Available Tools](mcp/MCP_SETUP.md#available-tools)

### Troubleshooting
- [When Stuff Breaks](../README.md#when-stuff-breaks)
- [MCP Troubleshooting](mcp/MCP_SETUP.md#troubleshooting)

---

MIT License. Do whatever you want. Not responsible for your bad life decisions.
