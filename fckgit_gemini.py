"""Gemini configuration shared by the CLI and MCP tools."""

import os
import stat
import subprocess
from functools import lru_cache
from pathlib import Path


class GeminiConfigurationError(RuntimeError):
    pass


def configured_key(directory=None):
    key = os.environ.get("GEMINI_API_KEY")
    dotenv_disabled = os.getenv("PYTHON_DOTENV_DISABLED", "").lower() in {"1", "true", "t", "yes", "y"}
    if key is not None or dotenv_disabled:
        return key
    try:
        from dotenv import dotenv_values
    except ImportError:
        return None
    return dotenv_values(Path(directory or ".") / ".env").get("GEMINI_API_KEY")


def get_client(directory=None):
    key = configured_key(directory)
    if not key or not key.strip():
        raise GeminiConfigurationError(
            "Set GEMINI_API_KEY in the environment or in an ignored .env in the "
            "working directory (the selected workspace for MCP)."
        )
    return _client_for_key(key)


def check_diff_for_key(diff, directory=None):
    key = configured_key(directory)
    if key and key in diff:
        raise GeminiConfigurationError(
            "The diff contains the configured GEMINI_API_KEY. Exclude the credential "
            "from the diff before generating a message. If the diff only removes the key, "
            "review the removal and commit it with your own message."
        )


def check_files_before_staging(directory=None, env=None):
    """Check only the files Git could stage, including untracked files."""
    directory = directory or Path.cwd()
    key = configured_key(directory)
    if not key:
        return
    status = subprocess.run(
        ["git", "--no-optional-locks", "status", "--porcelain=v1", "-z",
         "--no-renames", "--untracked-files=all"], cwd=directory, env=env, capture_output=True,
    )
    if status.returncode:
        raise RuntimeError("Git could not list pending files before staging.")

    if not status.stdout:
        return
    root = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"], cwd=directory, env=env, capture_output=True,
    )
    if root.returncode:
        raise RuntimeError("Git could not locate the working tree before staging.")
    worktree = Path(os.fsdecode(root.stdout.rstrip(b"\r\n")))
    needle = key.encode("utf-8")
    for entry in status.stdout.rstrip(b"\0").split(b"\0"):
        if entry.startswith(b"D  "):
            # An indexed deletion can leave an ignored local copy after git rm --cached.
            # A replacement eligible for staging has its own untracked entry.
            continue
        name = os.fsdecode(entry[3:])  # Porcelain v1 -z reports root-relative paths.
        try:
            contains_key = _file_contains_key(worktree / name, needle)
        except OSError as exc:
            raise RuntimeError("Could not check a pending file for the configured GEMINI_API_KEY.") from exc
        if contains_key:
            raise GeminiConfigurationError(
                f"{name.replace(key, '[redacted]')} contains the configured GEMINI_API_KEY. "
                "Add the file to .gitignore. If it is already tracked, remove it from "
                "the index with git rm --cached."
            )


def _file_contains_key(path, needle):
    try:
        mode = path.lstat().st_mode
    except FileNotFoundError:
        return False  # A pending deletion has no working-tree content to stage.
    if stat.S_ISLNK(mode):
        return needle in os.fsencode(os.readlink(path))
    if not stat.S_ISREG(mode):
        return False
    with path.open("rb") as stream:
        tail = b""
        for block in iter(lambda: stream.read(65536), b""):
            data = tail + block
            if needle in data:
                return True
            tail = data[-len(needle):]
    return False


@lru_cache(maxsize=1)
def _client_for_key(key):
    try:
        from google import genai
    except ImportError as exc:
        raise GeminiConfigurationError("Install google-genai to generate commit messages.") from exc
    return genai.Client(api_key=key)
