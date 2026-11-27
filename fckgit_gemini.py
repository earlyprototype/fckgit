"""Gemini configuration shared by the CLI and MCP tools."""

import codecs
import os
import re
import stat
import subprocess
from functools import lru_cache
from pathlib import Path


class GeminiConfigurationError(RuntimeError):
    pass


def _workspace_key(directory):
    dotenv_disabled = os.getenv("PYTHON_DOTENV_DISABLED", "").lower() in {"1", "true", "t", "yes", "y"}
    if dotenv_disabled:
        return None
    path = Path(directory or ".") / ".env"
    if not path.is_file():
        return None
    try:
        from dotenv import dotenv_values
    except ImportError:
        return None
    with path.open(encoding="utf-8-sig", errors="replace") as stream:
        return dotenv_values(stream=stream).get("GEMINI_API_KEY")


def configured_key(directory=None):
    key = os.environ.get("GEMINI_API_KEY")
    return key if key is not None else _workspace_key(directory)


def _credential_values(directory):
    values = {os.environ.get("GEMINI_API_KEY"), _workspace_key(directory)}
    return {value for value in values if value}


def get_client(directory=None):
    key = configured_key(directory)
    if not key or not key.strip():
        raise GeminiConfigurationError(
            "Set GEMINI_API_KEY in the environment or in an ignored .env in the "
            "working directory (the selected workspace for MCP)."
        )
    return _client_for_key(key)


def check_diff_for_key(diff, directory=None):
    # Check added, removed and context lines, including an index-only credential.
    assignment = any(_has_key_assignment(line[1:]) for line in diff.encode().splitlines()
                     if line[:1] in (b"+", b"-", b" "))
    if assignment or any(key in diff for key in _credential_values(directory)):
        raise GeminiConfigurationError(
            "The diff contains a GEMINI_API_KEY. Exclude the credential "
            "from the diff before generating a message. If the diff only removes the key, "
            "review the removal and commit it with your own message."
        )


_KEY_NAME = b"GEMINI_API_KEY"
_KEY_ASSIGNMENT = re.compile(
    rb"^(?:\xef\xbb\xbf)?[ \t]*(?:export[ \t]+)?(?:GEMINI_API_KEY|'GEMINI_API_KEY')[ \t]*="
    rb"[ \t]*(?!['\"]{2}[ \t]*(?:#|$))[^ \t\r\n#]"
)
_JSON_KEY_ASSIGNMENT = re.compile(rb'"GEMINI_API_KEY"[ \t]*:[ \t]*(?:"[^"]|$)')


def _has_key_assignment(line):
    return _KEY_ASSIGNMENT.match(line) or _JSON_KEY_ASSIGNMENT.search(line)


def _bom_encoding(stream):
    prefix = stream.peek(4)[:4]
    if prefix.startswith((codecs.BOM_UTF32_LE, codecs.BOM_UTF32_BE)):
        return "utf-32"
    if prefix.startswith((codecs.BOM_UTF16_LE, codecs.BOM_UTF16_BE)):
        return "utf-16"
    return None


def _encoded_stream_contains_key(stream, encoding, needles):
    for line in codecs.getreader(encoding)(stream, errors="replace"):
        data = line.rstrip("\r\n").encode("utf-8")
        if _has_key_assignment(data) or any(needle in data for needle in needles):
            return True
    return False


def check_staged_encodings(directory, env, diff, base=None, tree=None):
    """Read changed binary blobs directly when Git omits their contents from the patch."""
    if not diff:
        return
    revisions = [base, tree] if tree else ["--cached"]
    stats = subprocess.run(
        ["git", "diff", "--numstat", "-z", "--no-renames", "--no-relative", "--no-textconv",
         "--no-ext-diff", "--ignore-submodules=all", "--diff-filter=AMT", *revisions, "--"],
        cwd=directory, env=env, capture_output=True, timeout=60,
    )
    if stats.returncode:
        raise RuntimeError("Git could not list staged files to check for credentials.")
    needles = tuple(key.encode("utf-8") for key in _credential_values(directory))
    # A diff driver can force UTF-16 text into the patch with embedded NULs.
    forced_text = "\0" in diff
    for entry in stats.stdout.split(b"\0"):
        if not entry or (not entry.startswith(b"-\t-\t") and not forced_text):
            continue
        path = os.fsdecode(entry.split(b"\t", 2)[2])
        with subprocess.Popen(["git", "cat-file", "blob", f"{tree or ''}:{path}"],
                              cwd=directory, env=env, stdin=subprocess.DEVNULL,
                              stdout=subprocess.PIPE, stderr=subprocess.DEVNULL) as blob:
            with blob.stdout as stream:
                encoding = _bom_encoding(stream)
                if encoding and _encoded_stream_contains_key(stream, encoding, needles):
                    raise GeminiConfigurationError(
                        "A staged file contains a GEMINI_API_KEY. Remove the credential before committing."
                    )
                # Drain other binary formats without retaining the blob in memory.
                while stream.read(65536):
                    pass
            if blob.wait():
                raise RuntimeError("Git could not read a staged file to check for credentials.")


def check_files_before_staging(directory=None, env=None):
    """Check only the files Git could stage, including untracked files."""
    directory = directory or Path.cwd()
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
    needles = tuple(key.encode("utf-8") for key in _credential_values(directory))
    for entry in status.stdout.rstrip(b"\0").split(b"\0"):
        if entry.startswith(b"D  "):
            # An indexed deletion can leave an ignored local copy after git rm --cached.
            # A replacement eligible for staging has its own untracked entry.
            continue
        name = os.fsdecode(entry[3:])  # Porcelain v1 -z reports root-relative paths.
        try:
            contains_key = _file_contains_key(worktree / name, needles)
        except OSError as exc:
            raise RuntimeError("Could not check a pending file for the configured GEMINI_API_KEY.") from exc
        if contains_key:
            raise GeminiConfigurationError(
                "A pending file contains a GEMINI_API_KEY. Add credential files such as .env "
                "to .gitignore. If the file is already tracked, remove it from "
                "the index with git rm --cached."
            )


def _file_contains_key(path, needles):
    try:
        mode = path.lstat().st_mode
    except FileNotFoundError:
        return False  # A pending deletion has no working-tree content to stage.
    if stat.S_ISLNK(mode):
        target = os.fsencode(os.readlink(path))
        return any(needle in target for needle in needles)
    if not stat.S_ISREG(mode):
        return False
    with path.open("rb") as stream:
        encoding = _bom_encoding(stream)
        if encoding:
            if _encoded_stream_contains_key(stream, encoding, needles):
                return True
            stream.seek(0)
        tail = b""
        overlap = max(map(len, (*needles, _KEY_NAME))) - 1
        has_key_name = False
        for block in iter(lambda: stream.read(65536), b""):
            data = tail + block
            if any(needle in data for needle in needles):
                return True
            has_key_name = has_key_name or _KEY_NAME in data
            tail = data[-overlap:]
        if has_key_name:
            stream.seek(0)
            return any(_has_key_assignment(line.rstrip(b"\r\n")) for line in stream)
    return False


@lru_cache(maxsize=1)
def _client_for_key(key):
    try:
        from google import genai
    except ImportError as exc:
        raise GeminiConfigurationError("Install google-genai to generate commit messages.") from exc
    return genai.Client(api_key=key)
