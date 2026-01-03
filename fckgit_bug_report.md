# fckgit Bug Report: Hangs on Initial Commit with Untracked Files

## Environment
- **OS**: Windows 10 (Build 26100)
- **Python**: 3.12.3
- **fckgit**: v0.1.0
- **Date**: 2026-01-03

## Issue
fckgit hangs indefinitely when starting watch mode in a fresh git repository with untracked files.

## Reproduction Steps
1. Initialize fresh git repo: `git init`
2. Add remote: `git remote add origin <repo-url>`
3. Create files but don't stage them (untracked files present)
4. Run `python -m fckgit`
5. fckgit detects existing changes but hangs at "Found existing changes, committing before starting watch..."

## Expected Behaviour
fckgit should stage untracked files, generate a commit message, commit, and push before entering watch mode.

## Actual Behaviour
fckgit hangs indefinitely after printing "Found existing changes, committing before starting watch..."

## Root Cause
In `fckgit.py` lines 263-277, the watch mode startup checks for existing changes using `git status --porcelain`, but then attempts to get diff using `get_diff()` or `get_staged_diff()` **without staging files first**.

Untracked files don't appear in `git diff` output, so:
- `get_diff()` returns empty string (no staged changes)
- `get_staged_diff()` returns empty string (no unstaged tracked changes)
- The diff is effectively empty or contains only metadata
- Gemini API receives a poor/empty prompt and either:
  - Takes ages to respond to the odd prompt
  - Returns an error that isn't caught properly
  - Times out silently

## Code Location
```python
# Lines 263-277 in fckgit.py
status_result = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True, encoding='utf-8', errors='replace')
if status_result.stdout.strip():
    print("🔍 Found existing changes, committing before starting watch...")
    diff = get_staged_diff() or get_diff()  # BUG: This returns empty for untracked files!
    if diff.strip():
        try:
            message = generate_message(diff)
            if message:
                if commit(message):  # commit() does git add -A internally, but too late
                    push()
```

## Proposed Fix
Stage files **before** getting the diff in the watch mode startup:

```python
status_result = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True, encoding='utf-8', errors='replace')
if status_result.stdout.strip():
    print("🔍 Found existing changes, committing before starting watch...")
    
    # FIX: Stage files first so they appear in diff
    subprocess.run(["git", "add", "-A"], capture_output=True)
    
    diff = get_staged_diff() or get_diff()
    if diff.strip():
        try:
            message = generate_message(diff)
            if message:
                if commit(message):
                    push()
```

Alternatively, use `git add -A` and `git diff --cached` to ensure untracked files are included.

## Workaround
Manual first commit before running fckgit:
```bash
git add -A
git commit -m "Initial commit"
git push -u origin main
python -m fckgit
```

## Additional Notes
- This only affects fresh repos with untracked files
- Once the first commit is made manually, fckgit works perfectly
- The `commit()` function (line 88) does run `git add -A`, but this happens **after** trying to generate the message from an empty diff
- The process appears "stuck" but is likely waiting for Gemini API timeout/response

## Severity
**Medium** - Blocks first-time use in fresh repos, but workaround is simple and only needed once.

## Suggested Enhancement
Add better error handling and timeout for Gemini API calls with informative messages when the API call takes too long or fails.
