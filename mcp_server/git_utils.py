"""
Git-specific utilities for handling edge cases.

Provides support for:
- Git worktrees (where .git is a file, not directory)
- Git submodules (nested repositories)
- Bare repositories (no working tree)
- Nested repositories
"""

import os
import shutil
import stat
import subprocess
import sys
import tempfile
from contextlib import ExitStack, contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

if os.name == "nt":
    import _winapi
    import ctypes
    from ctypes import wintypes

    _create_file = ctypes.WinDLL("kernel32", use_last_error=True).CreateFileW
    _create_file.argtypes = (wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, wintypes.LPVOID,
                             wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE)
    _create_file.restype = wintypes.HANDLE


# Clear inherited repository selectors. Git's discovery boundaries still apply.
_REPO_ENV = {
    "GIT_ALTERNATE_OBJECT_DIRECTORIES", "GIT_COMMON_DIR",
    "GIT_CONFIG", "GIT_DIR",
    "GIT_GRAFT_FILE", "GIT_IMPLICIT_WORK_TREE",
    "GIT_INDEX_FILE", "GIT_NAMESPACE", "GIT_NO_REPLACE_OBJECTS", "GIT_OBJECT_DIRECTORY",
    "GIT_PREFIX", "GIT_QUARANTINE_PATH", "GIT_REPLACE_REF_BASE", "GIT_SHALLOW_FILE",
    "GIT_WORK_TREE",
}


def _quote_config_field(value: str) -> str:
    """Single-quote one field for Git's GIT_CONFIG_PARAMETERS encoding."""
    return "'" + value.replace("'", "'\\''") + "'"


def git_environment(*, discovery: bool = False) -> dict[str, str]:
    """Remove inherited repository selectors while preserving other command config."""
    env = {key: value for key, value in os.environ.items() if key not in _REPO_ENV}
    if not env.get("GIT_CONFIG_PARAMETERS") and env.get("GIT_CONFIG_COUNT", "0") == "0":
        return env

    # Let Git decode both command config formats in precedence order. Read
    # only the environment here, without following includes or opening a repo.
    result = subprocess.run(
        ["git", "config", "--null", "--list", "--no-includes"],
        env={**env, "GIT_DIR": os.devnull, "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"},
        capture_output=True, stdin=subprocess.DEVNULL, timeout=5,
    )
    if result.returncode:
        raise ValueError("Invalid inherited Git command configuration")

    kept = []
    for record in result.stdout.split(b"\0")[:-1]:
        entry = os.fsdecode(record)
        key, separator, value = entry.partition("\n")
        if key in ("core.worktree", "core.bare", "extensions.worktreeconfig"):
            continue
        # Includes may also set core.worktree. Restore them in their original
        # position once GIT_DIR and GIT_WORK_TREE control repository selection.
        if discovery and (key == "include.path" or (key.startswith("includeif.") and key.endswith(".path"))):
            continue
        # A missing value is an implicit boolean, distinct from an empty value.
        kept.append(_quote_config_field(key) + "=" + (_quote_config_field(value) if separator else ""))

    env.pop("GIT_CONFIG_COUNT", None)
    for key in list(env):
        if key.startswith(("GIT_CONFIG_KEY_", "GIT_CONFIG_VALUE_")) and key.rpartition("_")[2].isdigit():
            del env[key]
    env["GIT_CONFIG_PARAMETERS"] = " ".join(kept)
    return env


def rev_parse(path: Path, *args: str, env: Optional[dict[str, str]] = None) -> subprocess.CompletedProcess:
    if env is None:
        env = git_environment(discovery=True)
    return subprocess.run(
        ["git", "rev-parse", *args], cwd=path, env=env,
        capture_output=True, timeout=5.0, stdin=subprocess.DEVNULL,
    )


def decode_git_path(output: bytes) -> str:
    """Decode a single rev-parse path, including any whitespace in its name."""
    return os.fsdecode(output.removesuffix(b"\n"))


@dataclass
class GitRepoInfo:
    """Information about a git repository."""
    root: Path
    git_dir: Path
    is_worktree: bool
    is_submodule: bool
    is_bare: bool
    superproject_root: Optional[Path] = None


class GitUtilsError(RuntimeError):
    """Base exception for git utilities errors."""
    pass


def _directory_id(path: Path) -> tuple[int, int]:
    try:
        info = path.stat()
    except OSError as exc:
        raise GitUtilsError(f"Cannot verify directory for git operation: {path}") from exc
    if not stat.S_ISDIR(info.st_mode) or not info.st_ino:
        raise GitUtilsError(f"Cannot identify directory for git operation: {path}")
    return info.st_dev, info.st_ino


def _pin_directory(path: Path, stack: ExitStack) -> tuple[Path, int]:
    if os.name == "nt":
        # FILE_SHARE_READ | FILE_SHARE_WRITE permits normal Git operations.
        # Omitting FILE_SHARE_DELETE prevents a rename until the handle closes.
        file_flag_backup_semantics = 0x02000000  # open a directory
        file_list_directory = 0x0001
        handle = _create_file(str(path), file_list_directory, 3, None, _winapi.OPEN_EXISTING,
                              file_flag_backup_semantics, None)
        if handle == wintypes.HANDLE(-1).value:
            raise ctypes.WinError(ctypes.get_last_error())
        stack.callback(_winapi.CloseHandle, handle)
        return path, handle

    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    stack.callback(os.close, fd)
    if sys.platform == "darwin":
        # macOS exposes open directories by volume and file ID.
        info = os.fstat(fd)
        anchor = Path("/.vol") / str(info.st_dev) / str(info.st_ino)
    else:
        fd_root = "/proc/self/fd" if sys.platform.startswith("linux") else "/dev/fd"
        anchor = Path(fd_root) / str(fd)
    return anchor, fd


@dataclass(frozen=True)
class GitTarget:
    """The absolute Git directory and optional working tree selected together."""
    git_dir: Path
    worktree: Optional[Path]
    _identities: tuple[tuple[Path, tuple[int, int]], ...] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        paths = (self.git_dir,) if self.worktree is None else (self.git_dir, self.worktree)
        object.__setattr__(self, "_identities", tuple((path, _directory_id(path)) for path in paths))

    @property
    def cwd(self) -> Path:
        return self.worktree or self.git_dir

    def verify(self) -> None:
        """Check that each selected path still names the original directory."""
        for path, identity in self._identities:
            if _directory_id(path) != identity:
                raise GitUtilsError(f"Directory replaced during git operation: {path}")

    def environment(self) -> dict[str, str]:
        env = git_environment()
        env["GIT_DIR"] = str(self.git_dir)
        if self.worktree is None:
            env["GIT_IMPLICIT_WORK_TREE"] = "0"
        else:
            env["GIT_WORK_TREE"] = str(self.worktree)
        self.verify()
        return env

    @contextmanager
    def command_context(self, *, watcher: bool = False):
        """Keep both selected directories open through command completion."""
        with ExitStack() as stack:
            env = self.environment()
            anchors = {}
            handles = []
            try:
                for path, identity in self._identities:
                    anchor, handle = _pin_directory(path, stack)
                    if _directory_id(anchor) != identity:
                        raise GitUtilsError(f"Directory replaced during git operation: {path}")
                    anchors[path] = anchor
                    handles.append(handle)
            except OSError as exc:
                raise GitUtilsError(f"Cannot hold directory for git operation: {path}") from exc

            env["GIT_DIR"] = str(anchors[self.git_dir])
            if self.worktree is not None:
                env["GIT_WORK_TREE"] = str(anchors[self.worktree])
            options = {"cwd": anchors[self.cwd], "env": env}
            prefix = []
            if os.name != "nt":
                options["pass_fds"] = tuple(handles)
                prefix = [sys.executable, "-I", "-S", str(Path(__file__).with_name("_exec_target.py")),
                          "watch" if watcher else "run", str(self.git_dir), str(self.worktree or "")]
            elif watcher:
                for handle in handles:
                    os.set_handle_inheritable(handle, True)
                options["startupinfo"] = subprocess.STARTUPINFO(lpAttributeList={"handle_list": handles})
            self.verify()
            yield prefix, options
            self.verify()

    def run(self, cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        with self.command_context() as (prefix, options):
            if os.name != "nt" and cmd == ["git", "add", "-A"]:
                return self._stage([*prefix, *cmd], options, kwargs)
            return subprocess.run([*prefix, *cmd], **options, **kwargs)

    def _stage(self, cmd, options, kwargs) -> subprocess.CompletedProcess:
        # POSIX allows an open checkout to move while Git reads it. Reserve
        # Git's normal lock and publish the staged index only after validation.
        directory = Path(options["env"]["GIT_DIR"])
        index = directory / "index"
        lock = directory / "index.lock"
        with ExitStack() as stack:
            try:
                reservation = lock.open("xb")
            except FileExistsError as exc:
                raise GitUtilsError(f"Git index.lock already exists: {lock}") from exc
            stack.callback(lock.unlink, missing_ok=True)
            stack.enter_context(reservation)
            fd, name = tempfile.mkstemp(dir=directory, prefix="fckgit-index-")
            os.close(fd)
            private = Path(name)
            stack.callback(private.unlink, missing_ok=True)
            stack.callback(Path(name + ".lock").unlink, missing_ok=True)
            if index.exists():
                shutil.copy2(index, private)
            else:
                private.unlink()  # Git initializes a missing index in the repository format.
            env = {**options["env"], "GIT_INDEX_FILE": name}
            result = subprocess.run(cmd, **{**options, "env": env}, **kwargs)
            if result.returncode == 0:
                self.verify()
                if private.exists():
                    private.replace(index)
            return result

    def rev_parse(self, *args: str) -> subprocess.CompletedProcess:
        return self.run(["git", "rev-parse", *args], capture_output=True,
                        timeout=5.0, stdin=subprocess.DEVNULL)


def _read_git_target(path: Path, env: dict[str, str]) -> Optional[GitTarget]:
    result = rev_parse(path, "--absolute-git-dir", env=env)
    if result.returncode:
        return None
    git_dir = Path(decode_git_path(result.stdout)).resolve()
    top = rev_parse(path, "--show-toplevel", env=env)
    worktree = None if top.returncode else Path(decode_git_path(top.stdout)).resolve()
    return GitTarget(git_dir, worktree)


def discover_git_target(path: Path) -> Optional[GitTarget]:
    """Validate the worktree and retain the Git directory selected at the original path."""
    env = git_environment(discovery=True)
    target = _read_git_target(path, env)
    if target and target.worktree and target.worktree != path:
        at_root = rev_parse(target.worktree, "--absolute-git-dir", env={**env, "LC_ALL": "C"})
        if at_root.returncode:
            # An external core.worktree can have no .git entry or enclosing
            # repository. Other discovery errors leave its ownership unknown.
            if not at_root.stderr.startswith(b"fatal: not a git repository (or any "):
                raise GitUtilsError(f"Cannot verify Git directory at {target.worktree}")
            configured = rev_parse(target.git_dir, "--show-toplevel", env={**env, "GIT_DIR": str(target.git_dir)})
            if configured.returncode or Path(decode_git_path(configured.stdout)).resolve() != target.worktree:
                raise GitUtilsError(f"Git directory at {target.git_dir} does not select {target.worktree}")
        elif Path(decode_git_path(at_root.stdout)).resolve() != target.git_dir:
            raise GitUtilsError(f"Worktree at {target.worktree} does not select the Git directory for {path}")
    return target


def discover_worktree(path: Path) -> Optional[Path]:
    """Find a worktree that selects the same Git directory as the starting path."""
    target = discover_git_target(path)
    return target.worktree if target else None


def external_watcher_target(cwd: Path, process_env: dict[str, str]) -> Optional[GitTarget]:
    """Discover a watcher's target only when we can reproduce its Git context."""
    if os.name == "nt":
        process_env = {key.upper(): value for key, value in process_env.items()}
    selectors = {"GIT_DIR", "GIT_WORK_TREE"}
    if (_REPO_ENV - selectors).intersection(process_env):
        # A separate index, common directory, or object store is a different target.
        return None

    # Use the server's Git executable and configuration. If the watcher uses
    # another context, its cwd alone cannot establish which checkout it owns.
    context_keys = {
        "PATH", "HOME", "HOMEDRIVE", "HOMEPATH", "USERPROFILE", "XDG_CONFIG_HOME",
        "GIT_CEILING_DIRECTORIES", "GIT_DISCOVERY_ACROSS_FILESYSTEM", "GIT_EXEC_PATH",
    }

    def context(env):
        return {k: v for k, v in env.items() if k in context_keys or k.startswith("GIT_CONFIG_")}

    env = {key: value for key, value in os.environ.items() if key not in _REPO_ENV}
    watcher_context = context(process_env)
    if watcher_context != context(env):
        # Server-launched watchers receive both selectors and normalized command config.
        if not selectors.issubset(process_env):
            return None
        env = git_environment()
        if watcher_context != context(env):
            return None
    for key in selectors:
        if key in process_env:
            env[key] = process_env[key]
    return _read_git_target(cwd, env)


def detect_git_repo_type(path: Path | GitTarget) -> Optional[GitRepoInfo]:
    """Describe a worktree using the same Git directory for each probe."""
    try:
        target = path if isinstance(path, GitTarget) else discover_git_target(path)
        if not target or not target.worktree:
            return None
        common = target.rev_parse("--path-format=absolute", "--git-common-dir")
        common.check_returncode()
        common_dir = (target.cwd / decode_git_path(common.stdout)).resolve()
        superproject = target.rev_parse("--show-superproject-working-tree")
        superproject.check_returncode()
        parent = decode_git_path(superproject.stdout)
        return GitRepoInfo(
            root=target.worktree,
            git_dir=target.git_dir,
            is_worktree=not common_dir.samefile(target.git_dir),
            is_submodule=bool(parent),
            is_bare=False,
            superproject_root=Path(parent) if parent else None,
        )
    except (OSError, GitUtilsError, subprocess.SubprocessError):
        return None


def check_git_available() -> bool:
    """
    Check if git command is available.
    
    Returns:
        True if git is available, False otherwise
    """
    try:
        result = subprocess.run(
            ['git', '--version'],
            capture_output=True,
            text=True,
            timeout=5.0,
            stdin=subprocess.DEVNULL,
        )
        return result.returncode == 0
    except Exception:
        return False


def get_git_version() -> Optional[str]:
    """
    Get git version string.
    
    Returns:
        Git version string, or None if git not available
    """
    try:
        result = subprocess.run(
            ['git', '--version'],
            capture_output=True,
            text=True,
            timeout=5.0,
            stdin=subprocess.DEVNULL,
        )
        if result.returncode == 0:
            return result.stdout.strip()
        return None
    except Exception:
        return None
