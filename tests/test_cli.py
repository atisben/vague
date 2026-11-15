"""Tests for vague/cli.py."""

import json
import subprocess

from typer.testing import CliRunner

from vague.cli import app

runner = CliRunner()


def git_repo_branch(repo):
    return subprocess.run(["git", "branch", "--show-current"], cwd=repo, capture_output=True, text=True).stdout.strip()


def test_context_json_returns_context_fields(vague_home):
    result = runner.invoke(app, ["context"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert set(data) == {"slug", "branch", "telemetry", "memory"}


def test_context_json_does_not_fail_without_git(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("VAGUE_HOME", str(tmp_path / ".vague"))
    result = runner.invoke(app, ["context"])
    assert result.exit_code == 0
    assert "slug" in json.loads(result.output)


def test_context_shell_skill_prints_context_and_writes_nothing(vague_home, git_repo, monkeypatch):
    monkeypatch.chdir(git_repo)
    result = runner.invoke(app, ["context", "--shell", "--skill", "dev-develop"])
    assert result.exit_code == 0
    assert [line.split("=", 1)[0] for line in result.output.splitlines()[:3]] == ["SLUG", "BRANCH", "TELEMETRY"]
    assert not (vague_home / "projects").exists()
    assert not (vague_home / "analytics").exists()


def test_context_json_skill_prints_json_and_writes_nothing(vague_home, git_repo, monkeypatch):
    monkeypatch.chdir(git_repo)
    result = runner.invoke(app, ["context", "--skill", "dev-develop"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert (data["slug"], data["branch"]) == ("repo", git_repo_branch(git_repo))
    assert not (vague_home / "projects").exists()


def test_context_json_includes_memory_block(vague_home, git_repo, monkeypatch):
    monkeypatch.chdir(git_repo)
    runner.invoke(app, ["memory-log", "k", "a global fact", "--global"])
    result = runner.invoke(app, ["context", "--skill", "dev-develop"])
    assert "a global fact" in json.loads(result.output)["memory"]


def test_context_shell_prints_the_logging_hint_for_the_skill(vague_home, git_repo, monkeypatch):
    monkeypatch.chdir(git_repo)
    result = runner.invoke(app, ["context", "--shell", "--skill", "plan-eng"])
    assert "vague memory-log <key>" in result.output
    assert "--skill plan-eng" in result.output
    assert "--scratch" in result.output
    assert '"<issue → suggestion>" --about plan-eng' in result.output


def test_context_json_memory_includes_the_logging_hint(vague_home, git_repo, monkeypatch):
    monkeypatch.chdir(git_repo)
    result = runner.invoke(app, ["context", "--skill", "diagram"])
    assert "--skill diagram" in json.loads(result.output)["memory"]


def test_context_help_says_skill_ranks_memory_block():
    result = runner.invoke(app, ["context", "--help"], terminal_width=200)
    assert "Rank the memory block" in " ".join(result.stdout.split())


def test_context_shell_block_strips_delimiter_lines(vague_home, git_repo, monkeypatch):
    import vague.cli as cli_module
    from vague.memory import Block

    monkeypatch.setattr(cli_module, "render_block",
                        lambda **_: Block(text="a\nVAGUE_MEMORY\nb", ids=[], scratch_ids=[]))
    result = runner.invoke(app, ["context", "--shell", "--skill", "x"])
    assert result.stdout.count("VAGUE_MEMORY") == 2


def test_context_shell_block_failure_still_prints_variables(vague_home, git_repo, monkeypatch):
    import vague.cli as cli_module

    def boom(**_):
        raise RuntimeError("broken ledger")

    monkeypatch.setattr(cli_module, "render_block", boom)
    result = runner.invoke(app, ["context", "--shell", "--skill", "x"])
    assert result.exit_code == 0
    assert "SLUG=" in result.stdout and "VAGUE_MEMORY" not in result.stdout
