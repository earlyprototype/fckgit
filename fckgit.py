import subprocess
import os
import sys
import argparse
import time
from datetime import datetime

# Fix Windows console encoding for emojis
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

try:
    import google.generativeai as genai
except ImportError:
    print("❌ google-generativeai not installed. Run: pip install google-generativeai")
    sys.exit(1)

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False

# Try to load .env file if python-dotenv is available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv not installed, will use system env vars

# Configure Gemini
api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    print("❌ GEMINI_API_KEY environment variable not set.")
    sys.exit(1)

genai.configure(api_key=api_key)
model = genai.GenerativeModel("gemini-2.5-flash-lite")


def get_diff():
    """Get unstaged changes."""
    result = subprocess.run(["git", "diff"], capture_output=True, text=True, encoding='utf-8', errors='replace')
    return result.stdout if result.returncode == 0 else ""


def get_staged_diff():
    """Get staged changes."""
    result = subprocess.run(["git", "diff", "--cached"], capture_output=True, text=True, encoding='utf-8', errors='replace')
    return result.stdout if result.returncode == 0 else ""


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


def cleanup_git_lock():
    """Remove stale git lock file if it exists."""
    lock_file = ".git/index.lock"
    if os.path.exists(lock_file):
        try:
            os.remove(lock_file)
            print("🔧 Removed stale git lock file")
        except Exception:
            pass  # Ignore if we can't remove it


def commit(message: str) -> bool:
    """Stage all changes and commit."""
    # Clean up any stale locks first
    cleanup_git_lock()
    
    subprocess.run(["git", "add", "-A"], capture_output=True)
    result = subprocess.run(["git", "commit", "-m", message], capture_output=True, text=True, encoding='utf-8', errors='replace')
    if result.returncode == 0:
        # Get the commit hash
        hash_result = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True)
        commit_hash = hash_result.stdout.strip() if hash_result.returncode == 0 else "unknown"
        
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"✓ Committed: {message}")
        print(f"  [{commit_hash}] at {timestamp}")
        return True
    else:
        # Check if the error is just "nothing to commit"
        error_msg = result.stderr.strip() or result.stdout.strip() or "Unknown error"
        if "nothing to commit" in error_msg.lower():
            # This is expected when files were already committed
            return False
        else:
            # This is a real error
            timestamp = datetime.now().strftime("%H:%M:%S")
            print(f"❌ Commit failed at {timestamp}: {error_msg}")
            return False


def push():
    """Push to remote repository."""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"📤 Pushing to remote... ({timestamp})")
    result = subprocess.run(["git", "push"], capture_output=True, text=True, encoding='utf-8', errors='replace')
    if result.returncode == 0:
        print("✓ Pushed to remote!")
        return True
    else:
        error_msg = result.stderr.strip() or result.stdout.strip() or "Unknown error"
        print(f"❌ Push failed: {error_msg}")
        return False


class GitChangeHandler(FileSystemEventHandler):
    """Handle file system events and trigger commits."""
    
    def __init__(self):
        self.last_commit_time = 0
        self.cooldown = 5  # seconds between commits
        
    def should_process(self, event):
        """Check if we should process this event."""
        # Ignore directories
        if event.is_directory:
            return False
        
        # Ignore .git folder changes
        if '/.git/' in event.src_path.replace('\\', '/') or '\\.git\\' in event.src_path:
            return False
        
        # Check cooldown
        current_time = time.time()
        if current_time - self.last_commit_time < self.cooldown:
            return False
        
        return True
    
    def on_modified(self, event):
        """Handle file modification events."""
        if self.should_process(event):
            self.process_changes()
    
    def on_created(self, event):
        """Handle file creation events."""
        if self.should_process(event):
            self.process_changes()
    
    def on_deleted(self, event):
        """Handle file deletion events."""
        if self.should_process(event):
            self.process_changes()
    
    def process_changes(self):
        """Process git changes."""
        self.last_commit_time = time.time()
        
        # Small delay to ensure file writes are complete
        time.sleep(0.5)
        
        # Check if there are actually any changes in git
        status_result = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True, encoding='utf-8', errors='replace')
        if not status_result.stdout.strip():
            # No changes in git, silently skip (likely temp files or already committed)
            return
        
        # Double-check with diff
        diff = get_staged_diff() or get_diff()
        
        if not diff.strip():
            # No actual diff content, skip
            return
        
        print("\n" + "="*50)
        print("🔍 Changes detected! Analyzing...")
        
        try:
            message = generate_message(diff)
            
            if message:
                if commit(message):
                    push()
                else:
                    # Commit failed - check if it's because nothing to commit
                    status_check = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True)
                    if not status_check.stdout.strip():
                        print("ℹ️  (Changes were already committed)")
            else:
                print("❌ Failed to generate commit message.")
        except Exception as e:
            print(f"❌ Error: {e}")
        
        print("="*50 + "\n")


def watch_mode():
    """Start watching for file changes."""
    if not WATCHDOG_AVAILABLE:
        print("❌ watchdog not installed. Run: pip install watchdog")
        sys.exit(1)
    
    print("👀 Watching for changes... (Press Ctrl+C to stop)")
    print("   Will auto-commit and push when files are saved.")
    print()
    
    event_handler = GitChangeHandler()
    observer = Observer()
    observer.schedule(event_handler, ".", recursive=True)
    observer.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\n✓ Stopped watching.")
        observer.stop()
    observer.join()


def main():
    # Parse arguments
    parser = argparse.ArgumentParser(
        description="Auto-commit with AI-generated messages using Gemini (watch mode by default)"
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run once instead of watching for changes"
    )
    args = parser.parse_args()
    
    # Check if we're in a git repo
    result = subprocess.run(["git", "rev-parse", "--git-dir"], capture_output=True)
    if result.returncode != 0:
        print("❌ Not a git repository.")
        sys.exit(1)
    
    # Single commit mode
    if args.once:
        # Get diff (prefer staged, fall back to unstaged)
        diff = get_staged_diff() or get_diff()
        
        if not diff.strip():
            print("No changes to commit.")
            return
        
        print("🔍 Analyzing changes...")
        message = generate_message(diff)
        
        if message:
            if commit(message):
                push()
        else:
            print("❌ Failed to generate commit message.")
        return
    
    # Default: Watch mode
    watch_mode()


if __name__ == "__main__":
    main()
