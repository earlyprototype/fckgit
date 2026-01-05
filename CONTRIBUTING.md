# Contributing to fckgit

Thanks for considering contributing to fckgit. Here's how to get started.

## Quick Start

1. **Fork the repo** - Click the fork button
2. **Clone your fork** - `git clone https://github.com/yourname/fckgit.git`
3. **Create a branch** - `git checkout -b feature-name`
4. **Make your changes** - Write some code
5. **Test it** - Make sure it works
6. **Commit** - Ideally using fckgit itself
7. **Push** - `git push origin feature-name`
8. **Open a PR** - Submit your pull request

## What to Contribute

### We Love:
- Bug fixes
- Performance improvements
- New AI model support
- Better error handling
- Documentation improvements
- Test coverage
- Examples and use cases

### Please Don't:
- Add unnecessary dependencies
- Break existing functionality
- Submit PRs without testing
- Add features that bloat the core tool

## Code Style

- Keep it simple and readable
- Follow existing code patterns
- Add comments for complex logic
- Use meaningful variable names
- Keep functions focused and small

## Testing

Before submitting:
1. Test basic functionality: `python -m fckgit --once`
2. Test watch mode: `python -m fckgit` (let it run for a bit)
3. Test MCP server (if modifying): Check tools load in Cursor/Claude
4. Test on your platform (Windows/Linux/Mac/iPad)

## Commit Messages

We use conventional commits:
- `feat:` - New features
- `fix:` - Bug fixes
- `docs:` - Documentation changes
- `refactor:` - Code refactoring
- `test:` - Test additions
- `chore:` - Maintenance tasks

Or just use fckgit and let it write your commits.

## MCP Server Changes

If you're modifying the MCP server:
1. Update tool descriptions if needed
2. Test with both Cursor and Claude Desktop
3. Update `MCP_SETUP.md` documentation
4. Ensure async/await is used correctly
5. Test on Windows (subprocess handling is different)

## Pull Request Process

1. **Update documentation** - If your change affects usage
2. **Update CHANGELOG.md** - Add your changes under "Unreleased"
3. **Test thoroughly** - On your platform at minimum
4. **Describe your changes** - Explain what and why in the PR
5. **Be patient** - We'll review as soon as possible

## Questions?

Open an issue and ask. We're friendly (despite the name).

## License

By contributing, you agree your code will be licensed under MIT.

---

**Remember:** The goal is to make git commits faster and easier. Keep it simple, keep it fast, keep it fun.
