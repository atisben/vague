"""Tests for vague configuration loading."""

from pathlib import Path

import pytest

from vague.config import (
    claude_d_dir,
    claude_dirs,
    load_config,
    profile_name_for,
    vague_home,
)


@pytest.fixture
def clean_env(monkeypatch):
    """Remove every config env var so tests start from a known state."""
    for var in ("VAGUE_CLAUDE_DIRS", "CLAUDE_CONFIG_DIR"):
        monkeypatch.delenv(var, raising=False)


class TestVagueHome:
    def test_uses_env_var(self, vague_home_dir, monkeypatch):
        monkeypatch.setenv("VAGUE_HOME", str(vague_home_dir))
        assert vague_home() == vague_home_dir

    def test_defaults_to_home_dot_vague(self, monkeypatch):
        monkeypatch.delenv("VAGUE_HOME", raising=False)
        assert vague_home().name == ".vague"

    def test_expands_tilde(self, monkeypatch):
        monkeypatch.setenv("VAGUE_HOME", "~/.custom-vague")
        assert "~" not in str(vague_home())
        assert vague_home().name == ".custom-vague"


class TestLoadConfig:
    def test_returns_empty_when_no_file(self, vague_home_dir, monkeypatch):
        monkeypatch.setenv("VAGUE_HOME", str(vague_home_dir))
        assert load_config() == {}

    def test_parses_key_value_pairs(self, vague_home_dir, monkeypatch):
        monkeypatch.setenv("VAGUE_HOME", str(vague_home_dir))
        (vague_home_dir / "config.env").write_text("VAGUE_CLAUDE_DIRS=~/.claude-work\nOTHER=value\n")
        config = load_config()
        assert config["VAGUE_CLAUDE_DIRS"] == "~/.claude-work"
        assert config["OTHER"] == "value"

    def test_ignores_comments_and_blank_lines(self, vague_home_dir, monkeypatch):
        monkeypatch.setenv("VAGUE_HOME", str(vague_home_dir))
        (vague_home_dir / "config.env").write_text("# a comment\n\nKEY=value\n\n  # indented comment\n")
        assert load_config() == {"KEY": "value"}

    def test_strips_surrounding_quotes(self, vague_home_dir, monkeypatch):
        monkeypatch.setenv("VAGUE_HOME", str(vague_home_dir))
        (vague_home_dir / "config.env").write_text("KEY=\"quoted value\"\nOTHER='single'\n")
        config = load_config()
        assert config["KEY"] == "quoted value"
        assert config["OTHER"] == "single"

    def test_ignores_malformed_lines(self, vague_home_dir, monkeypatch):
        monkeypatch.setenv("VAGUE_HOME", str(vague_home_dir))
        (vague_home_dir / "config.env").write_text("no_equals_sign\nKEY=value\n")
        assert load_config() == {"KEY": "value"}

    def test_value_may_contain_equals(self, vague_home_dir, monkeypatch):
        monkeypatch.setenv("VAGUE_HOME", str(vague_home_dir))
        (vague_home_dir / "config.env").write_text("KEY=a=b=c\n")
        assert load_config()["KEY"] == "a=b=c"


class TestClaudeDirs:
    def test_empty_when_nothing_configured(self, vague_home_dir, monkeypatch, clean_env):
        monkeypatch.setenv("VAGUE_HOME", str(vague_home_dir))
        assert claude_dirs() == []

    def test_reads_from_config_file(self, vague_home_dir, tmp_path, monkeypatch, clean_env):
        monkeypatch.setenv("VAGUE_HOME", str(vague_home_dir))
        work = tmp_path / ".claude-work"
        personal = tmp_path / ".claude-personal"
        (vague_home_dir / "config.env").write_text(f"VAGUE_CLAUDE_DIRS={work}:{personal}\n")
        assert claude_dirs() == [work, personal]

    def test_env_var_overrides_config_file(self, vague_home_dir, tmp_path, monkeypatch, clean_env):
        monkeypatch.setenv("VAGUE_HOME", str(vague_home_dir))
        (vague_home_dir / "config.env").write_text("VAGUE_CLAUDE_DIRS=/from/file\n")
        monkeypatch.setenv("VAGUE_CLAUDE_DIRS", str(tmp_path / ".claude-env"))
        assert claude_dirs() == [tmp_path / ".claude-env"]

    def test_falls_back_to_claude_config_dir(self, vague_home_dir, tmp_path, monkeypatch, clean_env):
        monkeypatch.setenv("VAGUE_HOME", str(vague_home_dir))
        monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path / ".claude-personal"))
        assert claude_dirs() == [tmp_path / ".claude-personal"]

    def test_claude_dirs_wins_over_claude_config_dir(self, vague_home_dir, tmp_path, monkeypatch, clean_env):
        monkeypatch.setenv("VAGUE_HOME", str(vague_home_dir))
        monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path / ".ignored"))
        monkeypatch.setenv("VAGUE_CLAUDE_DIRS", str(tmp_path / ".wins"))
        assert claude_dirs() == [tmp_path / ".wins"]

    def test_expands_tilde_and_strips_whitespace(self, vague_home_dir, monkeypatch, clean_env):
        monkeypatch.setenv("VAGUE_HOME", str(vague_home_dir))
        monkeypatch.setenv("VAGUE_CLAUDE_DIRS", " ~/.claude-work : ~/.claude-personal ")
        dirs = claude_dirs()
        assert len(dirs) == 2
        assert all("~" not in str(d) for d in dirs)
        assert [d.name for d in dirs] == [".claude-work", ".claude-personal"]

    def test_drops_empty_segments(self, vague_home_dir, monkeypatch, clean_env):
        monkeypatch.setenv("VAGUE_HOME", str(vague_home_dir))
        monkeypatch.setenv("VAGUE_CLAUDE_DIRS", "/a::/b:")
        assert claude_dirs() == [Path("/a"), Path("/b")]

    def test_deduplicates_preserving_order(self, vague_home_dir, monkeypatch, clean_env):
        monkeypatch.setenv("VAGUE_HOME", str(vague_home_dir))
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


class TestClaudeDDir:
    def test_lives_under_vague_home(self, vague_home_dir, monkeypatch):
        monkeypatch.setenv("VAGUE_HOME", str(vague_home_dir))
        assert claude_d_dir() == vague_home_dir / "claude.d"
