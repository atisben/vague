"""Tests for get_config and set_config_key: one file, $VAGUE_HOME/config.env."""

from vague.config import get_config, set_config_key


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
