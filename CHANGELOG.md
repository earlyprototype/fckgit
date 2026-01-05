# Changelog

## [0.2.1] - 2026-01-03

### Added
- **`--cooldown` flag** - Configurable cooldown parameter for watch mode (default: 30 seconds)
- `cooldown` parameter for `fckgit_blastoff` MCP tool
- Cooldown time display in watch mode startup banner

### Changed
- `watch_mode()` now accepts `cooldown` parameter
- `GitChangeHandler` now accepts `cooldown` in constructor
- `start_watch_mode()` in MCP server now accepts and passes cooldown to fckgit process
- MCP blastoff tool now shows actual cooldown value in response message

### Features
- Users can customize auto-commit frequency via `--cooldown` flag
- MCP users can specify cooldown when launching blastoff mode
- More flexibility for different workflow needs (rapid commits vs. batched changes)

## [0.2.0] - 2026-01-03

### Added
- **`--faang` flag** - SILICON VALLEY MODE for standalone tool (works with watch and --once modes)
- **`fckgit_silicon_valley`** - MCP tool for FAANG-tier professional commits
- **`fckgit_professionalize`** - MCP tool to transform casual messages to enterprise-grade
- **`generate_silicon_valley_message()`** - Professional commit message generator
- SILICON_VALLEY.md - Complete guide to professional commit mode
- Buzzword-rich commit message generation
- Technical rationale paragraphs in professional commits

### Changed
- `generate_message()` now accepts `faang_mode` parameter
- `watch_mode()` now accepts `faang_mode` parameter  
- `GitChangeHandler` now accepts `faang_mode` in constructor
- MCP tools expanded from 9 to 11
- Enhanced AI prompts for enterprise-grade message generation
- Updated all documentation to include Silicon Valley mode
- Version bumped to 0.2.0

### Features
- Makes commits sound like they're from a Staff Engineer at Google/Meta/Amazon
- Transforms embarrassing commits into impressive ones
- Includes technical rationale and impact analysis
- Uses enterprise buzzwords: scalability, architecture, optimization, reliability
- Perfect for when recruiters are watching your GitHub
- Available in both standalone tool and MCP server

## [0.1.1] - 2026-01-03

### Added
- **`fckgit_blastoff`** - THE NUCLEAR OPTION - Start fckgit in full automatic watch mode from MCP
- **`fckgit_watch_status`** - Check if watch mode is running
- **`fckgit_stop_watch`** - Stop the watch mode process
- Process management with psutil for background watch mode
- Auto-detection of running fckgit instances per repository

### Changed
- MCP tools expanded from 6 to 9
- Added psutil as MCP optional dependency
- Updated all documentation to include new watch mode tools
- Enhanced installation scripts to include psutil

### Technical Details
- Watch mode runs as detached background process
- Process tracking per repository path
- Graceful termination with fallback to force kill
- Windows and Unix compatible process management

## [0.1.0] - 2026-01-03

### Added
- MCP (Model Context Protocol) server implementation
- Six initial MCP tools for AI assistants:
  - `fckgit_status` - Get git status and diff
  - `fckgit_generate_message` - Generate AI commit messages
  - `fckgit_commit` - Auto-commit with AI-generated message
  - `fckgit_commit_with_message` - Commit with specific message
  - `fckgit_push` - Push to remote with auto-rebase
  - `fckgit_cleanup_lock` - Clean up stale git lock files
- Comprehensive MCP setup documentation (MCP_SETUP.md)
- Installation scripts for MCP support (install_mcp.ps1, install_mcp.sh)
- Test script to verify MCP setup (test_mcp.py)
- Example MCP configuration file (mcp_config_example.json)
- Package structure for mcp_server module

### Changed
- Updated setup.py to include mcp_server package
- Added MCP as optional dependency
- Enhanced README with MCP server section
- Updated pyproject.toml with MCP entry points

### Technical Details
- MCP server runs via stdio transport
- Uses existing fckgit functionality (git operations, Gemini AI)
- Compatible with Cursor IDE, Claude Desktop, and other MCP clients
- Maintains same security model as standalone fckgit tool
