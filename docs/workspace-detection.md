# Case Study: Why the MCP Server Kept Using the First Repository

The server now resolves the repository at the start of each MCP tool call.

## Symptom

After a project switch, status and commit operations still used the
repository the server had detected at startup.

## Root Cause

```python
# Previous startup code in mcp_server/server.py
_workspace_path = _workspace_detector.detect_workspace()
```

The MCP server is a long-running process:

1. Open Project A → server starts → detects Project A.
2. Switch to Project B → the *same* server keeps running.
3. The cached `_workspace_path` still points to Project A.
4. Every git command operates on the wrong directory.

## Detection Strategy

`WorkspaceDetector` (`mcp_server/workspace.py`) resolves the workspace in
priority order:

1. `repo_path` tool argument
2. `WORKSPACE_FOLDER_PATHS` (Cursor/VSCode)
3. `PROJECT_ROOT` (manual config)
4. `git rev-parse --show-toplevel` from cwd
5. `Path.cwd()` fallback

Git resolves a selected subdirectory to its worktree root and Git directory.
If the reported root selects a different Git directory, discovery fails.
This can happen when a nested repository sets `core.worktree` to its
parent's worktree. The server records the device and file ID of each
selected directory and checks them before each Git command and retry.
A new directory at the old checkout path fails this check.

If the editor keeps the server's original environment and working directory,
pass the new project's absolute path as `repo_path`.

## Dead End: The MCP Roots Protocol

In the Python SDK, the server sends a `roots/list` request to the client.

```python
# mcp/server/session.py
async def list_roots(self) -> types.ListRootsResult:
    """Send a roots/list request."""
```

There is no `list_roots` decorator on the server side. Whether Cursor
answers this request at all is untested, so it can't be the primary
mechanism.

## Diagnosis Tooling

`fckgit_debug` reports the selected workspace, how it was selected, its
Git paths, and a status summary. Check `git_root` before committing.

`WorkspaceDetector` also caches `git rev-parse` lookups with a TTL and
exposes `get_cache_stats()` / `invalidate_cache()`.

## Fix Options Considered

| Option | Verdict |
|--------|---------|
| **A. Re-detect on every tool call** | Uses the settings visible to the server. Clients with a fixed environment and working directory pass the active project's `repo_path`. |
| **B. Request roots from client** | Proper MCP, but client support is unverified |
| **C. Hybrid** (roots on init, env fallback, per-call re-detect) | Best long-term, most complexity |

The server now uses per-call detection and accepts an explicit target.
To verify a switch, call `fckgit_debug` with the same arguments and inspect
`workspace_path`, `detection_method` and `git_root`.
