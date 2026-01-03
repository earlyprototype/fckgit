import asyncio
import os
import subprocess
import sys
from typing import Any

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

from mcp.server.models import InitializationOptions
import mcp.types as types
from mcp.server import NotificationOptions, Server
import mcp.server.stdio


# Configure Gemini
api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    print("GEMINI_API_KEY environment variable not set.")
    sys.exit(1)

client = genai.Client(api_key=api_key)

# Create MCP server
server = Server("fckgit")


def run_git_command(cmd: list[str]) -> tuple[str, str, int]:
    """Run a git command and return stdout, stderr, returncode."""
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding='utf-8',
        errors='replace'
    )
    return result.stdout, result.stderr, result.returncode


def get_diff() -> str:
    """Get unstaged changes."""
    stdout, _, returncode = run_git_command(["git", "diff"])
    return stdout if returncode == 0 else ""


def get_staged_diff() -> str:
    """Get staged changes."""
    stdout, _, returncode = run_git_command(["git", "diff", "--cached"])
    return stdout if returncode == 0 else ""


def get_git_status() -> str:
    """Get git status."""
    stdout, _, returncode = run_git_command(["git", "status", "--porcelain"])
    return stdout if returncode == 0 else ""


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


def cleanup_git_lock():
    """Remove stale git lock file if it exists."""
    lock_file = ".git/index.lock"
    if os.path.exists(lock_file):
        try:
            os.remove(lock_file)
            return True
        except Exception:
            return False
    return False


def commit_changes(message: str, stage_all: bool = True) -> tuple[bool, str]:
    """Stage all changes and commit."""
    cleanup_git_lock()
    
    if stage_all:
        _, _, returncode = run_git_command(["git", "add", "-A"])
        if returncode != 0:
            return False, "Failed to stage files"
    
    stdout, stderr, returncode = run_git_command(["git", "commit", "-m", message])
    
    if returncode == 0:
        # Get the commit hash
        hash_stdout, _, hash_returncode = run_git_command(["git", "rev-parse", "--short", "HEAD"])
        commit_hash = hash_stdout.strip() if hash_returncode == 0 else "unknown"
        return True, f"Committed successfully [{commit_hash}]: {message}"
    else:
        error_msg = stderr.strip() or stdout.strip() or "Unknown error"
        if "nothing to commit" in error_msg.lower():
            return False, "Nothing to commit"
        return False, f"Commit failed: {error_msg}"


def push_to_remote() -> tuple[bool, str]:
    """Push to remote repository."""
    stdout, stderr, returncode = run_git_command(["git", "push"])
    
    if returncode == 0:
        return True, "Successfully pushed to remote"
    
    error_msg = stderr.strip() or stdout.strip() or "Unknown error"
    
    # Try to handle rejected push
    if "rejected" in error_msg.lower() or "fetch first" in error_msg.lower():
        # Try to pull with rebase
        _, _, pull_returncode = run_git_command(["git", "pull", "--rebase"])
        
        if pull_returncode == 0:
            # Try pushing again
            _, _, retry_returncode = run_git_command(["git", "push"])
            if retry_returncode == 0:
                return True, "Pulled, rebased, and pushed successfully"
            return False, "Failed to push after rebase"
        return False, "Failed to pull for rebase"
    
    return False, f"Push failed: {error_msg}"


@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """List available tools."""
    return [
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
        )
    ]


@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict[str, Any] | None
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """Handle tool execution requests."""
    
    if arguments is None:
        arguments = {}
    
    # Check if in git repo
    _, _, returncode = run_git_command(["git", "rev-parse", "--git-dir"])
    if returncode != 0:
        return [types.TextContent(
            type="text",
            text="Error: Not a git repository"
        )]
    
    if name == "fckgit_status":
        include_diff = arguments.get("include_diff", False)
        
        status = get_git_status()
        if not status.strip():
            result = "No changes detected"
        else:
            files = [line.split()[-1] for line in status.strip().split('\n') if line.strip()]
            result = f"Changed files ({len(files)}):\n" + "\n".join(f"  - {f}" for f in files)
            
            if include_diff:
                diff = get_staged_diff() or get_diff()
                if diff:
                    result += f"\n\nDiff:\n{diff}"
        
        return [types.TextContent(type="text", text=result)]
    
    elif name == "fckgit_generate_message":
        use_staged = arguments.get("use_staged", False)
        
        if use_staged:
            diff = get_staged_diff()
        else:
            diff = get_staged_diff() or get_diff()
        
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
            run_git_command(["git", "add", "-A"])
        
        diff = get_staged_diff() or get_diff()
        
        if not diff.strip():
            return [types.TextContent(type="text", text="No changes to commit")]
        
        # Generate message
        message = generate_commit_message(diff)
        
        # Commit
        success, result_msg = commit_changes(message, stage_all=False)  # Already staged
        
        if not success:
            return [types.TextContent(type="text", text=result_msg)]
        
        # Push if requested
        if push:
            push_success, push_msg = push_to_remote()
            result_msg += f"\n{push_msg}"
        
        return [types.TextContent(type="text", text=result_msg)]
    
    elif name == "fckgit_commit_with_message":
        message = arguments.get("message")
        push = arguments.get("push", False)
        stage_all = arguments.get("stage_all", True)
        
        if not message:
            return [types.TextContent(type="text", text="Error: message is required")]
        
        # Commit
        success, result_msg = commit_changes(message, stage_all=stage_all)
        
        if not success:
            return [types.TextContent(type="text", text=result_msg)]
        
        # Push if requested
        if push:
            push_success, push_msg = push_to_remote()
            result_msg += f"\n{push_msg}"
        
        return [types.TextContent(type="text", text=result_msg)]
    
    elif name == "fckgit_push":
        success, message = push_to_remote()
        return [types.TextContent(type="text", text=message)]
    
    elif name == "fckgit_cleanup_lock":
        cleaned = cleanup_git_lock()
        if cleaned:
            return [types.TextContent(type="text", text="Cleaned up stale git lock file")]
        return [types.TextContent(type="text", text="No stale git lock file found")]
    
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
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


if __name__ == "__main__":
    asyncio.run(main())
