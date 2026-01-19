# Workspace Detection Diagnostic Findings

## Date: 2026-01-19

## Problem Statement
User reports that fckgit MCP sometimes doesn't detect changes in other repositories. Suspects the MCP server is always pointing to its installation directory instead of the current project directory.

## Diagnostic Steps Completed

### 1. Enhanced Debug Tool
**Status:** ✅ COMPLETED

**Changes Made:**
- Added `get_workspace_info()` method to `WorkspaceDetector` class
- Tracks detection timestamp, method used, and time since detection
- Enhanced `fckgit_debug` tool to show:
  - Workspace detection details (when, how, time elapsed)
  - Fresh detection comparison (what would be detected NOW vs cached)
  - All environment variables related to workspace/project/cursor
  - Git repository information
  - Cache statistics

**Code Location:** 
- `mcp_server/workspace.py` - lines 66-67, 301-315
- `mcp_server/server.py` - lines 706-780

### 2. MCP SDK Roots Protocol Investigation
**Status:** ✅ COMPLETED

**Findings:**

#### MCP Types Available:
```python
['ListRootsRequest', 'ListRootsResult', 
 "Notification[..., Literal['notifications/roots/list_changed']]", 
 "Request[..., Literal['roots/list']]", 
 'Root', 'RootModel', 'RootsCapability', 'RootsListChangedNotification']
```

#### Root Type Signature:
```python
Root(*, uri: FileUrl, name: str | None = None, _meta: dict | None = None, **extra_data)
```

#### Server Methods Available:
```
call_tool, completion, create_initialization_options, experimental,
get_capabilities, get_prompt, list_prompts, list_resource_templates,
list_resources, list_tools, progress_notification, read_resource,
request_context, run, set_logging_level, subscribe_resource,
unsubscribe_resource
```

**NO `list_roots` decorator found** - This is a **CLIENT-TO-SERVER** request, not server-implemented.

#### Session Methods:
Found in `mcp/server/session.py`:
```python
async def list_roots(self) -> types.ListRootsResult:
    """Send a roots/list request."""
    return await self.send_request(
        types.ServerRequest(types.ListRootsRequest()),
        types.ListRootsResult,
    )
```

This is for the **server to request roots FROM the client**, not to provide roots.

### 3. Core Issue Identified

**THE SMOKING GUN:**

```python
# mcp_server/server.py lines 56-62
# Detect workspace at startup
try:
    _workspace_path = _workspace_detector.detect_workspace()
    logger.info("Workspace detected", workspace=str(_workspace_path))
except WorkspaceError as e:
    logger.error("Failed to detect workspace", error=str(e))
    _workspace_path = Path.cwd()
    logger.warning("Using current directory as fallback", workspace=str(_workspace_path))
```

**Problem:** Workspace is detected ONCE at MCP server startup and cached globally. The MCP server is a long-running process, so:
- When you open Project A, the server starts and detects Project A
- When you switch to Project B, the server is STILL RUNNING
- The cached `_workspace_path` still points to Project A
- All git commands operate on the wrong directory

## Environment Variable Analysis

### Current Detection Strategy (Priority Order):
1. `override` parameter (manual)
2. `WORKSPACE_FOLDER_PATHS` (Cursor/VSCode)
3. `PROJECT_ROOT` (manual config)
4. `git rev-parse --show-toplevel` (from cwd)
5. `Path.cwd()` (fallback)

### Critical Question: Is `WORKSPACE_FOLDER_PATHS` per-process or per-request?

**Hypothesis:** If `WORKSPACE_FOLDER_PATHS` is set once when the MCP server process starts, it will never update when switching projects.

**Need to test:** Check if environment variables are updated per-request or frozen at process startup.

## Proposed Solutions

### Option A: Re-detect Workspace on Every Tool Call (QUICK FIX)
**Pros:**
- Simple to implement
- Works immediately
- No protocol changes needed

**Cons:**
- Performance overhead (mitigated by caching with short TTL)
- Doesn't use MCP protocol properly

**Implementation:**
```python
@server.call_tool()
async def handle_call_tool(name: str, arguments: dict[str, Any] | None):
    # Re-detect workspace for THIS request
    current_workspace = _workspace_detector.detect_workspace()
    # Use current_workspace instead of global _workspace_path
```

### Option B: Request Roots from Client (PROPER MCP WAY)
**Pros:**
- Uses MCP protocol correctly
- Client explicitly tells us which roots are active
- Handles multi-root workspaces

**Cons:**
- More complex
- Need to test if Cursor actually responds to roots requests
- May not be supported by all clients

**Implementation:**
```python
# During initialization or on-demand
async def update_workspace_from_client():
    session = server.request_context.session
    roots_result = await session.list_roots()
    if roots_result.roots:
        first_root = roots_result.roots[0]
        # Update workspace from root URI
        _workspace_path = Path(first_root.uri.path)
```

### Option C: Hybrid Approach (RECOMMENDED)
1. Try to request roots from client on initialization
2. Fall back to environment variable detection
3. Re-detect on every tool call (with caching)
4. Invalidate cache when environment changes

## Next Steps

### Required Tests:
1. ✅ Install updated debug tool
2. ⏳ Restart Cursor to reload MCP server
3. ⏳ Run `fckgit_debug` in fckgit project - note workspace and timestamp
4. ⏳ Switch to different project
5. ⏳ Run `fckgit_debug` again - check if:
   - Workspace path is still fckgit (CONFIRMS BUG)
   - `fresh_detection_would_give` shows correct path
   - `WORKSPACE_MISMATCH` is True
   - Environment variables show new project or old project
6. ⏳ Document findings
7. ⏳ Implement fix based on test results

### Questions to Answer:
- Does `WORKSPACE_FOLDER_PATHS` update when switching projects?
- Does `Path.cwd()` change when switching projects?
- Can we successfully request roots from Cursor client?
- What's the performance impact of per-request detection?

## Recommendations

**Immediate Action:** Implement Option A (re-detect per request) as it's the most reliable fix that doesn't depend on client capabilities.

**Future Enhancement:** Investigate Option B (MCP roots protocol) to see if Cursor supports it properly.

**Cache Strategy:** Keep 5-second TTL cache to balance performance vs responsiveness to project switches.
