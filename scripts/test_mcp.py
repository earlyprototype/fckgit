"""Quick test script to verify MCP server functionality"""

import subprocess
import sys
import os

print("Testing fckgit MCP Server Setup")
print("=" * 50)

# Test 1: Check Python imports
print("\n1. Checking Python dependencies...")
try:
    import mcp
    print("   mcp: installed")
except ImportError:
    print("   mcp: NOT INSTALLED - run: pip install mcp")
    sys.exit(1)

try:
    from google import genai
    print("   google-genai: installed")
except ImportError:
    print("   google-genai: NOT INSTALLED - run: pip install google-genai")
    sys.exit(1)

try:
    from watchdog.observers import Observer
    print("   watchdog: installed")
except ImportError:
    print("   watchdog: NOT INSTALLED - run: pip install watchdog")

try:
    from dotenv import load_dotenv
    print("   python-dotenv: installed")
except ImportError:
    print("   python-dotenv: NOT INSTALLED (optional)")

# Test 2: Check if mcp_server module loads
print("\n2. Checking mcp_server module...")
try:
    # Add current directory to path
    sys.path.insert(0, os.path.dirname(__file__))
    import mcp_server
    print("   mcp_server module: OK")
except Exception as e:
    print(f"   mcp_server module: ERROR - {e}")
    sys.exit(1)

# Test 3: Check if we're in a git repo
print("\n3. Checking git repository...")
result = subprocess.run(["git", "rev-parse", "--git-dir"], capture_output=True)
if result.returncode == 0:
    print("   In git repository: YES")
    
    # Check status
    status_result = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True)
    if status_result.stdout.strip():
        files = [line.split()[-1] for line in status_result.stdout.strip().split('\n') if line.strip()]
        print(f"   Changed files: {len(files)}")
    else:
        print("   Changed files: 0")
else:
    print("   In git repository: NO")
    print("   (This is OK - MCP server will work in any git repo)")

# Test 4: Check API key
print("\n4. Checking GEMINI_API_KEY...")
api_key = os.environ.get("GEMINI_API_KEY")
if api_key:
    print(f"   API key: SET (length: {len(api_key)})")
else:
    print("   API key: NOT SET")
    print("   Set it in your MCP config or as environment variable")

print("\n" + "=" * 50)
print("Setup check complete!")
print("\nNext steps:")
print("1. Get your Gemini API key: https://makersuite.google.com/app/apikey")
print("2. Read MCP_SETUP.md for configuration")
print("3. Configure your AI assistant")
print("4. Restart your AI assistant")
print("5. Try: 'What's the git status?'")
print("\nConfiguration example: see mcp_config_example.json")
