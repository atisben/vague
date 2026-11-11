"""Tests for vague context."""

import json

from typer.testing import CliRunner

from vague.sdk.cli import sdk_app

runner = CliRunner()


def test_context_json_returns_context_fields(vague_home):
    result = runner.invoke(sdk_app, ["context"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert set(data) == {"slug", "branch", "proactive", "telemetry", "memory"}


def test_context_json_does_not_fail_without_git(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("VAGUE_HOME", str(tmp_path / ".vague"))
    result = runner.invoke(sdk_app, ["context"])
    assert result.exit_code == 0
    assert "slug" in json.loads(result.output)


def test_init_command_is_gone(vague_home):
    result = runner.invoke(sdk_app, ["init"])
    assert result.exit_code != 0


def test_context_shell_skill_prints_context_and_writes_nothing(vague_home, git_repo, monkeypatch):
    monkeypatch.chdir(git_repo)
    result = runner.invoke(sdk_app, ["context", "--shell", "--skill", "dev-develop"])
    assert result.exit_code == 0
    for prefix in ("SLUG=", "BRANCH=", "PROACTIVE=", "TELEMETRY="):
        assert prefix in result.output
    assert not (vague_home / "projects").exists()
    assert not (vague_home / "analytics").exists()


def test_context_json_skill_prints_json_and_writes_nothing(vague_home, git_repo, monkeypatch):
    monkeypatch.chdir(git_repo)
    result = runner.invoke(sdk_app, ["context", "--skill", "dev-develop"])
    assert result.exit_code == 0
    assert json.loads(result.output)["slug"] == "repo"
    assert not (vague_home / "projects").exists()


def test_context_json_includes_memory_block(vague_home, git_repo, monkeypatch):
    monkeypatch.chdir(git_repo)
    runner.invoke(sdk_app, ["memory-log", "k", "a global fact", "--global"])
    result = runner.invoke(sdk_app, ["context", "--skill", "dev-develop"])
    assert "a global fact" in json.loads(result.output)["memory"]


def test_context_shell_prints_the_logging_hint_for_the_skill(vague_home, git_repo, monkeypatch):
    monkeypatch.chdir(git_repo)
    result = runner.invoke(sdk_app, ["context", "--shell", "--skill", "plan-eng"])
    assert "vague memory-log <key>" in result.output
    assert "--skill plan-eng" in result.output
    assert "--scratch" in result.output


def test_context_json_memory_includes_the_logging_hint(vague_home, git_repo, monkeypatch):
    monkeypatch.chdir(git_repo)
    result = runner.invoke(sdk_app, ["context", "--skill", "diagram"])
    assert "--skill diagram" in json.loads(result.output)["memory"]
