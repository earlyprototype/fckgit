"""Prepare a whole-repository diff and commit the same staged tree."""

import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


def _git(args, cwd, env):
    result = subprocess.run(
        ["git", *args], cwd=cwd, env=env, stdin=subprocess.DEVNULL,
        capture_output=True, timeout=60,
    )
    if result.returncode:
        error = result.stderr or result.stdout
        raise RuntimeError(error.decode("utf-8", "replace").strip() or "Git command failed.")
    return result.stdout


def _base_tree(cwd, env):
    # An unborn branch has no HEAD. Ask Git for its native empty-tree hash.
    head = subprocess.run(["git", "rev-parse", "--verify", "--quiet", "HEAD^{tree}"],
                          cwd=cwd, env=env, capture_output=True)
    if head.returncode == 1:
        return _git(["hash-object", "-t", "tree", "--stdin"], cwd, env).strip()
    if head.returncode:
        raise RuntimeError("Git could not read the current HEAD.")
    return head.stdout.strip()


@dataclass(frozen=True)
class StagedChanges:
    base: bytes
    tree: bytes
    diff: str

    @classmethod
    def read(cls, cwd, env=None):
        base = _base_tree(cwd, env)
        tree = _git(["write-tree"], cwd, env).strip()
        diff = _git(["diff", "--no-relative", "--no-color", base.decode(), tree.decode(), "--"], cwd, env)
        return cls(base, tree, diff.decode("utf-8", "replace"))

    def commit(self, message, cwd, env=None):
        index_name = _git(["rev-parse", "--git-path", "index"], cwd, env).rstrip(b"\r\n")
        index = Path(cwd) / os.fsdecode(index_name)
        lock = index.with_name(index.name + ".lock")
        try:
            owned_lock = lock.open("xb")
        except FileExistsError as exc:
            raise RuntimeError(f"Git index is locked: {lock.name}") from exc

        # Keep the real index locked from the comparison through publication.
        # Git can refresh the copy and run normal commit hooks against it.
        try:
            with owned_lock, index.open("rb") as source:
                shutil.copyfileobj(source, owned_lock)
            locked_env = dict(os.environ if env is None else env, GIT_INDEX_FILE=str(lock))
            if (_base_tree(cwd, locked_env) != self.base or
                    _git(["write-tree"], cwd, locked_env).strip() != self.tree):
                raise RuntimeError("Staged changes or HEAD changed during message generation. Retry the commit.")
            _git(["commit", "-m", message], cwd, locked_env)
            os.replace(lock, index)
        except BaseException:
            lock.unlink()
            raise
