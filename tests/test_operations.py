"""Offline acceptance tests using real repositories and the Git index."""

import ast
import asyncio
import subprocess
import sys
import time
from contextlib import contextmanager
from importlib import import_module
from pathlib import Path
from types import SimpleNamespace

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
            assert cwd == git_repo or cwd == tmp_path or tmp_path in cwd.parents
            if command[1] in ("push", "pull", "fetch"):
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
    else:
        cli.GitChangeHandler().on_created(FileCreatedEvent(str(path)))


@pytest.mark.parametrize("mode", ["once", "event"])
def test_cli_commits_new_file(mode, git_repo, prompts, monkeypatch):
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


def test_key_free_cli(git_repo, monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY")
    (git_repo / "new.txt").write_text("untracked")
    head = git(git_repo, "rev-parse", "HEAD")
    command = [sys.executable, "-m", "fckgit"]
    result = subprocess.run(command + ["--help"], capture_output=True, encoding="utf-8")
    assert result.returncode == 0 and "--once" in result.stdout
    result = subprocess.run(command + ["--once"], capture_output=True, encoding="utf-8")
    assert result.returncode != 0 and "GEMINI_API_KEY" in result.stdout + result.stderr
    assert git(git_repo, "rev-parse", "HEAD") == head
    assert git(git_repo, "status", "--porcelain") == "?? new.txt"


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
async def test_switch_client_roots_in_one_session(git_repo, tmp_path, prompts):
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
        assert "only-a.txt" in (await client.call_tool("fckgit_status", {})).content[0].text
        roots[:] = [other]
        status = (await client.call_tool("fckgit_status", {})).content[0].text
        assert "only-b.txt" in status and str(other) in status
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
