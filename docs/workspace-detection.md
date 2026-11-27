# How the MCP server selects a repository

Earlier versions selected a workspace when the server started. If an editor
switched from project A to B in the same session, status, staging and commits
could still run in A.

Each tool call now selects its workspace once. Every Git command in that
operation, including a requested push or rebase, uses the selected directory.
The server clears inherited Git repository overrides such as `GIT_DIR`,
`GIT_WORK_TREE` and `GIT_INDEX_FILE` for discovery and Git commands.
A watcher starts in the selected repository with the same overrides cleared.

## Selection order

1. The tool's optional `workspace_path` argument, an absolute directory path.
2. The current root returned by the client's MCP `roots/list` callback, if the
   client advertises roots.
3. The folder in `WORKSPACE_FOLDER_PATHS`.
4. The directory in `PROJECT_ROOT`.
5. The Git root for the server's current working directory. Outside a
   repository, `fckgit_debug` can still report the current directory.

If a client returns zero or several roots, pass `workspace_path` to select
a repository. The same applies to a multi-folder `WORKSPACE_FOLDER_PATHS`.
An unreadable root list or an invalid target stops the request before staging.

## Checking a switch

Call `fckgit_status` before and after switching projects. The response names
the selected workspace. For a client with a fixed working directory and no
roots support, pass the active project's path on each call. The process
environment alone cannot communicate a project switch to a running server.

Use `fckgit_debug` to inspect the selected path, Git root and Git directory.
Both diagnostic tools work before Gemini is configured.
