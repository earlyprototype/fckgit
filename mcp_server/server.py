import asyncio
import os
import re
import subprocess
import sys
import sysconfig
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

try:
    from google import genai
except ImportError:
    print("google-genai not installed. Run: pip install google-genai")
    sys.exit(1)

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import psutil
from mcp.server.models import InitializationOptions
import mcp.types as types
from mcp.server import NotificationOptions, Server
import mcp.server.stdio

# Import our new modules
from .workspace import InvalidWorkspaceError, WorkspaceDetector
from .git_utils import (
    GitUtilsError, decode_git_path, detect_git_repo_type, discover_worktree, git_environment, rev_parse,
)
from .platform_utils import get_subprocess_kwargs, check_subprocess_security
from .logging_config import setup_logging, init_logger

# Initialize logging (stderr to not interfere with stdio protocol)
setup_logging(level=os.environ.get('LOG_LEVEL', 'INFO'))
logger = init_logger('mcp_server')

# Configure Gemini
api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    print("GEMINI_API_KEY environment variable not set.")
    sys.exit(1)

client = genai.Client(api_key=api_key)

# Create MCP server
server = Server("fckgit")

# Track running watch processes
_watch_processes: dict[Path, subprocess.Popen] = {}
_WATCH_SCRIPT = Path(__file__).resolve().parent.parent / "fckgit.py"
_CONSOLE_SCRIPT = Path(sysconfig.get_path("scripts")) / ("fckgit.exe" if os.name == "nt" else "fckgit")


@dataclass
class GitCommandResult:
    """Result from a git command execution."""
    stdout: str
    stderr: str
    returncode: int
    duration: float  # seconds
    command: str  # for logging/debugging

    def checked_stdout(self) -> str:
        if self.returncode != 0:
            raise RuntimeError(f"{self.command} failed (exit {self.returncode}): {self.stderr.strip()}")
        return self.stdout


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
        cwd: Repository directory for this call
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
    kwargs['env'] = git_environment()
    
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


async def get_diff(cwd: Path) -> str:
    """Get unstaged changes."""
    result = await run_git_command(["git", "diff"], cwd)
    return result.checked_stdout()


async def get_staged_diff(cwd: Path) -> str:
    """Get staged changes."""
    result = await run_git_command(["git", "diff", "--cached"], cwd)
    return result.checked_stdout()


async def get_git_status(cwd: Path) -> str:
    """Get git status."""
    result = await run_git_command(["git", "status", "--porcelain"], cwd)
    return result.checked_stdout()


def generate_commit_message(diff: str) -> str:
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
    
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash-lite',
            contents=prompt
        )
        return response.text.strip().strip('"').strip("'")
    except Exception as e:
        return f"chore: Update files (AI error: {str(e)})"


def generate_silicon_valley_message(diff: str) -> str:
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
    
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash-lite',
            contents=prompt
        )
        return response.text.strip().strip('"').strip("'")
    except Exception as e:
        return f"refactor: Implement strategic codebase improvements\n\nEnhanced system architecture to improve maintainability and operational excellence. This change aligns with industry best practices and positions the codebase for future scalability."


def professionalize_message(casual_message: str) -> str:
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
    
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash-lite',
            contents=prompt
        )
        return response.text.strip().strip('"').strip("'")
    except Exception as e:
        return f"refactor: {casual_message}\n\nImplemented strategic improvements to enhance system architecture and operational efficiency. This change improves maintainability and positions the codebase for future scalability."


async def cleanup_git_lock(cwd: Path) -> bool:
    """Remove stale git lock file if it exists."""
    result = await asyncio.to_thread(rev_parse, cwd, "--git-path", "index.lock")
    result.check_returncode()
    lock_file = cwd / decode_git_path(result.stdout)
    if lock_file.exists():
        try:
            lock_file.unlink()
            logger.debug("Cleaned up git lock file", lock_file=str(lock_file))
            return True
        except Exception as e:
            logger.warning("Failed to clean up git lock file", lock_file=str(lock_file), error=str(e))
            return False
    return False


async def stage_changes(cwd: Path) -> None:
    result = await run_git_command(["git", "add", "-A"], cwd)
    if result.returncode != 0:
        raise RuntimeError(f"Failed to stage files: {result.stderr.strip()}")


async def commit_changes(cwd: Path, message: str, stage_all: bool = True) -> tuple[bool, str]:
    """Stage all changes and commit."""
    if stage_all:
        await stage_changes(cwd)
    
    result = await run_git_command(["git", "commit", "-m", message], cwd)
    
    if result.returncode == 0:
        # Get the commit hash
        hash_result = await run_git_command(["git", "rev-parse", "--short", "HEAD"], cwd)
        commit_hash = hash_result.stdout.strip() if hash_result.returncode == 0 else "unknown"
        return True, f"Committed successfully [{commit_hash}]: {message}"
    else:
        error_msg = result.stderr.strip() or result.stdout.strip() or "Unknown error"
        if "nothing to commit" in error_msg.lower():
            return False, "Nothing to commit"
        raise RuntimeError(f"Commit failed: {error_msg}")


async def push_to_remote(cwd: Path) -> tuple[bool, str]:
    """Push to remote repository."""
    result = await run_git_command(["git", "push"], cwd)
    
    if result.returncode == 0:
        return True, "Successfully pushed to remote"
    
    error_msg = result.stderr.strip() or result.stdout.strip() or "Unknown error"
    
    # Try to handle rejected push
    if "rejected" in error_msg.lower() or "fetch first" in error_msg.lower():
        # Try to pull with rebase
        pull_result = await run_git_command(["git", "pull", "--rebase"], cwd)
        
        if pull_result.returncode == 0:
            # Try pushing again
            retry_result = await run_git_command(["git", "push"], cwd)
            if retry_result.returncode == 0:
                return True, "Pulled, rebased, and pushed successfully"
            return False, "Failed to push after rebase"
        return False, "Failed to pull for rebase"
    
    return False, f"Push failed: {error_msg}"


def _is_watcher(executable: str, cmdline: list[str], cwd: Path) -> bool:
    if not re.fullmatch(r"pythonw?(?:\d+(?:\.\d+)*)?(?:\.exe)?", Path(executable).name, re.IGNORECASE):
        return False
    args = cmdline[1:]
    while args:
        if re.fullmatch(r"-[BEIu]+", args[0]) or (args[0].startswith("-X") and len(args[0]) > 2):
            args = args[1:]
        elif args[0] == "-X" and len(args) > 1:
            args = args[2:]
        else:
            break
    if args[:2] == ["-m", "fckgit"]:
        args = args[2:]
    elif args and (cwd / args[0]).resolve() in (_WATCH_SCRIPT, _CONSOLE_SCRIPT):
        args = args[1:]
    else:
        return False

    while args:
        option = args.pop(0)
        if option == "--faang":
            continue
        if option == "--cooldown" and args:
            value = args.pop(0)
        elif option.startswith("--cooldown="):
            value = option.partition("=")[2]
        else:
            return False
        if not re.fullmatch(r"[+-]?\d+", value):
            return False
    return True


def find_fckgit_processes() -> list[tuple[psutil.Process, Path]]:
    """Pair each watcher with its Git worktree, keeping the verified process handle."""
    processes = []
    for proc in psutil.process_iter(["exe", "cmdline", "cwd"]):
        try:
            info = proc.info
            if not info["exe"] or not info["cmdline"] or not info["cwd"]:
                continue
            cwd = Path(info["cwd"])
            if _is_watcher(info["exe"], info["cmdline"], cwd):
                root = discover_worktree(cwd)
                if root is not None:
                    processes.append((proc, root))
        except (GitUtilsError, psutil.Error, OSError, RuntimeError, subprocess.SubprocessError):
            continue
    return processes


async def start_watch_mode(repo_path: Path, cooldown: int | float = 30, faang_mode: bool = False) -> tuple[bool, str, Optional[int]]:
    """Start fckgit in watch mode as a background process."""
    # JSON Schema accepts whole-valued floats as integers. argparse needs "2" for 2.0.
    if isinstance(cooldown, float) and cooldown.is_integer():
        cooldown = int(cooldown)
    if type(cooldown) is not int:
        raise ValueError("cooldown must be an integer number of seconds")
    
    for proc, root in find_fckgit_processes():
        if root == repo_path:
            return False, f"fckgit watch already running (PID: {proc.pid})", proc.pid
    
    # Build command with cooldown and faang mode
    # Start the installed CLI by filename. -E excludes the caller's PYTHONPATH.
    cmd = [sys.executable, "-E", str(_WATCH_SCRIPT), "--cooldown", str(cooldown)]
    if faang_mode:
        cmd.append("--faang")
    
    try:
        if sys.platform == 'win32':
            launch_options = {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW}
        else:
            launch_options = {"start_new_session": True}
        process = subprocess.Popen(
            cmd, cwd=repo_path, env=git_environment(),
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            **launch_options,
        )
        
        # Store the process
        _watch_processes[repo_path] = process
        
        return True, f"fckgit watch mode started (PID: {process.pid})", process.pid
    except Exception as e:
        return False, f"Failed to start watch mode: {str(e)}", None


async def stop_watch_mode(repo_path: Path, pid: Optional[int] = None) -> tuple[bool, str]:
    """Stop a running fckgit watch process."""
    
    for proc, root in find_fckgit_processes():
        if root != repo_path or (pid is not None and proc.pid != pid):
            continue
        try:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except psutil.TimeoutExpired:
                proc.kill()
            return True, f"Stopped fckgit watch process (PID: {proc.pid})"
        except psutil.Error as e:
            return False, f"Failed to stop process: {e}"
    
    return False, "No fckgit watch process found for this repository"


async def get_watch_status(repo_path: Path) -> tuple[bool, str]:
    """Check if fckgit watch is running in current repo."""
    for proc, root in find_fckgit_processes():
        if root == repo_path:
            return True, f"fckgit watch is running (PID: {proc.pid})"
    
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
                        "type": "integer",
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
                        "description": "Optional: watch process ID to stop in this repository"
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
        tool.inputSchema["properties"]["repo_path"] = {
            "type": "string",
            "description": "Directory in the Git repository for this call. Omit to use workspace detection.",
        }
    return tools


@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict[str, Any] | None
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """Handle tool execution requests."""
    
    if arguments is None:
        arguments = {}
    
    detector = WorkspaceDetector()
    repo_path = arguments.get("repo_path")
    if "repo_path" in arguments and not isinstance(repo_path, str):
        raise InvalidWorkspaceError("repo_path must be a directory path")
    cwd = await asyncio.to_thread(detector.detect_workspace, override=repo_path)

    # Debug tool doesn't require git repo
    if name == "fckgit_debug":
        debug_info = {
            "workspace_path": str(cwd),
            "detection_method": detector.get_workspace_info()["detection_method"],
        }
        git_info = await asyncio.to_thread(detect_git_repo_type, cwd)
        if git_info:
            debug_info["git_repository"] = True
            debug_info["git_root"] = str(git_info.root)
            debug_info["git_dir"] = str(git_info.git_dir)
            debug_info["is_worktree"] = git_info.is_worktree
            debug_info["is_submodule"] = git_info.is_submodule
            debug_info["is_bare"] = git_info.is_bare
            if git_info.superproject_root:
                debug_info["superproject_root"] = str(git_info.superproject_root)
        else:
            bare = await run_git_command(["git", "rev-parse", "--is-bare-repository"], cwd)
            debug_info["git_repository"] = bare.returncode == 0
            if bare.returncode == 0:
                debug_info["is_bare"] = bare.stdout.strip() == "true"
        
        # Try running git status
        result = await run_git_command(["git", "status", "--porcelain"], cwd)
        debug_info["git_status_returncode"] = result.returncode
        debug_info["git_status_success"] = result.returncode == 0
        if result.returncode == 0:
            debug_info["git_changes_detected"] = len(result.stdout.splitlines())
        
        return [types.TextContent(type="text", text=str(debug_info))]
    
    result = await run_git_command(["git", "rev-parse", "--is-inside-work-tree"], cwd)
    if result.returncode != 0:
        raise InvalidWorkspaceError(f"Cannot open Git repository at {cwd}: {result.stderr.strip()}")
    requires_worktree = name not in ("fckgit_push", "fckgit_cleanup_lock", "fckgit_professionalize")
    if requires_worktree and result.stdout.strip() != "true":
        raise InvalidWorkspaceError(f"{name} requires a Git worktree at {cwd}")
    
    if name == "fckgit_status":
        include_diff = arguments.get("include_diff", False)
        
        status = await get_git_status(cwd)
        if not status.strip():
            result = "No changes detected"
        else:
            files = [line.split()[-1] for line in status.strip().split('\n') if line.strip()]
            result = f"Changed files ({len(files)}):\n" + "\n".join(f"  - {f}" for f in files)
            
            if include_diff:
                staged = await get_staged_diff(cwd)
                unstaged = await get_diff(cwd)
                diff = staged or unstaged
                if diff:
                    result += f"\n\nDiff:\n{diff}"
        
        return [types.TextContent(type="text", text=result)]
    
    elif name == "fckgit_generate_message":
        use_staged = arguments.get("use_staged", False)
        
        if use_staged:
            diff = await get_staged_diff(cwd)
        else:
            staged = await get_staged_diff(cwd)
            unstaged = await get_diff(cwd)
            diff = staged or unstaged
        
        if not diff.strip():
            return [types.TextContent(type="text", text="No changes to generate message for")]
        
        message = generate_commit_message(diff)
        return [types.TextContent(type="text", text=f"Generated message: {message}")]
    
    elif name == "fckgit_commit":
        push = arguments.get("push", False)
        stage_all = arguments.get("stage_all", True)
        
        # Get diff for message generation
        if stage_all:
            # Stage first so we can see untracked files
            await stage_changes(cwd)
        
        staged = await get_staged_diff(cwd)
        unstaged = await get_diff(cwd)
        diff = staged or unstaged
        
        if not diff.strip():
            return [types.TextContent(type="text", text="No changes to commit")]
        
        # Generate message
        message = generate_commit_message(diff)
        
        # Commit
        success, result_msg = await commit_changes(cwd, message, stage_all=False)  # Already staged
        
        if not success:
            return [types.TextContent(type="text", text=result_msg)]
        
        # Push if requested
        if push:
            push_success, push_msg = await push_to_remote(cwd)
            result_msg += f"\n{push_msg}"
        
        return [types.TextContent(type="text", text=result_msg)]
    
    elif name == "fckgit_commit_with_message":
        message = arguments.get("message")
        push = arguments.get("push", False)
        stage_all = arguments.get("stage_all", True)
        
        if not message:
            return [types.TextContent(type="text", text="Error: message is required")]
        
        # Commit
        success, result_msg = await commit_changes(cwd, message, stage_all=stage_all)
        
        if not success:
            return [types.TextContent(type="text", text=result_msg)]
        
        # Push if requested
        if push:
            push_success, push_msg = await push_to_remote(cwd)
            result_msg += f"\n{push_msg}"
        
        return [types.TextContent(type="text", text=result_msg)]
    
    elif name == "fckgit_push":
        success, message = await push_to_remote(cwd)
        return [types.TextContent(type="text", text=message)]
    
    elif name == "fckgit_cleanup_lock":
        cleaned = await cleanup_git_lock(cwd)
        if cleaned:
            return [types.TextContent(type="text", text="Cleaned up stale git lock file")]
        return [types.TextContent(type="text", text="No stale git lock file found")]
    
    elif name == "fckgit_blastoff":
        cooldown = arguments.get("cooldown", 30)
        faang_mode = arguments.get("faang_mode", False)
        success, message, pid = await start_watch_mode(cwd, cooldown=cooldown, faang_mode=faang_mode)
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
        success, message = await stop_watch_mode(cwd, pid=pid)
        return [types.TextContent(type="text", text=message)]
    
    elif name == "fckgit_watch_status":
        is_running, message = await get_watch_status(cwd)
        return [types.TextContent(type="text", text=message)]
    
    elif name == "fckgit_silicon_valley":
        push = arguments.get("push", False)
        stage_all = arguments.get("stage_all", True)
        
        # Get diff for message generation
        if stage_all:
            # Stage first so we can see untracked files
            await stage_changes(cwd)
        
        staged = await get_staged_diff(cwd)
        unstaged = await get_diff(cwd)
        diff = staged or unstaged
        
        if not diff.strip():
            return [types.TextContent(type="text", text="No changes to commit")]
        
        # Generate FAANG-tier professional message
        message = generate_silicon_valley_message(diff)
        
        # Commit
        success, result_msg = await commit_changes(cwd, message, stage_all=False)  # Already staged
        
        if not success:
            return [types.TextContent(type="text", text=result_msg)]
        
        result = "SILICON VALLEY MODE ACTIVATED\n\n" + result_msg
        
        # Push if requested
        if push:
            push_success, push_msg = await push_to_remote(cwd)
            result += f"\n{push_msg}"
        
        return [types.TextContent(type="text", text=result)]
    
    elif name == "fckgit_professionalize":
        casual_message = arguments.get("message")
        
        if not casual_message:
            return [types.TextContent(type="text", text="Error: message is required")]
        
        # Transform to professional
        professional_message = professionalize_message(casual_message)
        
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
