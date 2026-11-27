"""Prepare a whole-repository diff and commit the same staged tree."""

import os
import re
import shlex
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

if __package__:
    from .fckgit_gemini import check_staged_encodings
else:
    from fckgit_gemini import check_staged_encodings


def _git(args, cwd, env, allow_missing=False):
    result = subprocess.run(
        ["git", *args], cwd=cwd, env=env, stdin=subprocess.DEVNULL,
        capture_output=True, timeout=60,
    )
    if allow_missing and result.returncode == 1:
        return b""
    if result.returncode:
        error = result.stderr or result.stdout
        raise RuntimeError(error.decode("utf-8", "replace").strip() or "Git command failed.")
    return result.stdout


def _head(cwd, env):
    ref = _git(["symbolic-ref", "-q", "HEAD"], cwd, env, allow_missing=True).strip()
    parent = _git(["rev-parse", "--verify", "-q", "HEAD"], cwd, env, allow_missing=True).strip()
    return ref, parent


_RESTORE_CONFIG = 'export GIT_CONFIG_PARAMETERS="$FCKGIT_ORIGINAL_PARAMETERS"\n'

# Git supplies the proposed ref updates on stdin. In the prepared phase both
# the operator's hook and our check need that input, with refs still locked.
_REFERENCE_HOOK = """
if test -n "$FCKGIT_REFERENCE_HOOK"; then
    if test "$1" != prepared; then
        exec "$FCKGIT_REFERENCE_HOOK" "$@"
    fi
    input="$FCKGIT_COMMIT_RECORD.stdin.$$"
    cat > "$input" || exit 1
    "$FCKGIT_REFERENCE_HOOK" "$@" < "$input" || exit $?
    exec < "$input"
fi
test "$1" = prepared || exit 0
while read -r old new ref
do
    case "$ref" in HEAD|refs/*) ;; *) continue ;; esac
    if { test "$ref" != HEAD && test "$ref" != "$FCKGIT_REF"; } ||
       test "$(git symbolic-ref -q HEAD)" != "$FCKGIT_REF" ||
       test "$(git rev-parse -q --verify HEAD)" != "$FCKGIT_PARENT" ||
       test "$(git rev-parse --verify "$new^{tree}")" != "$FCKGIT_TREE" ||
       test "$(git write-tree)" != "$FCKGIT_TREE"
    then
        echo 'Staged changes or HEAD changed before commit publication. Retry the commit.' >&2
        exit 1
    fi
    echo "$new" > "$FCKGIT_COMMIT_RECORD" || exit 1
done
"""


def _write_hook(path, body):
    path.write_bytes(os.fsencode("#!/bin/sh\n" + _RESTORE_CONFIG + body))
    path.chmod(0o700)


def _guarded_hooks(cwd, env, directory):
    # Redirect only this git commit. Forward native hooks at their original
    # paths so they retain their arguments, stdin, exit codes and sibling files.
    name = _git(["rev-parse", "--git-path", "hooks/pre-commit"], cwd, env).rstrip(b"\r\n")
    original = (Path(cwd) / os.fsdecode(name)).parent.resolve()
    env["FCKGIT_REFERENCE_HOOK"] = ""
    if original.is_dir():
        for hook in original.iterdir():
            if hook.name.endswith(".sample") or not hook.is_file() or not os.access(hook, os.X_OK):
                continue
            if hook.name == "reference-transaction":
                env["FCKGIT_REFERENCE_HOOK"] = hook.as_posix()
            else:
                _write_hook(directory / hook.name, f'exec {shlex.quote(hook.as_posix())} "$@"\n')
    guard = directory / "reference-transaction"
    _write_hook(guard, _REFERENCE_HOOK)
    if not os.access(guard, os.X_OK):
        raise RuntimeError("Git needs an executable reference hook to verify the commit.")


@dataclass(frozen=True)
class StagedChanges:
    ref: bytes
    parent: bytes
    tree: bytes
    diff: str

    @classmethod
    def read(cls, cwd, env=None):
        ref, parent = _head(cwd, env)
        base = parent or _git(["hash-object", "-t", "tree", "--stdin"], cwd, env).strip()
        tree = _git(["write-tree"], cwd, env).strip()
        revisions = [base.decode(), tree.decode()]
        diff = _git(["diff", "--no-relative", "--no-color", *revisions, "--"], cwd, env).decode("utf-8", "replace")
        check_staged_encodings(cwd, env, diff, *revisions)
        return cls(ref, parent, tree, diff)

    def _commit_with_hooks(self, message, cwd, env, directory):
        version = re.match(rb"git version (\d+)\.(\d+)", _git(["--version"], cwd, env))
        if not version or tuple(map(int, version.groups())) < (2, 28):
            raise RuntimeError("Automatic commits require Git 2.28 or newer to verify reference updates.")
        hooks = directory / "hooks"
        hooks.mkdir()
        _guarded_hooks(cwd, env, hooks)
        record = directory / "candidate"
        env.update(
            FCKGIT_REF=os.fsdecode(self.ref), FCKGIT_TREE=self.tree.decode(),
            FCKGIT_PARENT=self.parent.decode(), FCKGIT_COMMIT_RECORD=record.as_posix(),
            FCKGIT_ORIGINAL_PARAMETERS=env.get("GIT_CONFIG_PARAMETERS", ""),
        )
        _git(["-c", f"core.hooksPath={hooks.as_posix()}", "commit", "-m", message], cwd, env)
        return record.read_bytes().strip() if record.exists() else None

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
            if (_head(cwd, locked_env) != (self.ref, self.parent) or
                    _git(["write-tree"], cwd, locked_env).strip() != self.tree):
                raise RuntimeError("Staged changes or HEAD changed during message generation. Retry the commit.")
            with tempfile.TemporaryDirectory(dir=index.parent) as tmp:
                candidate = self._commit_with_hooks(message, cwd, locked_env, Path(tmp))
            os.replace(lock, index)
        except BaseException:
            lock.unlink()
            raise
        if _head(cwd, env) != (self.ref, candidate):
            raise RuntimeError("HEAD changed or the commit could not be verified. Check HEAD before pushing.")
