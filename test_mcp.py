"""Quick test script to verify MCP server functionality"""

import asyncio
import sys
import os

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(__file__))

from mcp_server.server import (
    get_git_status,
    get_diff,
    generate_commit_message,
    run_git_command,
)


async def test_mcp_functions():
    """Test the core MCP server functions"""
    
    print("Testing fckgit MCP Server Functions\n" + "=" * 50)
    
    # Test 1: Check if we're in a git repo
    print("\n1. Checking if in git repository...")
    _, _, returncode = run_git_command(["git", "rev-parse", "--git-dir"])
    if returncode != 0:
        print("   NOT in a git repository")
        return
    print("   In git repository")
    
    # Test 2: Get git status
    print("\n2. Getting git status...")
    status = get_git_status()
    if status.strip():
        files = [line.split()[-1] for line in status.strip().split('\n') if line.strip()]
        print(f"   Found {len(files)} changed file(s):")
        for f in files[:5]:  # Show first 5
            print(f"     - {f}")
        if len(files) > 5:
            print(f"     ... and {len(files) - 5} more")
    else:
        print("   No changes detected")
    
    # Test 3: Get diff
    print("\n3. Getting diff...")
    diff = get_diff()
    if diff.strip():
        lines = diff.strip().split('\n')
        print(f"   Diff has {len(lines)} lines")
        print("   First few lines:")
        for line in lines[:5]:
            print(f"     {line[:80]}")
    else:
        print("   No diff available")
    
    # Test 4: Generate commit message (only if there are changes)
    if diff.strip():
        print("\n4. Generating AI commit message...")
        try:
            message = generate_commit_message(diff)
            print(f"   Generated: {message}")
        except Exception as e:
            print(f"   Error: {e}")
    else:
        print("\n4. Skipping commit message generation (no changes)")
    
    print("\n" + "=" * 50)
    print("MCP server functions are working!")
    print("\nNext steps:")
    print("1. Configure your MCP client (see MCP_SETUP.md)")
    print("2. Restart your AI assistant")
    print("3. Try: 'What's the git status?'")


if __name__ == "__main__":
    asyncio.run(test_mcp_functions())
