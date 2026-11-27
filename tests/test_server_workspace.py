"""Repository selection through the MCP tool interface."""

import asyncio
import ast
import os
import subprocess
import sys
import time
from contextlib import asynccontextmanager
from pathlib import Path
from unittest.mock import Mock

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from mcp_server.server import handle_call_tool, handle_list_tools, start_watch_mode
from mcp_server.workspace import InvalidWorkspaceError


async def call(name, arguments=None):
    response = await handle_call_tool(name, arguments)
    return response[0].text


def git_output(repo, *args):
    return subprocess.check_output(["git", *args], cwd=repo, text=True).strip()


@asynccontextmanager
async def mcp_client(cwd, **env):
    params = StdioServerParameters(
        command=sys.executable, args=["-m", "mcp_server"], cwd=cwd,
        env={"GEMINI_API_KEY": "test-key-not-real", "GIT_CONFIG_GLOBAL": os.devnull, **env},
    )
    async with stdio_client(params) as streams, ClientSession(*streams) as session:
        await session.initialize()
        yield session


@pytest.fixture
def projects(git_repo, tmp_path, monkeypatch):
    second = tmp_path / "second project"
    subprocess.run(["git", "init", str(second)], capture_output=True, check=True)
    (git_repo / "first.txt").touch()
    (second / "second.txt").touch()
    monkeypatch.delenv("WORKSPACE_FOLDER_PATHS", raising=False)
    monkeypatch.delenv("PROJECT_ROOT", raising=False)
    monkeypatch.chdir(git_repo)
    return git_repo, second


@pytest.mark.asyncio
async def test_repo_path_is_optional_in_tool_schemas():
    for tool in await handle_list_tools():
        assert tool.inputSchema["properties"]["repo_path"]["type"] == "string", tool.name
        assert "repo_path" not in tool.inputSchema.get("required", [])


@pytest.mark.asyncio
@pytest.mark.parametrize("source", ["WORKSPACE_FOLDER_PATHS", "PROJECT_ROOT", "cwd"])
async def test_status_follows_project_switch(projects, monkeypatch, source):
    for repo, marker in zip(projects, ["first.txt", "second.txt"]):
        if source == "cwd":
            monkeypatch.chdir(repo)
        else:
            monkeypatch.setenv(source, str(repo))
        assert marker in await call("fckgit_status")


@pytest.mark.asyncio
async def test_overlapping_calls_keep_their_own_repository(projects, monkeypatch):
    first, second = projects
    monkeypatch.setenv("WORKSPACE_FOLDER_PATHS", str(first))
    nested = second / "src"
    nested.mkdir()
    default, explicit = await asyncio.gather(
        call("fckgit_status"),
        call("fckgit_status", {"repo_path": str(nested)}),
    )
    assert "first.txt" in default and "second.txt" not in default
    assert "second.txt" in explicit and "first.txt" not in explicit
    assert "first.txt" in await call("fckgit_status")


@pytest.mark.asyncio
async def test_invalid_targets_are_mcp_errors(projects, tmp_path):
    first, _ = projects
    async with mcp_client(first) as session:
        for invalid in [None, 42, "", "  ", str(first / "first.txt"), str(first / "missing"), str(tmp_path)]:
            result = await session.call_tool("fckgit_status", {"repo_path": invalid})
            assert result.isError, invalid
        result = await session.call_tool("fckgit_status", {})
        assert not result.isError and "first.txt" in result.content[0].text


@pytest.mark.asyncio
@pytest.mark.parametrize("setting", ["WORKSPACE_FOLDER_PATHS", "PROJECT_ROOT"])
async def test_missing_configured_repo_blocks_commit(projects, monkeypatch, setting):
    first, second = projects
    monkeypatch.setenv(setting, str(second))
    assert "second.txt" in await call("fckgit_status")
    second.rename(second.with_name("moved"))
    with pytest.raises(InvalidWorkspaceError, match="does not exist"):
        await call("fckgit_commit_with_message", {"message": "Wrong target"})
    assert "first.txt" in await call("fckgit_status", {"repo_path": str(first)})
    monkeypatch.delenv(setting)
    assert "first.txt" in await call("fckgit_status")


@pytest.mark.asyncio
async def test_commit_ignores_inherited_git_target(projects):
    first, second = projects
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=second, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=second, check=True)
    args = {"repo_path": str(second)}
    async with mcp_client(
        first, GIT_DIR=str(first / ".git"), GIT_WORK_TREE=str(first),
        GIT_INDEX_FILE=str(first / ".git" / "index"),
    ) as session:
        status = await session.call_tool("fckgit_status", args)
        assert not status.isError and "second.txt" in status.content[0].text
        debug = await session.call_tool("fckgit_debug", args)
        assert Path(ast.literal_eval(debug.content[0].text)["git_root"]) == second
        commit = await session.call_tool(
            "fckgit_commit_with_message", {**args, "message": "Second project"}
        )
        assert not commit.isError and "Committed successfully" in commit.content[0].text
        default = await session.call_tool("fckgit_status", {})
        assert not default.isError and "first.txt" in default.content[0].text
    assert git_output(second, "ls-tree", "--name-only", "HEAD") == "second.txt"
    assert git_output(first, "log", "-1", "--format=%s") == "Initial commit"
    assert git_output(first, "status", "--porcelain") == "?? first.txt"


@pytest.mark.asyncio
async def test_commit_respects_discovery_ceiling(git_repo):
    child = git_repo / "unversioned"
    child.mkdir()
    (child / "new.txt").touch()
    (git_repo / "README.md").write_text("parent edit")
    head = git_output(git_repo, "rev-parse", "HEAD")
    status = git_output(git_repo, "status", "--porcelain")
    async with mcp_client(child, GIT_CEILING_DIRECTORIES=str(git_repo)) as session:
        result = await session.call_tool("fckgit_commit_with_message", {"message": "Child edit"})
        assert result.isError
        result = await session.call_tool("fckgit_status", {"repo_path": str(child)})
        assert result.isError
    assert git_output(git_repo, "rev-parse", "HEAD") == head
    assert git_output(git_repo, "status", "--porcelain") == status


@pytest.mark.asyncio
async def test_stdio_preserves_git_root_spelling(projects):
    first, second = projects
    # POSIX also allows whitespace at the end of a directory name.
    target = second.rename(second.with_name("caf\u00e9" if os.name == "nt" else "caf\u00e9 \n"))
    async with mcp_client(first, PYTHONUTF8="0") as session:
        args = {"repo_path": str(target)}
        status = await session.call_tool("fckgit_status", args)
        assert not status.isError and "second.txt" in status.content[0].text
        debug = await session.call_tool("fckgit_debug", args)
        assert Path(ast.literal_eval(debug.content[0].text)["git_root"]) == target


@pytest.mark.asyncio
async def test_default_commit_uses_configured_identity_and_selected_worktree(projects):
    first, second = projects
    async with mcp_client(
        first, PROJECT_ROOT=str(second), GIT_DIR=str(first / ".git"), GIT_CONFIG_COUNT="3",
        GIT_CONFIG_KEY_0="user.name", GIT_CONFIG_VALUE_0="MCP Author",
        GIT_CONFIG_KEY_1="core.worktree", GIT_CONFIG_VALUE_1=str(first),
        GIT_CONFIG_KEY_2="user.email", GIT_CONFIG_VALUE_2="mcp@example.com",
    ) as session:
        result = await session.call_tool("fckgit_commit_with_message", {"message": "Second repo"})
        assert not result.isError, result.content[0].text
    assert git_output(second, "log", "-1", "--format=%an <%ae>") == "MCP Author <mcp@example.com>"
    assert git_output(second, "ls-tree", "--name-only", "HEAD") == "second.txt"
    assert git_output(first, "status", "--porcelain") == "?? first.txt"
    assert git_output(first, "log", "-1", "--format=%s") == "Initial commit"


@pytest.mark.asyncio
async def test_worktree_tools_reject_git_metadata(git_repo, bare_repo):
    async with mcp_client(git_repo) as session:
        for path in (git_repo / ".git", bare_repo):
            for tool in ("fckgit_status", "fckgit_generate_message", "fckgit_watch_status"):
                result = await session.call_tool(tool, {"repo_path": str(path)})
                assert result.isError and "work" in result.content[0].text.lower(), (tool, path)
            debug = await session.call_tool("fckgit_debug", {"repo_path": str(path)})
            assert not debug.isError
            info = ast.literal_eval(debug.content[0].text)
            assert info["git_repository"] and info["is_bare"] == (path == bare_repo)
            assert "git_root" not in info


@pytest.mark.asyncio
async def test_git_read_errors_reach_the_client(git_repo):
    (git_repo / ".git" / "index").write_bytes(b"invalid index")
    async with mcp_client(git_repo) as session:
        for tool in ("fckgit_status", "fckgit_generate_message"):
            result = await session.call_tool(tool, {})
            assert result.isError and "index" in result.content[0].text.lower()


@pytest.mark.asyncio
async def test_debug_keeps_unrelated_environment_private(projects):
    first, second = projects
    async with mcp_client(first, PROJECT_ROOT=str(second), PROJECT_SERVICE_TOKEN="private-test-marker") as session:
        reply = await session.call_tool("fckgit_debug", {})
        result = reply.content[0].text
        assert "private-test-marker" not in result and "PROJECT_SERVICE_TOKEN" not in result
        assert Path(ast.literal_eval(result)["git_root"]) == second


@pytest.mark.asyncio
async def test_debug_reports_selected_root_and_handles_non_repo(projects, tmp_path):
    _, second = projects
    nested = second / "src"
    nested.mkdir()
    info = ast.literal_eval(await call("fckgit_debug", {"repo_path": str(nested)}))
    assert Path(info["git_root"]) == second
    assert info["detection_method"] == "override_parameter"
    assert info["git_changes_detected"] == 1
    outside = ast.literal_eval(await call("fckgit_debug", {"repo_path": str(tmp_path)}))
    assert outside["git_repository"] is False


@pytest.mark.asyncio
@pytest.mark.parametrize(("tool", "stage_all"), [
    ("fckgit_commit_with_message", True),
    ("fckgit_commit_with_message", False),
    ("fckgit_commit", True),
    ("fckgit_silicon_valley", True),
])
async def test_commit_preserves_worktree_locks(git_repo, git_worktree, monkeypatch, tool, stage_all):
    monkeypatch.chdir(git_repo)
    monkeypatch.setenv("WORKSPACE_FOLDER_PATHS", str(git_repo))
    args = {"repo_path": str(git_worktree), "stage_all": stage_all}
    (git_worktree / "change.txt").write_text("worktree change")
    if not stage_all:
        subprocess.run(["git", "add", "change.txt"], cwd=git_worktree, check=True)

    main_lock = git_repo / ".git" / "index.lock"
    git_dir = git_output(git_worktree, "rev-parse", "--absolute-git-dir")
    locks = [main_lock, Path(git_dir) / "index.lock"]
    for lock in locks:
        lock.write_bytes(b"active writer")
    with pytest.raises(RuntimeError, match=r"index\.lock"):
        await call(tool, {**args, "message": "Worktree change"})
    for lock in locks:
        assert lock.read_bytes() == b"active writer"
    for repo in (git_worktree, git_repo):
        assert git_output(repo, "log", "-1", "--format=%s") == "Initial commit"


@pytest.mark.asyncio
async def test_watch_tools_match_command_and_worktree_root(projects, monkeypatch):
    first, second = projects
    nested = second / "src"
    nested.mkdir()

    def process(pid, cwd, args, exe=sys.executable):
        proc = Mock(pid=pid)
        proc.info = {"pid": pid, "cwd": str(cwd), "exe": exe, "cmdline": [exe, *args]}
        return proc

    other = process(11, first, ["-m", "fckgit"])
    watcher = process(22, nested, ["-m", "fckgit", "--cooldown", "10"])
    unrelated = process(33, second, ["-m", "pytest", "test_fckgit.py"])
    once = process(44, second, ["-m", "fckgit", "--once"])
    non_python = process(55, second, ["-m", "fckgit"], exe="unrelated")
    procs = [unrelated, once, non_python, other, watcher]
    monkeypatch.setattr("mcp_server.server.psutil.process_iter", lambda attrs: procs)
    args = {"repo_path": str(second)}
    assert "PID: 22" in await call("fckgit_watch_status", args)
    assert "already running (PID: 22)" in await call("fckgit_blastoff", args)
    for proc in (other, unrelated, once, non_python):
        assert "No fckgit watch process" in await call("fckgit_stop_watch", {**args, "pid": proc.pid})
        proc.terminate.assert_not_called()
    assert "Stopped" in await call("fckgit_stop_watch", {**args, "pid": watcher.pid})
    watcher.terminate.assert_called_once_with()


def test_watcher_commit_preserves_active_lock(git_repo):
    lock = git_repo / ".git" / "index.lock"
    lock.write_bytes(b"active writer")
    (git_repo / "change.txt").touch()
    result = subprocess.run(
        [sys.executable, "-E", "-c", "from fckgit import commit; commit('Watch change')"],
        cwd=git_repo, capture_output=True, text=True, encoding="utf-8", check=True,
    )
    assert "index.lock" in result.stdout
    assert lock.read_bytes() == b"active writer"


@pytest.mark.asyncio
async def test_live_module_watcher_lifecycle(git_repo, tmp_path):
    log = tmp_path / "watch.log"
    with log.open("wb") as output:
        watcher = subprocess.Popen(
            [sys.executable, "-B", "-m", "fckgit"], cwd=git_repo,
            env={**os.environ, "PYTHONUTF8": "1", "PYTHONUNBUFFERED": "1"},
            stdin=subprocess.DEVNULL, stdout=output, stderr=subprocess.STDOUT,
        )
    try:
        deadline = time.monotonic() + 30
        while "Press Ctrl+C" not in log.read_text(encoding="utf-8"):
            assert watcher.poll() is None and time.monotonic() < deadline, log.read_text(encoding="utf-8")
            await asyncio.sleep(0.1)
        args = {"repo_path": str(git_repo)}
        status = await call("fckgit_watch_status", args)
        assert "is running (PID:" in status, status
        pid = int(status.split("PID: ")[1].split(")")[0])
        assert f"already running (PID: {pid})" in await call("fckgit_blastoff", args)
        assert "Stopped" in await call("fckgit_stop_watch", {**args, "pid": pid})
        watcher.wait(timeout=5)
        assert "is not running" in await call("fckgit_watch_status", args)
    finally:
        if watcher.poll() is None:
            watcher.terminate()
            watcher.wait(timeout=5)


@pytest.mark.asyncio
async def test_fractional_cooldown_is_an_mcp_error(git_repo):
    async with mcp_client(git_repo) as session:
        result = await session.call_tool("fckgit_blastoff", {"cooldown": 2.5})
        assert result.isError and "integer" in result.content[0].text


@pytest.mark.asyncio
async def test_watcher_launch_uses_installed_cli_and_clean_git_env(projects, monkeypatch):
    first, second = projects
    (second / "fckgit.py").touch()
    (second / "argparse.py").touch()
    monkeypatch.setenv("PYTHONPATH", str(second))
    monkeypatch.setenv("GIT_DIR", str(first / ".git"))
    monkeypatch.setenv("GIT_WORK_TREE", str(first))
    monkeypatch.setattr("mcp_server.server.psutil.process_iter", lambda attrs: [])
    with monkeypatch.context() as launch:
        popen = Mock()
        launch.setattr(subprocess, "Popen", popen)
        with pytest.raises(ValueError, match="cooldown"):
            await start_watch_mode(second, cooldown=2.5)
        popen.assert_not_called()
        started, _, _ = await start_watch_mode(second, cooldown=2.0)
        assert started
    (cmd,), kwargs = popen.call_args
    assert cmd[cmd.index("--cooldown") + 1] == "2"
    assert kwargs["cwd"] == second
    env = kwargs.get("env", os.environ)
    assert "GIT_DIR" not in env and "GIT_WORK_TREE" not in env
    help_text = subprocess.check_output([*cmd, "--help"], cwd=second, env=env, text=True)
    assert "--cooldown" in help_text
