import subprocess
import os
import sys

try:
    import google.generativeai as genai
except ImportError:
    print("❌ google-generativeai not installed. Run: pip install google-generativeai")
    sys.exit(1)

# Configure Gemini
api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    print("❌ GEMINI_API_KEY environment variable not set.")
    sys.exit(1)

genai.configure(api_key=api_key)
model = genai.GenerativeModel("gemini-1.5-flash")


def get_diff():
    """Get unstaged changes."""
    result = subprocess.run(["git", "diff"], capture_output=True, text=True)
    return result.stdout


def get_staged_diff():
    """Get staged changes."""
    result = subprocess.run(["git", "diff", "--cached"], capture_output=True, text=True)
    return result.stdout


def generate_message(diff: str) -> str:
    """Generate commit message using Gemini."""
    prompt = f"""Generate a concise git commit message following Conventional Commits format.

Rules:
- Start with type: feat, fix, docs, style, refactor, test, chore
- Keep the subject line under 72 characters
- Be specific but concise

Changes:
{diff[:4000]}

Output ONLY the commit message, nothing else."""
    
    response = model.generate_content(prompt)
    return response.text.strip().strip('"').strip("'")


def commit(message: str):
    """Stage all changes and commit."""
    subprocess.run(["git", "add", "-A"])
    result = subprocess.run(["git", "commit", "-m", message], capture_output=True, text=True)
    if result.returncode == 0:
        print(f"✓ Committed: {message}")
    else:
        print(f"❌ Commit failed: {result.stderr}")


def main():
    # Check if we're in a git repo
    result = subprocess.run(["git", "rev-parse", "--git-dir"], capture_output=True)
    if result.returncode != 0:
        print("❌ Not a git repository.")
        sys.exit(1)
    
    # Get diff (prefer staged, fall back to unstaged)
    diff = get_staged_diff() or get_diff()
    
    if not diff.strip():
        print("No changes to commit.")
        return
    
    print("🔍 Analyzing changes...")
    message = generate_message(diff)
    
    if message:
        commit(message)
    else:
        print("❌ Failed to generate commit message.")


if __name__ == "__main__":
    main()
