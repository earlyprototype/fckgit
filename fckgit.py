import subprocess
import os
import sys
import argparse
import threading
import time
from datetime import datetime

# Fix Windows console encoding for emojis
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

if __package__:
    from .fckgit_index import StagedChanges
    from .fckgit_gemini import (
        GeminiConfigurationError, check_diff_for_key, check_files_before_staging, get_client,
    )
else:
    from fckgit_index import StagedChanges
    from fckgit_gemini import (
        GeminiConfigurationError, check_diff_for_key, check_files_before_staging, get_client,
    )

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False
    FileSystemEventHandler = object

def stage_all_changes():
    check_files_before_staging()
    result = subprocess.run(["git", "add", "-A"], capture_output=True, text=True, encoding='utf-8', errors='replace')
    if result.returncode:
        raise RuntimeError(f"Failed to stage files: {result.stderr.strip()}")


def prepare_staged_changes():
    """Check Gemini configuration before modifying the index."""
    get_client()
    stage_all_changes()
    staged = StagedChanges.read(os.getcwd())
    check_diff_for_key(staged.diff)
    return staged


def stage_and_get_diff():
    return prepare_staged_changes().diff


def generate_message(diff: str, faang_mode: bool = False) -> str:
    """Generate commit message using Gemini."""
    if faang_mode:
        return generate_silicon_valley_message(diff)
    
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
    
    client = get_client()
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash-lite',
            contents=prompt
        )
        return response.text.strip().strip('"').strip("'")
    except Exception as e:
        print(f"⚠️  AI timeout/error, using fallback message: {e}")
        return "chore: Update files"


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
    
    client = get_client()
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash-lite',
            contents=prompt
        )
        return response.text.strip().strip('"').strip("'")
    except Exception as e:
        print(f"⚠️  AI timeout/error, using fallback message: {e}")
        return f"refactor: Implement strategic codebase improvements\n\nEnhanced system architecture to improve maintainability and operational excellence. This change aligns with industry best practices and positions the codebase for future scalability."


def commit(message: str, stage_all: bool = True, staged=None) -> bool:
    """Stage all changes unless the caller has already prepared the index."""
    if stage_all:
        try:
            stage_all_changes()
        except RuntimeError as exc:
            print(f"❌ {exc}")
            return False
    try:
        if staged is None:
            result = subprocess.run(["git", "commit", "-m", message], capture_output=True, text=True, encoding="utf-8", errors="replace")
            if result.returncode:
                raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "Unknown error")
        else:
            staged.commit(message, os.getcwd())
    except (RuntimeError, OSError, subprocess.TimeoutExpired) as exc:
        if "nothing to commit" not in str(exc).lower():
            print(f"❌ Commit failed: {exc}")
        return False
    hash_result = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True)
    commit_hash = hash_result.stdout.strip() if hash_result.returncode == 0 else "unknown"
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"✓ Committed: {message}")
    print(f"  [{commit_hash}] at {timestamp}")
    return True


def push():
    """Push to remote repository."""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"📤 Pushing to remote... ({timestamp})")
    result = subprocess.run(["git", "push"], capture_output=True, text=True, encoding='utf-8', errors='replace')
    
    if result.returncode == 0:
        print("✓ Pushed to remote!")
        return True
    else:
        # Check if it's a rejected push (need to pull first)
        error_msg = result.stderr.strip() or result.stdout.strip() or "Unknown error"
        
        if "rejected" in error_msg.lower() or "fetch first" in error_msg.lower():
            print("🔄 Remote has new commits, pulling...")
            pull_result = subprocess.run(["git", "pull", "--rebase"], capture_output=True, text=True, encoding='utf-8', errors='replace')
            
            if pull_result.returncode == 0:
                print("✓ Pulled and rebased")
                # Try pushing again
                retry_result = subprocess.run(["git", "push"], capture_output=True, text=True, encoding='utf-8', errors='replace')
                if retry_result.returncode == 0:
                    print("✓ Pushed to remote!")
                    return True
                else:
                    print(f"❌ Push failed after pull: {retry_result.stderr.strip()}")
                    return False
            else:
                print(f"❌ Pull failed: {pull_result.stderr.strip()}")
                return False
        else:
            print(f"❌ Push failed: {error_msg}")
            return False


def watch_status():
    return subprocess.run(
        ["git", "--no-optional-locks", "status", "--porcelain", "--untracked-files=normal"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    ).stdout


class GitChangeHandler(FileSystemEventHandler):
    """Handle file system events and trigger commits."""
    
    def __init__(self, faang_mode: bool = False, cooldown: int = 30):
        self.last_commit_time = float("-inf")
        self.cooldown = cooldown  # seconds between commits
        self.faang_mode = faang_mode
        self._lock = threading.Lock()
        self._timer = None
        self._stopped = False
        
    def should_process(self, event):
        """Check if we should process this event."""
        # Ignore directories
        if event.is_directory:
            return False
        
        # Ignore .git folder changes
        path = os.fsdecode(getattr(event, "dest_path", None) or event.src_path)
        if ".git" in path.replace("\\", "/").split("/"):
            return False
        
        return True
    
    def _on_change(self, event):
        if self.should_process(event):
            self.check_for_changes()

    on_created = on_modified = on_deleted = on_moved = _on_change

    def check_for_changes(self):
        with self._lock:
            if self._stopped or self._timer is not None:
                return
            delay = self.last_commit_time + self.cooldown - time.monotonic()
            if delay > 0:
                self._timer = threading.Timer(delay, self._process_pending)
                self._timer.daemon = True
                self._timer.start()
            else:
                self.process_changes()

    def _process_pending(self):
        with self._lock:
            self._timer = None
            if not self._stopped:
                self.process_changes()

    def stop(self):
        with self._lock:
            self._stopped = True
            if self._timer is not None:
                self._timer.cancel()
                self._timer = None
    
    def process_changes(self):
        """Process git changes."""
        # Small delay to ensure file writes are complete
        time.sleep(0.5)
        
        # Check if there are actually any changes in git
        status = watch_status()
        if not status.strip():
            # No changes in git, silently skip (likely temp files or already committed)
            return
        self.last_commit_time = time.monotonic()
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        changed_files = [line[3:] for line in status.splitlines()]
        
        print("\n" + "="*50)
        print(f"🔍 Changes detected at {timestamp}")
        print(f"   Files: {', '.join(changed_files[:3])}{' ...' if len(changed_files) > 3 else ''}")
        if self.faang_mode:
            print("   Analyzing with AI... (SILICON VALLEY MODE)")
        else:
            print("   Analyzing with AI...")
        
        try:
            staged = prepare_staged_changes()
            if not staged.diff.strip():
                return
            message = generate_message(staged.diff, faang_mode=self.faang_mode)
            
            if message:
                if commit(message, stage_all=False, staged=staged):
                    push()
                else:
                    # Commit failed - check if it's because nothing to commit
                    if not watch_status().strip():
                        print("ℹ️  (Changes were already committed)")
            else:
                print("❌ Failed to generate commit message.")
        except Exception as e:
            print(f"❌ Error: {e}")
        
        print("="*50 + "\n")


def watch_mode(faang_mode: bool = False, cooldown: int = 30):
    """Start watching for file changes."""
    if not WATCHDOG_AVAILABLE:
        print("❌ watchdog not installed. Run: pip install watchdog")
        sys.exit(1)
    
    # Get current branch
    branch_result = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], capture_output=True, text=True)
    branch = branch_result.stdout.strip() if branch_result.returncode == 0 else "unknown"
    
    # Get repo name
    repo_path = os.getcwd()
    repo_name = os.path.basename(repo_path)
    
    start_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    print("="*50)
    if faang_mode:
        print("👀 fckgit - Auto-commit watcher started (SILICON VALLEY MODE)")
    else:
        print("👀 fckgit - Auto-commit watcher started")
    print(f"   Repository: {repo_name}")
    print(f"   Branch: {branch}")
    if faang_mode:
        print("   Mode: FAANG Professional")
    print(f"   Cooldown: {cooldown} seconds")
    print(f"   Started: {start_time}")
    print(f"   Press Ctrl+C to stop")
    print("="*50)
    print()
    
    event_handler = GitChangeHandler(faang_mode=faang_mode, cooldown=cooldown)
    observer = Observer()
    observer.schedule(event_handler, ".", recursive=True)
    observer.start()
    
    try:
        event_handler.check_for_changes()
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\n✓ Stopped watching.")
    finally:
        observer.stop()
        event_handler.stop()
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
    parser.add_argument(
        "--faang",
        action="store_true",
        help="Silicon Valley mode - Generate FAANG-tier professional commit messages"
    )
    parser.add_argument(
        "--cooldown",
        type=int,
        default=30,
        help="Cooldown time in seconds between commits (default: 30)"
    )
    args = parser.parse_args()
    
    # Check if we're in a git repo
    result = subprocess.run(["git", "rev-parse", "--git-dir"], capture_output=True)
    if result.returncode != 0:
        print("❌ Not a git repository.")
        sys.exit(1)
    
    # Single commit mode
    if args.once:
        try:
            staged = prepare_staged_changes()
        except (RuntimeError, OSError, subprocess.TimeoutExpired) as e:
            print(f"❌ {e}")
            sys.exit(1)
        
        if not staged.diff.strip():
            print("No changes to commit.")
            return
        
        if args.faang:
            print("🔍 Analyzing changes... (SILICON VALLEY MODE)")
        else:
            print("🔍 Analyzing changes...")
        
        message = generate_message(staged.diff, faang_mode=args.faang)
        
        if message:
            if not commit(message, stage_all=False, staged=staged):
                sys.exit(1)
            push()
        else:
            print("❌ Failed to generate commit message.")
        return
    
    # Default: Watch mode
    try:
        get_client()
    except GeminiConfigurationError as e:
        print(f"❌ {e}")
        sys.exit(1)
    watch_mode(faang_mode=args.faang, cooldown=args.cooldown)


if __name__ == "__main__":
    main()
