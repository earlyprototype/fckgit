# Using the --faang Flag

Make your standalone fckgit commits sound FAANG professional with one simple flag.

## Quick Start

```bash
# Watch mode with professional commits:
python -m fckgit --faang

# Single professional commit:
python -m fckgit --once --faang
```

That's it. Your commits now sound like they came from a Staff Engineer at Google.

## Watch Mode with --faang

```bash
python -m fckgit --faang
```

**What you'll see:**

```
==================================================
👀 fckgit - Auto-commit watcher started (SILICON VALLEY MODE)
   Repository: my-project
   Branch: main
   Mode: FAANG Professional
   Started: 2026-01-03 14:32:00
   Press Ctrl+C to stop
==================================================

🔍 Changes detected at 2026-01-03 14:32:15
   Files: app.py, utils.js
   Analyzing with AI... (SILICON VALLEY MODE)
✓ Committed: refactor: Enhance algorithmic efficiency in data processing layer

Refactored core processing algorithms to reduce computational complexity
and improve throughput. This optimization enhances system performance
under high-load scenarios and supports our scalability objectives.
  [abc1234] at 14:32:17
📤 Pushed to remote!
==================================================
```

## Single Commit with --faang

```bash
python -m fckgit --once --faang
```

**What you'll see:**

```
🔍 Analyzing changes... (SILICON VALLEY MODE)
✓ Committed: feat: Implement comprehensive observability infrastructure

Enhanced system monitoring capabilities through strategic logging implementation.
This improvement provides critical insights into system behavior, enabling
proactive issue detection and supporting our operational excellence initiatives.
  [def5678] at 14:35:42
📤 Pushed to remote!
```

## Examples

### Example 1: Fixing A Typo

**Without --faang:**
```
fix: correct typo in README
```

**With --faang:**
```
docs: Enhance documentation clarity and maintainability

Improved technical documentation to ensure consistency and readability across
the codebase. This change enhances developer experience and reduces onboarding
friction, supporting our commitment to engineering excellence and scalability.
```

### Example 2: Adding A Print Statement

**Without --faang:**
```
chore: add logging
```

**With --faang:**
```
feat: Implement comprehensive observability infrastructure

Enhanced system monitoring capabilities through strategic logging implementation.
This improvement provides critical insights into system behavior, enabling
proactive issue detection and supporting our operational excellence initiatives.
The enhanced observability directly contributes to improved reliability and
faster incident response.
```

### Example 3: Random File Updates

**Without --faang:**
```
chore: Update files
```

**With --faang:**
```
refactor: Modernize codebase architecture for improved maintainability

Implemented strategic refactoring to enhance code organization and reduce
technical debt. This change improves long-term maintainability and positions
the codebase for future scalability requirements, aligning with industry
best practices and architectural standards.
```

## Combining Flags

You can combine `--faang` with `--once`:

```bash
# Professional single commit:
python -m fckgit --once --faang

# Watch mode is default, so these are equivalent:
python -m fckgit --faang
python -m fckgit --faang --watch  # (there's no --watch flag, it's default)
```

## When To Use --faang

### Use --faang When:
- Sharing repo access with your manager
- Open sourcing your code
- Job hunting and recruiters might check your commits
- Need to justify your salary
- Presenting at standup
- Want to look professional on GitHub
- Co-workers can see your commits
- Building your portfolio

### Skip --faang When:
- Solo project nobody will see
- Don't care about appearances
- 3am coding session
- Actually just being honest
- Speed over professionalism

## The Buzzword Engine

With `--faang`, your commits will include terms like:
- "Architectural improvements"
- "Scalability enhancements"
- "Performance optimization"
- "System reliability"
- "Engineering excellence"
- "Operational efficiency"
- "Best practices"
- "Fault tolerance"

## Performance

The `--faang` flag uses the same Gemini 2.5 Flash-Lite model, so there's no performance difference. Same speed, same cost, just sounds way more professional.

## MCP Server Alternative

If you're using the MCP server, you don't need the `--faang` flag. Just tell your AI assistant:
- "Commit in Silicon Valley mode"
- "Make this commit sound professional"

The MCP server has separate tools (`fckgit_silicon_valley` and `fckgit_professionalize`) that do the same thing.

## Limitations

- Can't professionalize existing commits (only generates new ones)
- Can't preview the message before committing (use MCP `fckgit_professionalize` for previews)
- Always commits (no dry-run mode)

## FAQ

**Q: Can I use --faang by default?**
A: Not yet, but you could create an alias:
```bash
# Add to .bashrc or .zshrc:
alias fckgit-pro="python -m fckgit --faang"

# Then just run:
fckgit-pro
```

**Q: Can I switch between modes mid-watch?**
A: No, you need to stop (`Ctrl+C`) and restart with or without `--faang`.

**Q: Does this actually make me a better engineer?**
A: No. But it makes you look like one.

**Q: Will this get me promoted?**
A: Probably not. But your commits will sound impressive during reviews.

**Q: Can I use this on team repos?**
A: Yes, but your team might wonder why you suddenly sound so professional.

## License

MIT. Use it to impress recruiters, fool your manager, or just feel better about your 3am commits.

Not responsible for any promotions based on commit message quality.
