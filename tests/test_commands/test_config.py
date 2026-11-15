"""Tests for config commands."""

from typer.testing import CliRunner

from vague.sdk.cli import sdk_app

runner = CliRunner()


def test_config_get_unknown_key_returns_null(vague_home):
    result = runner.invoke(sdk_app, ["config-get", "nonexistent-key"])
    assert result.exit_code == 0
    assert result.output.strip() == "null"


def test_config_set_and_get_roundtrip(vague_home):
    runner.invoke(sdk_app, ["config-set", "telemetry", "off"])
    result = runner.invoke(sdk_app, ["config-get", "telemetry"])
    assert result.exit_code == 0
    assert result.output.strip() == "off"


def test_config_get_reads_any_key_in_config_env(vague_home):
    (vague_home / "config.env").write_text("VAGUE_CLAUDE_DIRS=~/.claude-work\n")
    result = runner.invoke(sdk_app, ["config-get", "VAGUE_CLAUDE_DIRS"])
    assert result.output.strip() == "~/.claude-work"


def test_config_get_existing_key(vague_home):
    from vague.config import set_config_key
    set_config_key(key="telemetry", value="local")
    result = runner.invoke(sdk_app, ["config-get", "telemetry"])
    assert result.exit_code == 0
    assert result.output.strip() == "local"
