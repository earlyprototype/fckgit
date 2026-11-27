import asyncio
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlsplit
from urllib.request import url2pathname

from fckgit_gemini import (
    GeminiConfigurationError, check_diff_for_key, check_files_before_staging, configured_key, get_client,
)

import psutil
from mcp.server.models import InitializationOptions
import mcp.types as types
from mcp.server import NotificationOptions, Server
import mcp.server.stdio

# Import our new modules
from .workspace import WorkspaceDetector, WorkspaceError, InvalidWorkspaceError
from .git_utils import detect_git_repo_type, workspace_git_env
from .platform_utils import get_subprocess_kwargs, check_subprocess_security
from .logging_config import setup_logging, init_logger

# Initialize logging (stderr to not interfere with stdio protocol)
setup_logging(level=os.environ.get('LOG_LEVEL', 'INFO'))
logger = init_logger('mcp_server')

# Create MCP server
server = Server("fckgit")

# Track running watch processes
_watch_processes: dict[str, subprocess.Popen] = {}


async def client_workspace_path() -> Optional[str]:
    """Read live roots when the connected client advertises them."""
    try:
        session = server.request_context.session
    except LookupError:
        return None
    if not session.check_client_capability(types.ClientCapabilities(roots=types.RootsCapability())):
        return None
    try:
        roots = (await session.list_roots()).roots
    except Exception as exc:
        raise WorkspaceError("Cannot read client roots. Supply a workspace_path.") from exc
    if len(roots) != 1:
        raise WorkspaceError("Ambiguous workspace. Supply one workspace_path.")
    uri = urlsplit(str(roots[0].uri))
    if uri.scheme != "file" or uri.query or uri.fragment:
        raise InvalidWorkspaceError("The client root must be a file URI.")
    path = uri.path
    if uri.netloc and uri.netloc.lower() != "localhost":
        if sys.platform != "win32":
            raise InvalidWorkspaceError("The client root must be a local directory.")
        path = f"//{uri.netloc}{path}"
    return url2pathname(path)


@dataclass
class GitCommandResult:
    """Result from a git command execution."""
    stdout: str
    stderr: str
    returncode: int
    duration: float  # seconds
    command: str  # for logging/debugging


async def run_git_command(
    cmd: list[str],
    cwd: Path,
    timeout: float = 15.0,
    retry: int = 1
) -> GitCommandResult:
    """
    Execute git command with proper error handling and security.
    
    Args:
        cmd: Git command as list (e.g., ['git', 'status'])
        cwd: Workspace selected for this request
        timeout: Command timeout in seconds
        retry: Number of retries for transient failures
        
    Returns:
        GitCommandResult with stdout, stderr, returncode, duration
        
    Raises:
        WorkspaceError: If workspace is invalid
    """
    start_time = time.time()
    
    # Security check
    try:
        check_subprocess_security(cmd)
    except ValueError as e:
        logger.error("Subprocess security check failed", error=str(e), command=cmd)
        return GitCommandResult(
            stdout="",
            stderr=f"Security check failed: {e}",
            returncode=1,
            duration=0.0,
            command=' '.join(cmd)
        )
    
    # Get platform-specific subprocess kwargs
    kwargs = get_subprocess_kwargs(is_background=False, timeout=timeout)
    kwargs['cwd'] = str(cwd)
    kwargs['env'] = workspace_git_env()
    
    # Log command execution (without sensitive data)
    cmd_str = ' '.join(cmd)
    logger.debug("Executing git command", command=cmd_str, cwd=str(cwd))
    
    # Execute with retry logic
    last_error = None
    for attempt in range(retry + 1):
        try:
            loop = asyncio.get_event_loop()
        
            # Run command asynchronously
            result = await loop.run_in_executor(
                None,
                lambda: subprocess.run(cmd, **kwargs)
            )
            
            duration = time.time() - start_time
            
            logger.debug(
                "Git command completed",
                command=cmd_str,
                returncode=result.returncode,
                duration_ms=int(duration * 1000)
            )
            
            return GitCommandResult(
                stdout=result.stdout,
                stderr=result.stderr,
                returncode=result.returncode,
                duration=duration,
                command=cmd_str
            )
            
        except subprocess.TimeoutExpired as e:
            last_error = f"Command timed out after {timeout}s"
            logger.warning(
                "Git command timeout",
                command=cmd_str,
                timeout=timeout,
                attempt=attempt + 1
            )
            if attempt < retry:
                await asyncio.sleep(0.5)  # Brief delay before retry
                continue
                
        except Exception as e:
            last_error = str(e)
            logger.error(
                "Git command failed",
                command=cmd_str,
                error=str(e),
                attempt=attempt + 1
            )
            if attempt < retry:
                await asyncio.sleep(0.5)
                continue
    
    # All retries exhausted
    duration = time.time() - start_time
    return GitCommandResult(
        stdout="",
        stderr=last_error or "Command failed",
        returncode=1,
        duration=duration,
        command=cmd_str
    )


async def get_diff(workspace: Path) -> str:
    """Get unstaged changes."""
    result = await run_git_command(["git", "diff"], workspace)
    return result.stdout if result.returncode == 0 else ""


async def get_staged_diff(workspace: Path) -> str:
    """Get staged changes."""
    result = await run_git_command(["git", "diff", "--cached"], workspace)
    return result.stdout if result.returncode == 0 else ""


def generate_commit_message(diff: str, workspace: Optional[Path] = None) -> str:
    """Generate commit message using Gemini."""
    if not diff.strip():
        return "chore: Update files"
    
    prompt = f"""Generate a concise git commit message following Conventional Commits format.

Rules:
- Start with type: feat, fix, docs, style, refactor, test, chore
- Keep the subject line under 72 characters
- Be specific but concise

Changes:
{diff[:4000]}

Output ONLY the commit message, nothing else."""
    
    check_diff_for_key(diff, workspace)
    client = get_client(workspace)
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash-lite',
            contents=prompt
        )
        return response.text.strip().strip('"').strip("'")
    except Exception as e:
        return f"chore: Update files (AI error: {str(e)})"


def generate_silicon_valley_message(diff: str, workspace: Optional[Path] = None) -> str:
    """Generate a FAANG-tier professional commit message."""
    if not diff.strip():
        return "refactor: Optimize codebase architecture for improved maintainability"
    
    prompt = f"""You are a senior engineer at a FAANG company. Generate a professional, enterprise-grade git commit message that sounds impressive and makes the changes seem important.

Requirements:
- Use Conventional Commits format (feat, fix, refactor, perf, docs, test, chore)
- Make it sound impressive and professional
- Use enterprise buzzwords naturally: "scalability", "performance", "architecture", "optimization", "reliability"
- Include a brief body paragraph explaining the technical rationale
- Sound like it came from a Staff Engineer at Google/Meta/Amazon
- Make even trivial changes sound important
- Keep subject line under 72 characters

Changes:
{diff[:4000]}

Output format:
<subject line>

<body paragraph explaining the technical rationale and impact>

Output ONLY the commit message, nothing else."""
    
    check_diff_for_key(diff, workspace)
    client = get_client(workspace)
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash-lite',
            contents=prompt
        )
        return response.text.strip().strip('"').strip("'")
    except Exception as e:
        return f"refactor: Implement strategic codebase improvements\n\nEnhanced system architecture to improve maintainability and operational excellence. This change aligns with industry best practices and positions the codebase for future scalability."


def professionalize_message(casual_message: str, workspace: Optional[Path] = None) -> str:
    """Transform a casual commit message into a FAANG-tier professional one."""
    if not casual_message.strip():
        return "refactor: Optimize codebase architecture"
    
    prompt = f"""You are a senior engineer at a FAANG company. Transform this casual commit message into an impressive, enterprise-grade commit message.

Casual message: "{casual_message}"

Requirements:
- Keep the same type prefix (feat, fix, etc.) if present
- Make it sound professional and important
- Use enterprise buzzwords: "scalability", "architecture", "optimization", "reliability", "performance"
- Add a body paragraph with technical rationale
- Sound like it came from a Staff Engineer at Google/Meta/Amazon
- Keep subject line under 72 characters

Output format:
<professional subject line>

<technical rationale paragraph>

Output ONLY the professional commit message, nothing else."""
    
    client = get_client(workspace)
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash-lite',
            contents=prompt
        )
        return response.text.strip().strip('"').strip("'")
    except Exception as e:
        return f"refactor: {casual_message}\n\nImplemented strategic improvements to enhance system architecture and operational efficiency. This change improves maintainability and positions the codebase for future scalability."


def cleanup_git_lock(workspace: Path):
    """Remove stale git lock file if it exists."""
    lock_file = workspace / ".git" / "index.lock"
    if lock_file.exists():
        try:
            lock_file.unlink()
            logger.debug("Cleaned up git lock file", lock_file=str(lock_file))
            return True
        except Exception as e:
            logger.warning("Failed to clean up git lock file", lock_file=str(lock_file), error=str(e))
            return False
    return False


async def stage_all_changes(workspace: Path) -> Optional[str]:
    try:
        await asyncio.get_running_loop().run_in_executor(
            None, check_files_before_staging, workspace, workspace_git_env()
        )
    except RuntimeError as exc:
        return str(exc)
    result = await run_git_command(["git", "add", "-A"], workspace)
    if result.returncode:
        return f"Failed to stage files: {result.stderr.strip()}"
    return None


async def commit_changes(workspace: Path, message: str, stage_all: bool = True) -> tuple[bool, str]:
    """Stage all changes and commit."""
    if stage_all:
        error = await stage_all_changes(workspace)
        if error:
            return False, error
    
    result = await run_git_command(["git", "commit", "-m", message], workspace)
    
    if result.returncode == 0:
        # Get the commit hash
        hash_result = await run_git_command(["git", "rev-parse", "--short", "HEAD"], workspace)
        commit_hash = hash_result.stdout.strip() if hash_result.returncode == 0 else "unknown"
        return True, f"Committed successfully [{commit_hash}]: {message}"
    else:
        error_msg = result.stderr.strip() or result.stdout.strip() or "Unknown error"
        if "nothing to commit" in error_msg.lower():
            return False, "Nothing to commit"
        return False, f"Commit failed: {error_msg}"


async def push_to_remote(workspace: Path) -> tuple[bool, str]:
    """Push to remote repository."""
    result = await run_git_command(["git", "push"], workspace)
    
    if result.returncode == 0:
        return True, "Successfully pushed to remote"
    
    error_msg = result.stderr.strip() or result.stdout.strip() or "Unknown error"
    
    # Try to handle rejected push
    if "rejected" in error_msg.lower() or "fetch first" in error_msg.lower():
        # Try to pull with rebase
        pull_result = await run_git_command(["git", "pull", "--rebase"], workspace)
        
        if pull_result.returncode == 0:
            # Try pushing again
            retry_result = await run_git_command(["git", "push"], workspace)
            if retry_result.returncode == 0:
                return True, "Pulled, rebased, and pushed successfully"
            return False, "Failed to push after rebase"
        return False, "Failed to pull for rebase"
    
    return False, f"Push failed: {error_msg}"


async def get_repo_path(workspace: Path) -> str:
    """Get the current repository root path."""
    result = await run_git_command(["git", "rev-parse", "--show-toplevel"], workspace)
    if result.returncode == 0:
        return result.stdout.strip()
    return str(workspace)


def find_fckgit_processes() -> list[dict[str, Any]]:
    """Find running fckgit watch processes."""
    processes = []
    try:
        for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'cwd']):
            try:
                cmdline = proc.info['cmdline'] or []
                cmdline_str = ' '.join(cmdline)
                
                # Look for python -m fckgit or fckgit without --once
                if ('python' in cmdline_str.lower() and 
                    'fckgit' in cmdline_str and 
                    '--once' not in cmdline_str):
                    processes.append({
                        'pid': proc.info['pid'],
                        'cmdline': cmdline_str,
                        'cwd': proc.info.get('cwd', 'unknown')
                    })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
    except Exception:
        pass
    return processes


async def start_watch_mode(workspace: Path, cooldown: int = 30, faang_mode: bool = False) -> tuple[bool, str, Optional[int]]:
    """Start fckgit in watch mode as a background process."""
    repo_path = await get_repo_path(workspace)
    
    # Check if already running in this repo
    # Normalize paths for comparison (handles Windows forward/backslash differences)
    repo_path_normalized = str(Path(repo_path).resolve())
    existing = find_fckgit_processes()
    for proc in existing:
        proc_cwd_normalized = str(Path(proc['cwd']).resolve()) if proc['cwd'] != 'unknown' else 'unknown'
        if proc_cwd_normalized == repo_path_normalized:
            return False, f"fckgit watch already running (PID: {proc['pid']})", proc['pid']
    
    # Build command with cooldown and faang mode
    cmd = [sys.executable, "-m", "fckgit", "--cooldown", str(cooldown)]
    if faang_mode:
        cmd.append("--faang")
    
    # Start the process
    try:
        env = workspace_git_env()
        key = configured_key(workspace)
        if key:
            env["GEMINI_API_KEY"] = key
        if sys.platform == 'win32':
            background = {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW}
        else:
            background = {"start_new_session": True}
        process = subprocess.Popen(
            cmd, cwd=repo_path, env=env, stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **background,
        )
        
        # Store the process
        _watch_processes[repo_path] = process
        
        return True, f"fckgit watch mode started (PID: {process.pid})", process.pid
    except Exception as e:
        return False, f"Failed to start watch mode: {str(e)}", None


async def stop_watch_mode(workspace: Path, pid: Optional[int] = None) -> tuple[bool, str]:
    """Stop a running fckgit watch process."""
    repo_path = await get_repo_path(workspace)
    
    # Normalize paths for comparison (handles Windows forward/backslash differences)
    repo_path_normalized = str(Path(repo_path).resolve())
    existing = find_fckgit_processes()
    for proc_info in existing:
        if pid is not None and proc_info['pid'] != pid:
            continue
        proc_cwd_normalized = str(Path(proc_info['cwd']).resolve()) if proc_info['cwd'] != 'unknown' else 'unknown'
        if proc_cwd_normalized == repo_path_normalized:
            try:
                proc = psutil.Process(proc_info['pid'])
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except psutil.TimeoutExpired:
                    proc.kill()
                return True, f"Stopped fckgit watch process (PID: {proc_info['pid']})"
            except Exception as e:
                return False, f"Failed to stop process: {str(e)}"
    
    return False, "No fckgit watch process found for this repository"


async def get_watch_status(workspace: Path) -> tuple[bool, str]:
    """Check if fckgit watch is running in current repo."""
    repo_path = await get_repo_path(workspace)
    existing = find_fckgit_processes()
    
    # Normalize paths for comparison (handles Windows forward/backslash differences)
    repo_path_normalized = str(Path(repo_path).resolve())
    
    for proc in existing:
        proc_cwd_normalized = str(Path(proc['cwd']).resolve()) if proc['cwd'] != 'unknown' else 'unknown'
        if proc_cwd_normalized == repo_path_normalized:
            return True, f"fckgit watch is running (PID: {proc['pid']})"
    
    # Enhanced debugging info if not found
    if existing:
        debug_info = f"fckgit watch is not running in this repo.\n\nDetected repo: {repo_path_normalized}\n\nRunning fckgit processes:"
        for proc in existing:
            proc_cwd_normalized = str(Path(proc['cwd']).resolve()) if proc['cwd'] != 'unknown' else 'unknown'
            debug_info += f"\n  PID {proc['pid']}: {proc_cwd_normalized}"
        return False, debug_info
    
    return False, "fckgit watch is not running"


@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """List available tools."""
    tools = [
        types.Tool(
            name="fckgit_debug",
            description="Debug MCP server configuration and git repo detection",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        types.Tool(
            name="fckgit_status",
            description="Get the current git status and diff of the repository",
            inputSchema={
                "type": "object",
                "properties": {
                    "include_diff": {
                        "type": "boolean",
                        "description": "Whether to include the full diff in the response",
                        "default": False
                    }
                }
            }
        ),
        types.Tool(
            name="fckgit_generate_message",
            description="Generate an AI commit message based on current changes without committing",
            inputSchema={
                "type": "object",
                "properties": {
                    "use_staged": {
                        "type": "boolean",
                        "description": "Use staged changes instead of all changes",
                        "default": False
                    }
                }
            }
        ),
        types.Tool(
            name="fckgit_commit",
            description="Auto-commit with an AI-generated commit message",
            inputSchema={
                "type": "object",
                "properties": {
                    "push": {
                        "type": "boolean",
                        "description": "Automatically push after committing",
                        "default": False
                    },
                    "stage_all": {
                        "type": "boolean",
                        "description": "Stage all changes before committing",
                        "default": True
                    }
                }
            }
        ),
        types.Tool(
            name="fckgit_commit_with_message",
            description="Commit with a specific message (no AI generation)",
            inputSchema={
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "description": "The commit message to use"
                    },
                    "push": {
                        "type": "boolean",
                        "description": "Automatically push after committing",
                        "default": False
                    },
                    "stage_all": {
                        "type": "boolean",
                        "description": "Stage all changes before committing",
                        "default": True
                    }
                },
                "required": ["message"]
            }
        ),
        types.Tool(
            name="fckgit_push",
            description="Push commits to remote repository (handles conflicts with auto-rebase)",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        types.Tool(
            name="fckgit_cleanup_lock",
            description="Clean up stale git lock files",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        types.Tool(
            name="fckgit_blastoff",
            description="START AUTOMATIC WATCH MODE - Launch fckgit in full auto mode (watches files, auto-commits, auto-pushes). Maximum automation. This runs in the background until stopped.",
            inputSchema={
                "type": "object",
                "properties": {
                    "cooldown": {
                        "type": "number",
                        "description": "Cooldown time in seconds between commits (default: 30)",
                        "default": 30
                    },
                    "faang_mode": {
                        "type": "boolean",
                        "description": "Enable Silicon Valley mode for FAANG-tier professional commit messages (default: false)",
                        "default": False
                    }
                }
            }
        ),
        types.Tool(
            name="fckgit_stop_watch",
            description="Stop the running fckgit watch mode process",
            inputSchema={
                "type": "object",
                "properties": {
                    "pid": {
                        "type": "number",
                        "description": "Optional: specific process ID to stop"
                    }
                }
            }
        ),
        types.Tool(
            name="fckgit_watch_status",
            description="Check if fckgit watch mode is currently running",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        types.Tool(
            name="fckgit_silicon_valley",
            description="SILICON VALLEY MODE - Generate a FAANG-tier professional commit message that makes your code sound enterprise-ready. Transforms casual changes into impressive, buzzword-rich commits.",
            inputSchema={
                "type": "object",
                "properties": {
                    "push": {
                        "type": "boolean",
                        "description": "Automatically push after committing",
                        "default": False
                    },
                    "stage_all": {
                        "type": "boolean",
                        "description": "Stage all changes before committing",
                        "default": True
                    }
                }
            }
        ),
        types.Tool(
            name="fckgit_professionalize",
            description="Transform an existing casual commit message into a FAANG-tier professional one. Makes it sound like a Staff Engineer wrote it.",
            inputSchema={
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "description": "The casual commit message to professionalize"
                    }
                },
                "required": ["message"]
            }
        )
    ]

    for tool in tools:
        tool.inputSchema["properties"]["workspace_path"] = {
            "type": "string",
            "description": "Absolute path to the workspace for this request. Use to select one of several roots.",
        }
    return tools


@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict[str, Any] | None
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """Handle tool execution requests."""
    try:
        return await _call_tool(name, arguments)
    except GeminiConfigurationError as exc:
        return [types.TextContent(type="text", text=str(exc))]


async def _call_tool(name: str, arguments: dict[str, Any] | None):
    
    if arguments is None:
        arguments = {}
    
    detector = WorkspaceDetector()
    try:
        target = arguments.get("workspace_path")
        if "workspace_path" not in arguments:
            target = await client_workspace_path()
        elif not isinstance(target, str) or not Path(target).is_absolute():
            raise InvalidWorkspaceError("workspace_path must be an absolute directory path.")
        workspace = detector.detect_workspace(override=target)
    except WorkspaceError as exc:
        return [types.TextContent(type="text", text=f"Error: {exc}")]

    if name in {"fckgit_generate_message", "fckgit_commit", "fckgit_silicon_valley",
                "fckgit_professionalize", "fckgit_blastoff"}:
        get_client(workspace)

    # Debug tool doesn't require git repo
    if name == "fckgit_debug":
        import datetime
        
        debug_info = {}
        
        # === WORKSPACE DETECTION DIAGNOSTICS ===
        debug_info["=== WORKSPACE DETECTION ==="] = ""
        
        # Current workspace info from detector
        workspace_info = detector.get_workspace_info()
        debug_info["workspace_path"] = str(workspace)
        debug_info["workspace_exists"] = workspace.exists()
        debug_info["workspace_is_dir"] = workspace.is_dir()
        if target is not None and "workspace_path" not in arguments:
            debug_info["detection_method"] = "mcp_roots"
        else:
            debug_info["detection_method"] = workspace_info.get('detection_method', 'unknown')
        
        if workspace_info.get('detection_timestamp'):
            timestamp = workspace_info['detection_timestamp']
            debug_info["detected_at"] = datetime.datetime.fromtimestamp(timestamp).isoformat()
            debug_info["seconds_since_detection"] = round(workspace_info.get('time_since_detection', 0), 2)
        
        # Current process info
        debug_info["current_cwd"] = str(Path.cwd())
        debug_info["mcp_server_file"] = __file__
        
        debug_info["env_vars"] = {
            key: os.environ[key] for key in ("WORKSPACE_FOLDER_PATHS", "PROJECT_ROOT")
            if key in os.environ
        }

        # === GIT REPOSITORY INFO ===
        debug_info["=== GIT REPOSITORY ==="] = ""
        
        git_info = detect_git_repo_type(workspace)
        if git_info:
            debug_info["git_root"] = str(git_info.root)
            debug_info["git_dir"] = str(git_info.git_dir)
            debug_info["is_worktree"] = git_info.is_worktree
            debug_info["is_submodule"] = git_info.is_submodule
            debug_info["is_bare"] = git_info.is_bare
            if git_info.superproject_root:
                debug_info["superproject_root"] = str(git_info.superproject_root)
        else:
            debug_info["git_repository"] = False
        
        # Try running git status
        result = await run_git_command(["git", "--no-optional-locks", "status", "--porcelain"], workspace)
        debug_info["git_status_returncode"] = result.returncode
        debug_info["git_status_success"] = result.returncode == 0
        if result.returncode != 0:
            debug_info["git_status_error"] = result.stderr[:200] if result.stderr else ""
        else:
            changes_count = len([l for l in result.stdout.split('\n') if l.strip()])
            debug_info["git_changes_detected"] = changes_count
        
        # === CACHE STATS ===
        debug_info["=== CACHE STATS ==="] = ""
        cache_stats = detector.get_cache_stats()
        debug_info["cache_stats"] = cache_stats
        
        return [types.TextContent(type="text", text=str(debug_info))]
    
    # Check if in git repo (skip for debug tool)
    result = await run_git_command(["git", "rev-parse", "--git-dir"], workspace)
    if result.returncode != 0:
        return [types.TextContent(
            type="text",
            text="Error: Not a git repository"
        )]
    
    if name == "fckgit_status":
        include_diff = arguments.get("include_diff", False)
        
        status_result = await run_git_command(["git", "--no-optional-locks", "status", "--porcelain"], workspace)
        if status_result.returncode:
            return [types.TextContent(type="text", text=f"Status failed: {status_result.stderr.strip()}")]
        status = status_result.stdout
        if not status.strip():
            result = "No changes detected"
        else:
            files = [line[3:] for line in status.splitlines()]
            result = f"Changed files ({len(files)}):\n" + "\n".join(f"  - {f}" for f in files)
            
            if include_diff:
                staged = await get_staged_diff(workspace)
                unstaged = await get_diff(workspace)
                diff = staged or unstaged
                if diff:
                    result += f"\n\nDiff:\n{diff}"
        
        return [types.TextContent(type="text", text=f"Workspace: {workspace}\n{result}")]
    
    elif name == "fckgit_generate_message":
        use_staged = arguments.get("use_staged", False)
        
        if use_staged:
            diff = await get_staged_diff(workspace)
        else:
            staged = await get_staged_diff(workspace)
            unstaged = await get_diff(workspace)
            diff = staged or unstaged
        
        if not diff.strip():
            return [types.TextContent(type="text", text="No changes to generate message for")]
        
        message = generate_commit_message(diff, workspace)
        return [types.TextContent(type="text", text=f"Generated message: {message}")]
    
    elif name in ("fckgit_commit", "fckgit_silicon_valley"):
        push = arguments.get("push", False)
        stage_all = arguments.get("stage_all", True)
        
        # Get diff for message generation
        if stage_all:
            # Stage first so we can see untracked files
            error = await stage_all_changes(workspace)
            if error:
                return [types.TextContent(type="text", text=error)]
        
        diff = await get_staged_diff(workspace)
        
        if not diff.strip():
            return [types.TextContent(type="text", text="No changes to commit")]
        
        # Generate message
        if name == "fckgit_silicon_valley":
            message = generate_silicon_valley_message(diff, workspace)
        else:
            message = generate_commit_message(diff, workspace)
        
        # Commit
        success, result_msg = await commit_changes(workspace, message, stage_all=False)  # Already staged
        
        if not success:
            return [types.TextContent(type="text", text=result_msg)]
        
        if name == "fckgit_silicon_valley":
            result_msg = "SILICON VALLEY MODE ACTIVATED\n\n" + result_msg

        # Push if requested
        if push:
            push_success, push_msg = await push_to_remote(workspace)
            result_msg += f"\n{push_msg}"
        
        return [types.TextContent(type="text", text=result_msg)]
    
    elif name == "fckgit_commit_with_message":
        message = arguments.get("message")
        push = arguments.get("push", False)
        stage_all = arguments.get("stage_all", True)
        
        if not message:
            return [types.TextContent(type="text", text="Error: message is required")]
        
        # Commit
        success, result_msg = await commit_changes(workspace, message, stage_all=stage_all)
        
        if not success:
            return [types.TextContent(type="text", text=result_msg)]
        
        # Push if requested
        if push:
            push_success, push_msg = await push_to_remote(workspace)
            result_msg += f"\n{push_msg}"
        
        return [types.TextContent(type="text", text=result_msg)]
    
    elif name == "fckgit_push":
        success, message = await push_to_remote(workspace)
        return [types.TextContent(type="text", text=message)]
    
    elif name == "fckgit_cleanup_lock":
        cleaned = cleanup_git_lock(workspace)
        if cleaned:
            return [types.TextContent(type="text", text="Cleaned up stale git lock file")]
        return [types.TextContent(type="text", text="No stale git lock file found")]
    
    elif name == "fckgit_blastoff":
        cooldown = arguments.get("cooldown", 30)
        faang_mode = arguments.get("faang_mode", False)
        success, message, pid = await start_watch_mode(workspace, cooldown=cooldown, faang_mode=faang_mode)
        if success:
            result = f"BLASTOFF! {message}\n\n"
            result += "fckgit is now watching for changes and will:\n"
            if faang_mode:
                result += "- Auto-commit with FAANG-tier professional AI messages (SILICON VALLEY MODE)\n"
            else:
                result += "- Auto-commit every change with AI-generated messages\n"
            result += "- Auto-push to remote\n"
            result += f"- {cooldown} second cooldown between commits\n\n"
            result += "Use fckgit_stop_watch to stop it."
        else:
            result = message
        return [types.TextContent(type="text", text=result)]
    
    elif name == "fckgit_stop_watch":
        pid = arguments.get("pid")
        success, message = await stop_watch_mode(workspace, pid=pid)
        return [types.TextContent(type="text", text=message)]
    
    elif name == "fckgit_watch_status":
        is_running, message = await get_watch_status(workspace)
        return [types.TextContent(type="text", text=message)]
    
    elif name == "fckgit_professionalize":
        casual_message = arguments.get("message")
        
        if not casual_message:
            return [types.TextContent(type="text", text="Error: message is required")]
        
        # Transform to professional
        professional_message = professionalize_message(casual_message, workspace)
        
        result = f"CASUAL MESSAGE:\n{casual_message}\n\n"
        result += f"PROFESSIONAL VERSION:\n{professional_message}\n\n"
        result += "Use fckgit_commit_with_message if you want to commit with this professional message."
        
        return [types.TextContent(type="text", text=result)]
    
    else:
        return [types.TextContent(type="text", text=f"Unknown tool: {name}")]


async def main():
    """Run the MCP server using stdin/stdout streams."""
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="fckgit",
                server_version="0.2.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


if __name__ == "__main__":
    asyncio.run(main())
