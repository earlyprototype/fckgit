"""Offline acceptance tests using real repositories and the Git index."""

import ast
import asyncio
import json
import shutil
import subprocess
import sys
import sysconfig
import time
from contextlib import ExitStack, contextmanager
from importlib import import_module
from pathlib import Path
from threading import Event
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
import fckgit
from google.genai.models import Models
from mcp import ClientSession, StdioServerParameters, types
from mcp.client.stdio import stdio_client
from mcp.shared.memory import create_connected_server_and_client_session


# The console entry point can come from the source package or the installed module.
cli = import_module("fckgit.fckgit") if hasattr(fckgit, "__path__") else fckgit


def git(repo, *args):
    return subprocess.run(["git", *args], cwd=repo, capture_output=True,
                          text=True, check=True).stdout.strip()


@pytest.fixture(autouse=True)
def isolated_repo(git_repo, tmp_path, monkeypatch):
    monkeypatch.chdir(git_repo)
    monkeypatch.delenv("WORKSPACE_FOLDER_PATHS", raising=False)
    monkeypatch.delenv("PROJECT_ROOT", raising=False)
    monkeypatch.setenv("PYTHON_DOTENV_DISABLED", "1")
    monkeypatch.setenv("GEMINI_API_KEY", "offline-test")
    run = subprocess.run

    def local_run(command, **kwargs):
        if command[0] == "git":
            cwd = Path(kwargs.get("cwd", Path.cwd())).resolve()
            assert any(cwd == root or root in cwd.parents for root in (git_repo, tmp_path))
            if command[1] in ("push", "pull", "fetch"):
                remote = run(["git", "remote", "get-url", "--push", "origin"],
                             cwd=cwd, capture_output=True, text=True)
                if command[1] != "push" or remote.stdout.strip() != str(tmp_path / "local.git"):
                    pytest.fail(f"Unexpected git {command[1]} in an offline test")
        return run(command, **kwargs)

    monkeypatch.setattr(subprocess, "run", local_run)


@pytest.fixture
def prompts(monkeypatch):
    inputs = []

    def generate(self, *, model, contents):
        inputs.append(contents)
        return SimpleNamespace(text="feat: Include new file")

    monkeypatch.setattr(Models, "generate_content", generate)
    return inputs


def run_cli(mode, monkeypatch, path):
    from watchdog.events import FileCreatedEvent

    if mode == "once":
        monkeypatch.setattr(sys, "argv", ["fckgit", "--once"])
        cli.main()
    elif mode == "event":
        cli.GitChangeHandler().on_created(FileCreatedEvent(str(path)))
    else:
        monkeypatch.setattr(cli, "Observer", Mock)
        monkeypatch.setattr(cli, "time", SimpleNamespace(sleep=Mock(side_effect=KeyboardInterrupt)))
        cli.watch_mode()


@pytest.mark.parametrize("mode", ["once", "event", "startup"])
def test_cli_commits_new_file(mode, git_repo, prompts, monkeypatch):
    git(git_repo, "config", "status.showUntrackedFiles", "no")
    pushed_heads = []
    monkeypatch.setattr(cli, "push", lambda: pushed_heads.append(git(git_repo, "rev-parse", "HEAD")))
    path = git_repo / "new file.txt"
    path.write_text("new payload\n")
    run_cli(mode, monkeypatch, path)
    assert len(prompts) == 1
    assert path.name in prompts[0] and "+new payload" in prompts[0]
    assert git(git_repo, "show", f"HEAD:{path.name}") == "new payload"
    assert git(git_repo, "log", "-1", "--format=%s") == "feat: Include new file"
    assert pushed_heads == [git(git_repo, "rev-parse", "HEAD")]


def test_watch_commits_file_saved_by_rename(git_repo, prompts, monkeypatch):
    from watchdog.events import FileCreatedEvent, FileMovedEvent

    (git_repo / ".git" / "info" / "exclude").write_text("*.draft\n")
    handler = cli.GitChangeHandler()
    push = Mock()
    monkeypatch.setattr(cli, "push", push)
    draft = git_repo / "article.draft"
    article = git_repo / "article.txt"
    draft.write_text("saved by rename\n")
    handler.dispatch(FileCreatedEvent(str(draft)))
    draft.rename(article)
    handler.dispatch(FileMovedEvent(str(draft), str(article)))
    assert len(prompts) == 1 and "+saved by rename" in prompts[0]
    assert git(git_repo, "show", "HEAD:article.txt") == "saved by rename"
    push.assert_called_once()


def test_watch_processes_last_save_during_cooldown(git_repo, prompts, monkeypatch):
    pushed = Event()
    monkeypatch.setattr(cli, "push", pushed.set)
    observer = cli.Observer()
    handler = cli.GitChangeHandler(cooldown=3)
    observer.schedule(handler, str(git_repo), recursive=True)
    observer.start()
    try:
        (git_repo / "first.txt").write_text("first save\n")
        assert pushed.wait(10)
        pushed.clear()
        (git_repo / "last.txt").write_text("last save\n")
        assert pushed.wait(10)
    finally:
        observer.stop()
        handler.stop()
        observer.join()
    assert len(prompts) == 2
    assert "+first save" in prompts[0] and "+last save" in prompts[1]
    assert git(git_repo, "show", "HEAD:last.txt") == "last save"
    assert git(git_repo, "status", "--porcelain") == ""


@pytest.mark.parametrize("operation", ["once", "fckgit_commit"])
def test_commit_from_subdirectory_includes_root_file(operation, git_repo, prompts, monkeypatch):
    git(git_repo, "config", "diff.relative", "true")
    child = git_repo / "src"
    child.mkdir()
    monkeypatch.chdir(child)
    path = git_repo / "root.txt"
    path.write_text("root payload\n")
    if operation == "once":
        monkeypatch.setattr(cli, "push", lambda: True)
        run_cli(operation, monkeypatch, path)
    else:
        assert "Committed" in call_tool(operation, workspace_path=str(child))
    assert len(prompts) == 1 and "+root payload" in prompts[0]
    assert git(git_repo, "show", "HEAD:root.txt") == "root payload"


@pytest.mark.parametrize("operation", ["once", "fckgit_commit", "fckgit_silicon_valley"])
def test_concurrent_staging_stops_commit(operation, git_repo, monkeypatch, capsys):
    from mcp_server import server

    head = git(git_repo, "rev-parse", "HEAD")
    path = git_repo / "first.txt"
    path.write_text("in the prompt\n")
    inputs = []

    def stage_second(self, *, model, contents):
        inputs.append(contents)
        (git_repo / "second.txt").write_text("staged during generation\n")
        git(git_repo, "add", "second.txt")
        return SimpleNamespace(text="feat: Add first file")

    monkeypatch.setattr(Models, "generate_content", stage_second)
    if operation == "once":
        push = Mock()
        monkeypatch.setattr(cli, "push", push)
        with pytest.raises(SystemExit):
            run_cli(operation, monkeypatch, path)
        result = capsys.readouterr().out
    else:
        push = AsyncMock(return_value=(True, "pushed"))
        monkeypatch.setattr(server, "push_to_remote", push)
        result = call_tool(operation, push=True)
    assert "staged" in result.lower() and "changed" in result.lower()
    assert len(inputs) == 1 and "+in the prompt" in inputs[0] and "second.txt" not in inputs[0]
    assert git(git_repo, "rev-parse", "HEAD") == head
    assert git(git_repo, "diff", "--cached", "--name-only").splitlines() == ["first.txt", "second.txt"]
    push.assert_not_called()


def test_index_stays_locked_through_git_commit(git_repo, prompts, monkeypatch):
    path = git_repo / "first.txt"
    path.write_text("prepared\n")
    run = subprocess.run
    other_writer = []

    def run_with_contender(command, **kwargs):
        if command[0] == "git" and "commit" in command[1:4]:
            (git_repo / "second.txt").write_text("another writer\n")
            other_writer.append(run(["git", "add", "second.txt"], cwd=git_repo,
                                    capture_output=True))
        return run(command, **kwargs)

    monkeypatch.setattr(subprocess, "run", run_with_contender)
    monkeypatch.setattr(cli, "push", lambda: True)
    run_cli("once", monkeypatch, path)
    assert len(other_writer) == 1 and other_writer[0].returncode != 0
    assert b"index.lock" in other_writer[0].stderr
    assert len(prompts) == 1 and "+prepared" in prompts[0]
    assert git(git_repo, "show", "HEAD:first.txt") == "prepared"
    assert git(git_repo, "status", "--porcelain") == "?? second.txt"
    git(git_repo, "add", "second.txt")  # The contender can retry after publication.


@pytest.mark.parametrize("change", ["sibling", "parent"])
def test_head_changed_during_generation(git_repo, monkeypatch, capsys, change):
    original_ref = git(git_repo, "symbolic-ref", "HEAD")
    original = git(git_repo, "rev-parse", "HEAD")
    git(git_repo, "branch", "sibling")
    expected_head = []
    path = git_repo / "reviewed.txt"
    path.write_text("reviewed\n")

    def change_head(self, *, model, contents):
        if change == "sibling":
            git(git_repo, "switch", "sibling")
        else:
            git(git_repo, "commit", "--only", "--allow-empty", "-m", "Concurrent empty commit")
        expected_head.append(git(git_repo, "rev-parse", "HEAD"))
        return SimpleNamespace(text="feat: Add reviewed file")

    monkeypatch.setattr(Models, "generate_content", change_head)
    push = Mock()
    monkeypatch.setattr(cli, "push", push)
    with pytest.raises(SystemExit):
        run_cli("once", monkeypatch, path)
    assert "changed" in capsys.readouterr().out.lower()
    assert git(git_repo, "rev-parse", "HEAD") == expected_head[0]
    assert git(git_repo, "rev-parse", original_ref) == (original if change == "sibling" else expected_head[0])
    assert git(git_repo, "diff", "--cached", "--name-only") == path.name
    push.assert_not_called()


def install_hook(repo, name, body):
    hooks = repo / ".git" / "custom hooks"
    hooks.mkdir(exist_ok=True)
    git(repo, "config", "core.hooksPath", str(hooks))
    hook = hooks / name
    hook.write_bytes(("#!/bin/sh\n" + body + "\n").encode())
    hook.chmod(0o755)


@pytest.mark.parametrize("hook", ["pre-commit", "commit-msg"])
def test_commit_refuses_tree_changed_by_hook(git_repo, prompts, monkeypatch, capsys, hook):
    original = git(git_repo, "rev-parse", "HEAD")
    install_hook(git_repo, hook, "echo generated > generated.txt && git add generated.txt")
    path = git_repo / "reviewed.txt"
    path.write_text("reviewed\n")
    push = Mock()
    monkeypatch.setattr(cli, "push", push)
    with pytest.raises(SystemExit):
        run_cli("once", monkeypatch, path)
    assert "changed" in capsys.readouterr().out.lower()
    assert len(prompts) == 1 and "+reviewed" in prompts[0] and "generated.txt" not in prompts[0]
    assert git(git_repo, "rev-parse", "HEAD") == original
    assert git(git_repo, "diff", "--cached", "--name-only") == path.name
    assert (git_repo / "generated.txt").read_text().strip() == "generated"
    push.assert_not_called()


def test_commit_honors_message_hook(git_repo, prompts, monkeypatch):
    original = git(git_repo, "rev-parse", "HEAD")
    install_hook(git_repo, "commit-msg", 'echo "message rejected" >&2; exit 1')
    (git_repo / "reviewed.txt").touch()
    result = call_tool("fckgit_commit", push=True)
    assert "message rejected" in result
    assert len(prompts) == 1 and git(git_repo, "rev-parse", "HEAD") == original


def test_reference_hook_can_reject_the_commit(git_repo, prompts):
    original = git(git_repo, "rev-parse", "HEAD")
    install_hook(git_repo, "reference-transaction",
                 'if test "$1" = prepared && read -r old new ref; then\n'
                 '    echo "operator declined $ref" >&2\n    exit 1\nfi')
    (git_repo / "new.txt").touch()
    assert "operator declined" in call_tool("fckgit_commit", push=True)
    assert git(git_repo, "rev-parse", "HEAD") == original
    assert git(git_repo, "diff", "--cached", "--name-only") == "new.txt"


def test_unavailable_reference_hook_stops_before_commit(git_repo, prompts, monkeypatch):
    # Git versions older than 2.28 silently ignore reference-transaction.
    original = git(git_repo, "rev-parse", "HEAD")
    run = subprocess.run

    def older_git(command, **kwargs):
        if command == ["git", "--version"]:
            return subprocess.CompletedProcess(command, 0, b"git version 2.27.0\n", b"")
        return run(command, **kwargs)

    monkeypatch.setattr(subprocess, "run", older_git)
    (git_repo / "new.txt").touch()
    result = call_tool("fckgit_commit")
    assert git(git_repo, "rev-parse", "HEAD") == original
    assert "Git 2.28" in result


@pytest.mark.parametrize("mode", ["once", "event", "startup"])
def test_cli_blocks_pending_credential(mode, git_repo, prompts, monkeypatch, capsys):
    monkeypatch.delenv("GEMINI_API_KEY")
    monkeypatch.delenv("PYTHON_DOTENV_DISABLED")
    push = Mock()
    monkeypatch.setattr(cli, "push", push)
    path = git_repo / ".env"
    path.write_text("GEMINI_API_KEY=offline-test\n")
    head = git(git_repo, "rev-parse", "HEAD")
    index = (git_repo / ".git" / "index").read_bytes()
    if mode == "once":
        with pytest.raises(SystemExit) as error:
            run_cli(mode, monkeypatch, path)
        assert error.value.code != 0
    else:
        run_cli(mode, monkeypatch, path)
    output = capsys.readouterr().out
    assert ".gitignore" in output and ".env" in output and "offline-test" not in output
    assert not prompts
    push.assert_not_called()
    assert git(git_repo, "rev-parse", "HEAD") == head
    assert (git_repo / ".git" / "index").read_bytes() == index


def test_credential_outside_cli_subdirectory(git_repo, prompts, monkeypatch, capsys):
    child = git_repo / "src"
    child.mkdir()
    monkeypatch.chdir(child)
    monkeypatch.setattr(cli, "push", lambda: True)
    path = git_repo / ".env"
    path.write_text("LOG_LEVEL=INFO\n")
    run_cli("once", monkeypatch, path)
    assert git(git_repo, "show", "HEAD:.env") == "LOG_LEVEL=INFO"
    head = git(git_repo, "rev-parse", "HEAD")
    (git_repo / ".gitignore").write_text(".env\n")
    path.write_text("GEMINI_API_KEY=offline-test\n")
    with pytest.raises(SystemExit):
        run_cli("once", monkeypatch, path)
    assert len(prompts) == 1
    assert "git rm --cached" in capsys.readouterr().out
    assert git(git_repo, "rev-parse", "HEAD") == head
    assert git(git_repo, "diff", "--cached") == ""

    git(git_repo, "rm", "--cached", "--", path.name)
    run_cli("once", monkeypatch, path)
    assert git(git_repo, "ls-files", "--", path.name) == ""
    assert git(git_repo, "show", "HEAD:.gitignore") == ".env"
    assert len(prompts) == 2 and "offline-test" not in prompts[-1]


def test_mcp_blocks_pending_credential_in_selected_repo(git_repo, tmp_path, prompts, monkeypatch):
    monkeypatch.chdir(tmp_path)
    path = git_repo / ".env"
    path.write_text("GEMINI_API_KEY=offline-test\n")
    head = git(git_repo, "rev-parse", "HEAD")
    for tool in ("fckgit_commit", "fckgit_silicon_valley", "fckgit_commit_with_message"):
        result = call_tool(tool, workspace_path=str(git_repo), message="docs: Update", push=True)
        assert ".gitignore" in result and "offline-test" not in result
        assert git(git_repo, "rev-parse", "HEAD") == head
        assert git(git_repo, "status", "--porcelain") == "?? .env"
    assert not prompts


@pytest.mark.parametrize("operation", ["once", "fckgit_commit", "fckgit_generate_message"])
def test_workspace_assignment_with_different_client_key(operation, git_repo, prompts, monkeypatch, capsys):
    monkeypatch.delenv("PYTHON_DOTENV_DISABLED")
    path = git_repo / ".env"
    path.write_text("export GEMINI_API_KEY = 'workspace-fixture'\n")
    head = git(git_repo, "rev-parse", "HEAD")
    if operation == "fckgit_generate_message":
        git(git_repo, "add", ".env")
        path.write_text("LOG_LEVEL=INFO\n")  # Only the staged version has the assignment.
    index = (git_repo / ".git" / "index").read_bytes()
    if operation == "once":
        monkeypatch.setattr(cli, "push", Mock())
        with pytest.raises(SystemExit):
            run_cli(operation, monkeypatch, path)
        result = capsys.readouterr().out
    else:
        result = call_tool(operation, use_staged=True)
    assert "GEMINI_API_KEY" in result
    assert "workspace-fixture" not in result and "offline-test" not in result
    assert not prompts
    assert git(git_repo, "rev-parse", "HEAD") == head
    assert (git_repo / ".git" / "index").read_bytes() == index


def test_ignored_workspace_key_copied_to_pending_file(git_repo, prompts, monkeypatch):
    monkeypatch.delenv("PYTHON_DOTENV_DISABLED")
    (git_repo / ".git" / "info" / "exclude").write_text(".env\n")
    (git_repo / ".env").write_text("GEMINI_API_KEY=workspace-fixture\n")
    (git_repo / "notes.txt").write_text("copied value: workspace-fixture\n")
    result = call_tool("fckgit_commit")
    assert "GEMINI_API_KEY" in result and "workspace-fixture" not in result
    assert not prompts
    assert git(git_repo, "status", "--porcelain") == "?? notes.txt"


@pytest.mark.parametrize("staged_only", [False, True])
def test_mcp_json_credential_with_different_client_key(git_repo, prompts, staged_only):
    config = git_repo / ".cursor" / "mcp.json"
    config.parent.mkdir()
    document = {"mcpServers": {"fckgit": {"env": dict(GEMINI_API_KEY="fixture-project-only")}}}
    config.write_text(json.dumps(document, indent=2 if staged_only else None))
    if staged_only:
        git(git_repo, "add", ".cursor/mcp.json")
        config.write_text("{}")
    original = git(git_repo, "rev-parse", "HEAD")
    index = (git_repo / ".git" / "index").read_bytes()
    result = call_tool("fckgit_generate_message" if staged_only else "fckgit_commit", use_staged=True)
    assert "GEMINI_API_KEY" in result and "fixture-project-only" not in result
    assert prompts == []
    assert git(git_repo, "rev-parse", "HEAD") == original
    assert (git_repo / ".git" / "index").read_bytes() == index


def test_staged_diff_with_removed_key_stays_local(git_repo, prompts, monkeypatch, capsys):
    path = git_repo / "README.md"
    path.write_text("GEMINI_API_KEY=offline-test\n")
    git(git_repo, "commit", "-am", "Initial test configuration")
    path.write_text("removed\n")
    git(git_repo, "add", path.name)
    head = git(git_repo, "rev-parse", "HEAD")
    with pytest.raises(SystemExit):
        run_cli("once", monkeypatch, path)
    assert "GEMINI_API_KEY" in capsys.readouterr().out
    for tool in ("fckgit_generate_message", "fckgit_commit"):
        result = call_tool(tool, stage_all=False)
        assert "GEMINI_API_KEY" in result and "offline-test" not in result
    assert not prompts
    assert git(git_repo, "rev-parse", "HEAD") == head


def call_tool(name, **arguments):
    from mcp_server.server import handle_call_tool

    return asyncio.run(handle_call_tool(name, arguments))[0].text


@contextmanager
def held_index_lock(repo):
    """Keep Git waiting for index entries on stdin while it owns index.lock."""
    (repo / "held.txt").write_text("another operation\n")
    lock = repo / ".git" / "index.lock"
    with subprocess.Popen(["git", "update-index", "--add", "--stdin"], cwd=repo,
                          stdin=subprocess.PIPE, stderr=subprocess.PIPE) as holder:
        try:
            deadline = time.monotonic() + 10
            while not lock.exists():
                assert holder.poll() is None and time.monotonic() < deadline
                time.sleep(0.02)
            yield lock
        finally:
            _, stderr = holder.communicate(b"held.txt\n", timeout=10)
        assert holder.returncode == 0, stderr


@pytest.mark.parametrize("operation", ["once", "event", "commit", "fckgit_commit",
                                       "fckgit_silicon_valley", "fckgit_commit_with_message"])
def test_commit_preserves_active_lock(operation, git_repo, prompts, monkeypatch, capsys):
    path = git_repo / "README.md"
    path.write_text("unstaged change\n")
    head = git(git_repo, "rev-parse", "HEAD")
    with held_index_lock(git_repo) as lock:
        if operation == "once":
            with pytest.raises(SystemExit) as error:
                run_cli(operation, monkeypatch, path)
            assert error.value.code == 1
            output = capsys.readouterr().out
        elif operation == "event":
            run_cli(operation, monkeypatch, path)
            output = capsys.readouterr().out
        elif operation == "commit":
            assert not cli.commit("docs: Update")
            output = capsys.readouterr().out
        else:
            output = call_tool(operation, push=True, message="docs: Update")
        assert lock.is_file()
        assert "index.lock" in output
        assert git(git_repo, "rev-parse", "HEAD") == head
        assert not git(git_repo, "diff", "--cached")
    assert git(git_repo, "diff", "--cached", "--name-only") == "held.txt"


def test_once_reports_lock_taken_during_generation(git_repo, monkeypatch, capsys):
    path = git_repo / "new.txt"
    path.write_text("new payload\n")
    head = git(git_repo, "rev-parse", "HEAD")
    with ExitStack() as stack:
        def generate(self, *, model, contents):
            assert "+new payload" in contents
            stack.enter_context(held_index_lock(git_repo))
            return SimpleNamespace(text="feat: Include new file")

        monkeypatch.setattr(Models, "generate_content", generate)
        with pytest.raises(SystemExit) as error:
            run_cli("once", monkeypatch, path)
        assert error.value.code != 0
        assert "index.lock" in capsys.readouterr().out
        assert (git_repo / ".git" / "index.lock").is_file()
        assert git(git_repo, "rev-parse", "HEAD") == head
        assert git(git_repo, "diff", "--cached", "--name-only") == path.name


@pytest.mark.parametrize("entry_point", ["module", "installed"])
def test_key_free_cli(entry_point, git_repo, monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY")
    (git_repo / "new.txt").write_text("untracked")
    head = git(git_repo, "rev-parse", "HEAD")
    command = [sys.executable, "-m", "fckgit"]
    if entry_point == "installed":
        executable = shutil.which("fckgit", path=sysconfig.get_path("scripts"))
        assert executable
        command = [executable]
    result = subprocess.run(command + ["--help"], capture_output=True, encoding="utf-8")
    assert result.returncode == 0 and "--once" in result.stdout
    result = subprocess.run(command + ["--once"], capture_output=True, encoding="utf-8")
    assert result.returncode != 0 and "GEMINI_API_KEY" in result.stdout + result.stderr
    assert ".env" in result.stdout and "working directory" in result.stdout
    assert git(git_repo, "rev-parse", "HEAD") == head
    assert git(git_repo, "status", "--porcelain") == "?? new.txt"

    monkeypatch.delenv("PYTHON_DOTENV_DISABLED")
    (git_repo / ".git" / "info" / "exclude").write_text(".env\nnew.txt\n")
    (git_repo / ".env").write_text("GEMINI_API_KEY=offline-test\n")
    result = subprocess.run(command + ["--once"], capture_output=True, encoding="utf-8")
    assert result.returncode == 0 and "No changes to commit" in result.stdout
    assert git(git_repo, "rev-parse", "HEAD") == head


def test_key_free_mcp(git_repo, prompts, monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY")
    path = git_repo / "README.md"
    path.write_text("already staged")
    git(git_repo, "add", path.name)
    path.write_text("still unstaged")
    (git_repo / "new.txt").touch()
    head = git(git_repo, "rev-parse", "HEAD")
    assert "new.txt" in call_tool("fckgit_status")
    assert Path(ast.literal_eval(call_tool("fckgit_debug"))["git_root"]) == git_repo
    index = (git_repo / ".git" / "index").read_bytes()
    for tool in ("fckgit_generate_message", "fckgit_commit", "fckgit_silicon_valley",
                 "fckgit_professionalize", "fckgit_blastoff"):
        assert "GEMINI_API_KEY" in call_tool(tool, message="update")
        assert (git_repo / ".git" / "index").read_bytes() == index
    assert git(git_repo, "rev-parse", "HEAD") == head
    assert path.read_text() == "still unstaged"
    assert "Committed" in call_tool("fckgit_commit_with_message", message="docs: Manual", stage_all=False)
    assert git(git_repo, "show", "HEAD:README.md") == "already staged"


@pytest.mark.asyncio
async def test_key_free_stdio_startup(git_repo, monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY")
    params = StdioServerParameters(
        command=sys.executable, args=["-m", "mcp_server"], cwd=git_repo,
        env={"PYTHON_DOTENV_DISABLED": "1"},
    )
    async with stdio_client(params) as streams, ClientSession(*streams) as session:
        await session.initialize()
        status = await session.call_tool("fckgit_status", {})
        debug = await session.call_tool("fckgit_debug", {})
        assert str(git_repo) in status.content[0].text
        assert Path(ast.literal_eval(debug.content[0].text)["git_root"]) == git_repo


@pytest.mark.asyncio
async def test_switch_client_roots_in_one_session(git_repo, tmp_path, prompts, monkeypatch):
    from mcp_server.server import server

    other = tmp_path / "repository B"
    other.mkdir()
    git(other, "init")
    git(other, "config", "user.name", "Test")
    git(other, "config", "user.email", "test@example.com")
    (git_repo / "only-a.txt").touch()
    (other / "only-b.txt").write_text("from B\n")
    original = git(git_repo, "rev-parse", "HEAD")
    roots = [git_repo]

    async def list_roots(context):
        return types.ListRootsResult(roots=[types.Root(uri=p.as_uri()) for p in roots])

    async with create_connected_server_and_client_session(server, list_roots_callback=list_roots) as client:
        with monkeypatch.context() as inherited:
            inherited.setenv("GIT_DIR", str(git_repo / ".git"))
            inherited.setenv("GIT_WORK_TREE", str(git_repo))
            inherited.setenv("GIT_INDEX_FILE", str(git_repo / ".git" / "index"))
            assert "only-a.txt" in (await client.call_tool("fckgit_status", {})).content[0].text
            roots[:] = [other]
            status = (await client.call_tool("fckgit_status", {})).content[0].text
            assert "only-b.txt" in status and str(other) in status and "only-a.txt" not in status
            debug = ast.literal_eval((await client.call_tool("fckgit_debug", {})).content[0].text)
            assert Path(debug["git_root"]) == other and Path(debug["git_dir"]) == other / ".git"
            assert "Committed" in (await client.call_tool("fckgit_commit", {})).content[0].text
        assert "only-b.txt" in prompts[0] and "only-a.txt" not in prompts[0]
        assert git(other, "show", "HEAD:only-b.txt") == "from B"
        second_head = git(other, "rev-parse", "HEAD")
        (other / "pending.txt").touch()
        roots.append(git_repo)
        result = await client.call_tool("fckgit_commit", {})
        assert "ambiguous" in result.content[0].text.lower()
        selection = await client.call_tool("fckgit_status", {"workspace_path": str(other)})
        assert "pending.txt" in selection.content[0].text
        assert git(other, "rev-parse", "HEAD") == second_head
    assert git(git_repo, "rev-parse", "HEAD") == original
    assert git(git_repo, "diff", "--cached") == git(other, "diff", "--cached") == ""


def test_bad_target_stops_before_staging(git_repo, tmp_path, prompts, monkeypatch):
    (git_repo / "new.txt").touch()
    monkeypatch.setenv("WORKSPACE_FOLDER_PATHS", f"{git_repo};{tmp_path}")
    result = call_tool("fckgit_commit")
    assert "ambiguous" in result.lower()
    result = call_tool("fckgit_commit", workspace_path=str(tmp_path / "missing"))
    assert "does not exist" in result.lower()
    assert git(git_repo, "status", "--porcelain") == "?? new.txt"


def test_discovery_and_watcher_ignore_repository_overrides(git_repo, tmp_path, monkeypatch):
    from mcp_server import server

    git(tmp_path, "init")
    monkeypatch.setenv("GIT_DIR", str(tmp_path / ".git"))
    monkeypatch.setenv("GIT_WORK_TREE", str(tmp_path))
    debug = ast.literal_eval(call_tool("fckgit_debug"))
    assert Path(debug["workspace_path"]) == git_repo
    assert Path(debug["git_root"]) == git_repo

    popen = subprocess.Popen
    child_roots = []
    child_has_key = []
    watcher_help = []
    (git_repo / "fckgit.py").touch()  # Name collision with the installed module.
    workspace = git_repo / "src"
    workspace.mkdir()
    (workspace / ".env").write_text("GEMINI_API_KEY=offline-test\n")
    (git_repo / ".git" / "info" / "exclude").write_text(".env\n")
    monkeypatch.delenv("GEMINI_API_KEY")
    monkeypatch.delenv("PYTHON_DOTENV_DISABLED")

    def launch(command, **kwargs):
        if command[0] == sys.executable:
            with popen([*command, "--help"], cwd=kwargs["cwd"], env=kwargs["env"],
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE) as probe:
                stdout, stderr = probe.communicate(timeout=15)
                assert probe.returncode == 0, stderr
                watcher_help.append(stdout)
            root = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=kwargs["cwd"],
                                  env=kwargs.get("env"), capture_output=True, text=True, check=True)
            child_roots.append(Path(root.stdout.strip()))
            child_has_key.append((kwargs.get("env") or {}).get("GEMINI_API_KEY") == "offline-test")
            return SimpleNamespace(pid=1234)
        return popen(command, **kwargs)

    monkeypatch.setattr(server, "find_fckgit_processes", lambda: [])
    monkeypatch.setattr(server, "_watch_processes", {})
    monkeypatch.setattr(subprocess, "Popen", launch)
    assert "started" in call_tool("fckgit_blastoff", workspace_path=str(workspace))
    assert child_roots == [git_repo]
    assert child_has_key == [True]
    assert b"--cooldown" in watcher_help[0]


def test_mcp_keeps_git_author_settings_without_worktree_redirect(git_repo, tmp_path, prompts, monkeypatch):
    (git_repo / "target.txt").write_text("selected workspace\n")
    settings = [("user.name", "Environment Author"), ("core.worktree", str(tmp_path)),
                ("user.email", "author@example.invalid")]
    with monkeypatch.context() as inherited:
        inherited.setenv("GIT_CONFIG_COUNT", str(len(settings)))
        for i, (key, value) in enumerate(settings):
            inherited.setenv(f"GIT_CONFIG_KEY_{i}", key)
            inherited.setenv(f"GIT_CONFIG_VALUE_{i}", value)
        assert "Committed" in call_tool("fckgit_commit", workspace_path=str(git_repo))
    assert len(prompts) == 1 and "+selected workspace" in prompts[0]
    assert git(git_repo, "log", "-1", "--format=%an <%ae>") == "Environment Author <author@example.invalid>"
    assert git(git_repo, "show", "HEAD:target.txt") == "selected workspace"


@pytest.mark.parametrize("source", ["numbered", "parameters"])
@pytest.mark.parametrize(("setting", "value", "diagnostic"), [
    ("push.default", "nothing", "push.default"),
    ("protocol.file.allow", "never", "not allowed"),
])
def test_mcp_push_respects_operator_restrictions(git_repo, tmp_path, monkeypatch, source,
                                                 setting, value, diagnostic):
    remote = tmp_path / "local.git"
    git(tmp_path, "init", "--bare", str(remote))
    branch = git(git_repo, "symbolic-ref", "--short", "HEAD")
    git(git_repo, "remote", "add", "origin", str(remote))
    git(git_repo, "config", "protocol.allow", "never")
    git(git_repo, "config", "protocol.file.allow", "always")
    git(git_repo, "push", "-u", "origin", branch)
    original = git(remote, "rev-parse", f"refs/heads/{branch}")
    git(git_repo, "commit", "--allow-empty", "-m", "Local only")
    if source == "numbered":
        monkeypatch.setenv("GIT_CONFIG_COUNT", "1")
        monkeypatch.setenv("GIT_CONFIG_KEY_0", setting)
        monkeypatch.setenv("GIT_CONFIG_VALUE_0", value)
    else:
        monkeypatch.setenv("GIT_CONFIG_PARAMETERS", f"'{setting}'='{value}'")
    result = call_tool("fckgit_push")
    assert git(remote, "rev-parse", f"refs/heads/{branch}") == original
    assert diagnostic in result
