"""Tests for vague/config.py."""

from pathlib import Path

import pytest
from typer.testing import CliRunner

from vague.cli import app
from vague.config import (
    claude_dirs,
    get_config,
    load_config,
    profile_name_for,
    set_config_key,
)


@pytest.fixture
def clean_env(monkeypatch):
    """Remove every config env var so tests start from a known state."""
    for var in ("VAGUE_CLAUDE_DIRS", "CLAUDE_CONFIG_DIR"):
        monkeypatch.delenv(var, raising=False)


class TestLoadConfig:
    def test_returns_empty_when_no_file(self, vague_home, monkeypatch):
        assert load_config() == {}

    def test_parses_key_value_pairs(self, vague_home, monkeypatch):
        (vague_home / "config.env").write_text("VAGUE_CLAUDE_DIRS=~/.claude-work\nOTHER=value\n")
        config = load_config()
        assert config["VAGUE_CLAUDE_DIRS"] == "~/.claude-work"
        assert config["OTHER"] == "value"

    def test_ignores_comments_and_blank_lines(self, vague_home, monkeypatch):
        (vague_home / "config.env").write_text("# a comment\n\nKEY=value\n\n  # indented comment\n")
        assert load_config() == {"KEY": "value"}

    def test_strips_surrounding_quotes(self, vague_home, monkeypatch):
        (vague_home / "config.env").write_text("KEY=\"quoted value\"\nOTHER='single'\n")
        config = load_config()
        assert config["KEY"] == "quoted value"
        assert config["OTHER"] == "single"

    def test_ignores_malformed_lines(self, vague_home, monkeypatch):
        (vague_home / "config.env").write_text("no_equals_sign\nKEY=value\n")
        assert load_config() == {"KEY": "value"}

    def test_value_may_contain_equals(self, vague_home, monkeypatch):
        (vague_home / "config.env").write_text("KEY=a=b=c\n")
        assert load_config()["KEY"] == "a=b=c"


class TestClaudeDirs:
    def test_empty_when_nothing_configured(self, vague_home, monkeypatch, clean_env):
        assert claude_dirs() == []

    def test_reads_from_config_file(self, vague_home, tmp_path, monkeypatch, clean_env):
        work = tmp_path / ".claude-work"
        personal = tmp_path / ".claude-personal"
        (vague_home / "config.env").write_text(f"VAGUE_CLAUDE_DIRS={work}:{personal}\n")
        assert claude_dirs() == [work, personal]

    def test_env_var_overrides_config_file(self, vague_home, tmp_path, monkeypatch, clean_env):
        (vague_home / "config.env").write_text("VAGUE_CLAUDE_DIRS=/from/file\n")
        monkeypatch.setenv("VAGUE_CLAUDE_DIRS", str(tmp_path / ".claude-env"))
        assert claude_dirs() == [tmp_path / ".claude-env"]

    def test_falls_back_to_claude_config_dir(self, vague_home, tmp_path, monkeypatch, clean_env):
        monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path / ".claude-personal"))
        assert claude_dirs() == [tmp_path / ".claude-personal"]

    def test_claude_dirs_wins_over_claude_config_dir(self, vague_home, tmp_path, monkeypatch, clean_env):
        monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path / ".ignored"))
        monkeypatch.setenv("VAGUE_CLAUDE_DIRS", str(tmp_path / ".wins"))
        assert claude_dirs() == [tmp_path / ".wins"]

    def test_expands_tilde_and_strips_whitespace(self, vague_home, monkeypatch, clean_env):
        monkeypatch.setenv("VAGUE_CLAUDE_DIRS", " ~/.claude-work : ~/.claude-personal ")
        dirs = claude_dirs()
        assert len(dirs) == 2
        assert all("~" not in str(d) for d in dirs)
        assert [d.name for d in dirs] == [".claude-work", ".claude-personal"]

    def test_drops_empty_segments(self, vague_home, monkeypatch, clean_env):
        monkeypatch.setenv("VAGUE_CLAUDE_DIRS", "/a::/b:")
        assert claude_dirs() == [Path("/a"), Path("/b")]

    def test_deduplicates_preserving_order(self, vague_home, monkeypatch, clean_env):
        monkeypatch.setenv("VAGUE_CLAUDE_DIRS", "/a:/b:/a")
        assert [str(d) for d in claude_dirs()] == ["/a", "/b"]


class TestProfileNameFor:
    @pytest.mark.parametrize(
        ("dirname", "expected"),
        [
            (".claude-work", "work"),
            (".claude-personal", "personal"),
            (".claude", "default"),
            ("claude-work", "work"),
            (".claude_work", "work"),
        ],
    )
    def test_derives_readable_profile_name(self, tmp_path, dirname, expected):
        assert profile_name_for(tmp_path / dirname) == expected

    def test_falls_back_to_directory_name(self, tmp_path):
        assert profile_name_for(tmp_path / ".somethingelse") == "somethingelse"


def test_get_config_returns_defaults_when_no_file(vague_home):
    assert get_config().telemetry == "local"


def test_get_config_reads_telemetry_from_config_env(vague_home):
    (vague_home / "config.env").write_text("VAGUE_CLAUDE_DIRS=~/.claude-work\ntelemetry=off\n")
    assert get_config().telemetry == "off"


def test_set_config_key_replaces_the_key_and_keeps_every_other_line(vague_home):
    path = vague_home / "config.env"
    path.write_text("# my profiles\nVAGUE_CLAUDE_DIRS=~/.claude-work\ntelemetry=local\n")
    set_config_key(key="telemetry", value="off")
    assert path.read_text() == "# my profiles\nVAGUE_CLAUDE_DIRS=~/.claude-work\ntelemetry=off\n"


def test_set_config_key_creates_the_file(vague_home):
    set_config_key(key="telemetry", value="off")
    assert (vague_home / "config.env").read_text() == "telemetry=off\n"


runner = CliRunner()


def test_config_get_unknown_key_returns_null(vague_home):
    result = runner.invoke(app, ["config-get", "nonexistent-key"])
    assert result.exit_code == 0
    assert result.output.strip() == "null"


def test_config_set_and_get_roundtrip(vague_home):
    runner.invoke(app, ["config-set", "telemetry", "off"])
    result = runner.invoke(app, ["config-get", "telemetry"])
    assert result.exit_code == 0
    assert result.output.strip() == "off"


def test_config_get_reads_any_key_in_config_env(vague_home):
    (vague_home / "config.env").write_text("VAGUE_CLAUDE_DIRS=~/.claude-work\n")
    result = runner.invoke(app, ["config-get", "VAGUE_CLAUDE_DIRS"])
    assert result.output.strip() == "~/.claude-work"


def test_config_get_existing_key(vague_home):
    from vague.config import set_config_key
    set_config_key(key="telemetry", value="local")
    result = runner.invoke(app, ["config-get", "telemetry"])
    assert result.exit_code == 0
    assert result.output.strip() == "local"
