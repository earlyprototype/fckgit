"""Enter a pinned POSIX Git target, then replace this process with the command."""

import os
import sys


def main():
    mode, git_dir, worktree, *command = sys.argv[1:]
    for key, path in (("GIT_DIR", git_dir), ("GIT_WORK_TREE", worktree)):
        if not path:
            continue
        anchor = os.environ[key]
        if not os.path.samefile(path, anchor):
            sys.exit(f"Directory replaced during git operation: {path}")
    for key in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE"):
        value = os.environ.get(key, "")
        if value.startswith("/proc/self/fd/"):
            # Helpers can address the owner's directories even if they close their fds.
            os.environ[key] = value.replace("/proc/self/", f"/proc/{os.getpid()}/", 1)
    if mode == "watch":
        # The server reads startup errors until exec closes this duplicate.
        # The long-running watcher writes stderr to the null device.
        error_fd = os.dup(2)
        with open(os.devnull, "wb") as sink:
            os.dup2(sink.fileno(), 2)
    try:
        os.execvp(command[0], command)
    except OSError:
        if mode == "watch":
            os.dup2(error_fd, 2)
        raise


if __name__ == "__main__":
    main()
