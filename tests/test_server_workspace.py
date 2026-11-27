"""Repository selection through the MCP tool interface."""

import asyncio
import ast
import subprocess
from pathlib import Path
from unittest.mock import Mock

import pytest

from mcp_server.server import handle_call_tool, handle_list_tools


async def call(name, arguments=None):
    response = await handle_call_tool(name, arguments)
    return response[0].text


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
async def test_invalid_repo_path_never_uses_default(projects, tmp_path):
    first, _ = projects
    for invalid in [None, 42, "", "  ", str(first / "first.txt"), str(first / "missing"), str(tmp_path)]:
        assert (await call("fckgit_status", {"repo_path": invalid})).startswith("Error:")


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
async def test_commit_uses_selected_worktree_and_its_index_lock(git_repo, git_worktree, monkeypatch):
    monkeypatch.chdir(git_repo)
    monkeypatch.setenv("WORKSPACE_FOLDER_PATHS", str(git_repo))
    args = {"repo_path": str(git_worktree)}
    (git_worktree / "change.txt").write_text("worktree change")
    assert "change.txt" in await call("fckgit_status", args)

    main_lock = git_repo / ".git" / "index.lock"
    git_dir = subprocess.check_output(
        ["git", "rev-parse", "--absolute-git-dir"], cwd=git_worktree, text=True
    ).strip()
    main_lock.touch()
    (Path(git_dir) / "index.lock").touch()
    result = await call("fckgit_commit_with_message", {**args, "message": "Worktree change"})
    assert "Committed successfully" in result
    assert main_lock.exists()
    for repo, subject in [(git_worktree, "Worktree change"), (git_repo, "Initial commit")]:
        assert subprocess.check_output(
            ["git", "log", "-1", "--format=%s"], cwd=repo, text=True
        ).strip() == subject


@pytest.mark.asyncio
async def test_stop_watch_checks_pid_in_selected_repository(projects, monkeypatch):
    first, second = projects
    watches = [{"pid": 11, "cwd": str(first)}, {"pid": 22, "cwd": str(second)}]
    process = Mock()
    monkeypatch.setattr("mcp_server.server.find_fckgit_processes", lambda: watches)
    monkeypatch.setattr("mcp_server.server.psutil.Process", process)

    await call("fckgit_stop_watch", {"repo_path": str(second), "pid": 11})
    process.assert_not_called()
    await call("fckgit_stop_watch", {"repo_path": str(second), "pid": 22})
    process.assert_called_once_with(22)
    process.return_value.terminate.assert_called_once_with()
