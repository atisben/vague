"""Tests for core/config.py"""


from vague.models import ConfigModel
from vague.sdk.core.config import get_config, set_config_key


def test_get_config_returns_defaults_when_no_file(vague_home):
    config = get_config()
    assert config.telemetry == "local"


def test_get_config_returns_defaults_on_corrupt_file(vague_home, capsys):
    config_path = vague_home / "config.md"
    config_path.write_text("---\nkey: [\nbad: [yaml\n---\n")
    config = get_config()
    assert config == ConfigModel()
    captured = capsys.readouterr()
    assert "Warning" in captured.err


def test_set_and_get_config_key(vague_home):
    set_config_key("telemetry", "off")
    config = get_config()
    assert config.telemetry == "off"


def test_set_config_key_preserves_other_keys(vague_home):
    set_config_key("custom", "kept")
    set_config_key("telemetry", "off")
    assert (vague_home / "config.md").read_text().count("custom: kept") == 1
    assert get_config().telemetry == "off"
