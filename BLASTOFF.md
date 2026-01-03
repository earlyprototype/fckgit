# fckgit BLASTOFF - The Nuclear Option

Your MCP server now has the ability to launch fckgit in full automatic mode.

## What It Does

The `fckgit_blastoff` tool starts fckgit watch mode as a background process that:
- Watches all files in your repository
- Auto-commits every change with AI-generated messages
- Auto-pushes to remote after each commit
- 30 second cooldown between commits
- Runs until you explicitly stop it

## Usage

Just tell your AI assistant:

```
"Blastoff!"
"Start fckgit in automatic mode"
"Launch auto-commit mode"
```

The AI will use the `fckgit_blastoff` tool to start the process in the background.

## Check Status

To see if it's running:

```
"Is fckgit watching?"
"Check fckgit status"
```

The AI will use `fckgit_watch_status` to check.

## Stop It

When you're done:

```
"Stop fckgit"
"Stop watching"
"Kill the watcher"
```

The AI will use `fckgit_stop_watch` to terminate the process.

## How It Works

1. **Background Process**: Launches `python -m fckgit` as a detached background process
2. **Process Tracking**: Uses psutil to track and manage the process
3. **Per-Repository**: Only one watch process per repository at a time
4. **Platform Compatible**: Works on Windows, iPad, and Linux

## Technical Details

### Starting Watch Mode
- Checks if already running in current repo
- Spawns detached process (won't block MCP server)
- Returns process ID for tracking
- Uses CREATE_NEW_PROCESS_GROUP on Windows
- Uses start_new_session on Unix

### Stopping Watch Mode
- Finds process by repository path
- Graceful termination (SIGTERM)
- Waits up to 5 seconds
- Force kill (SIGKILL) if needed
- Can specify PID to stop specific process

### Status Check
- Scans all running Python processes
- Looks for `fckgit` without `--once` flag
- Matches by repository working directory
- Returns PID if found

## Safety Features

- One watcher per repository (prevents duplicates)
- Graceful shutdown before force kill
- Process isolation (won't affect MCP server)
- Repository-specific process tracking

## Requirements

- `psutil>=5.9.0` (installed with MCP dependencies)
- Python 3.8+
- fckgit already installed

Install with:
```bash
pip install "psutil>=5.9.0"
```

Or use the install script:
```bash
.\install_mcp.ps1  # Windows
./install_mcp.sh   # Mac/Linux
```

## Example Session

```
You: "Blastoff!"

AI: *uses fckgit_blastoff*
    "BLASTOFF! fckgit watch mode started (PID: 12345)
    
    fckgit is now watching for changes and will:
    - Auto-commit every change with AI-generated messages
    - Auto-push to remote
    - 30 second cooldown between commits
    
    Use fckgit_stop_watch to stop it."

*You make some changes to files*

*fckgit automatically commits and pushes in the background*

You: "Is it still running?"

AI: *uses fckgit_watch_status*
    "fckgit watch is running (PID: 12345)"

You: "Stop it"

AI: *uses fckgit_stop_watch*
    "Stopped fckgit watch process (PID: 12345)"
```

## Comparison: Manual vs Blastoff

| Feature | Manual MCP Tools | Blastoff Mode |
|---------|------------------|---------------|
| Commits | On AI request | Automatic on file change |
| Watch files | No | Yes |
| Push | Optional parameter | Always |
| Cooldown | None | 30 seconds |
| AI messages | Yes | Yes |
| Background | No | Yes |
| Stops when | After one commit | Until you stop it |

## When to Use

### Use Manual Tools When:
- You want control over each commit
- Working on specific features
- Need custom commit messages
- Testing or reviewing changes

### Use Blastoff When:
- Maximum automation desired
- Rapid prototyping
- You're a vibe warrior
- Don't care about commit history
- Want to focus on coding, not committing

## Warning

This gives your AI the power to start a background process that will automatically commit and push every change you make until you stop it. 

Use with caution. Don't use on production repositories. The AI can't force push (yet).

## Troubleshooting

**"fckgit watch already running"**
- Another instance is running for this repo
- Use `fckgit_stop_watch` first
- Or check with `fckgit_watch_status`

**Process won't stop**
- Check if you have multiple instances
- Try providing specific PID to stop
- Check Task Manager/Activity Monitor

**Can't find process**
- Process may have crashed
- Check with `fckgit_watch_status`
- Try starting fresh with blastoff

**Permissions error**
- Windows: Run as administrator if needed
- Unix: Check process ownership

## What Could Go Wrong?

Everything. But that's the point. Maximum speed, zero accountability.

Just like the readme says: **Prompt - Accept - Publish to Main.**

Now with one command: **Blastoff.**

---

MIT License. Not responsible for any commits to main while you were getting coffee.
