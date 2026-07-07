# Case Study: Why the MCP Server Sometimes Commits the Wrong Repo

**Status: known limitation.** Workspace is detected once at server startup
(`mcp_server/server.py`, module scope). The `fckgit_debug` tool exposes the
mismatch; per-request re-detection is the planned fix and has not shipped yet.

## Symptom

fckgit's MCP server sometimes doesn't see changes in the project you're
working on. It looks like the server is stuck pointing at whichever
directory it started in.

## Root Cause

```python
# mcp_server/server.py — module scope, runs once per process
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

1. `override` parameter (manual)
2. `WORKSPACE_FOLDER_PATHS` (Cursor/VSCode)
3. `PROJECT_ROOT` (manual config)
4. `git rev-parse --show-toplevel` from cwd
5. `Path.cwd()` fallback

All of these are read at process startup, so none of them help once the
editor switches projects under a running server.

## Dead End: The MCP Roots Protocol

The obvious "proper" fix looked like the MCP roots protocol — but
inspecting the Python SDK showed `roots/list` is a request the **server
sends to the client**, not something the server implements:

```python
# mcp/server/session.py
async def list_roots(self) -> types.ListRootsResult:
    """Send a roots/list request."""
```

There is no `list_roots` decorator on the server side. Whether Cursor
answers this request at all is untested, so it can't be the primary
mechanism.

## Diagnosis Tooling

The `fckgit_debug` tool was extended to make the bug observable:

- when and how the workspace was detected, and time elapsed since
- a fresh detection run compared against the cached value
  (`WORKSPACE_MISMATCH: true` confirms the bug live)
- all workspace/project/cursor environment variables
- git repo info and detector cache statistics

`WorkspaceDetector` also caches `git rev-parse` lookups with a TTL and
exposes `get_cache_stats()` / `invalidate_cache()`.

## Fix Options Considered

| Option | Verdict |
|--------|---------|
| **A. Re-detect on every tool call** (short-TTL cache) | Recommended — simple, reliable, no client cooperation needed |
| **B. Request roots from client** | Proper MCP, but client support is unverified |
| **C. Hybrid** (roots on init, env fallback, per-call re-detect) | Best long-term, most complexity |

Option A is the intended next step; until it lands, restarting the IDE (and
with it the MCP server) after switching projects is the workaround.
