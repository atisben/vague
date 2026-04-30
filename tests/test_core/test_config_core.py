"""Tests for core/config.py"""

import os
import pytest
from pathlib import Path

from vague.models import ConfigModel
from vague.sdk.core.config import get_config, set_config_key


def test_get_config_returns_defaults_when_no_file(vague_home):
    config = get_config()
    assert config.proactive == True
    assert config.telemetry == "local"


def test_get_config_returns_defaults_on_corrupt_file(vague_home, capsys):
    config_path = vague_home / "config.md"
    config_path.write_text("---\nkey: [\nbad: [yaml\n---\n")
    config = get_config()
    assert isinstance(config, ConfigModel)
    assert config.proactive == True
    captured = capsys.readouterr()
    assert "Warning" in captured.err


def test_set_and_get_config_key(vague_home):
    set_config_key("proactive", False)
    config = get_config()
    assert config.proactive == False


def test_set_config_key_preserves_other_keys(vague_home):
    set_config_key("proactive", True)
    set_config_key("telemetry", "off")
    config = get_config()
    assert config.proactive == True
    assert config.telemetry == "off"
