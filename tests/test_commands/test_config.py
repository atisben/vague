"""Tests for config commands."""

import pytest
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


def test_config_set_boolean(vague_home):
    runner.invoke(sdk_app, ["config-set", "proactive", "false"])
    result = runner.invoke(sdk_app, ["config-get", "proactive"])
    assert result.exit_code == 0
    assert result.output.strip() == "False"


def test_config_get_existing_key(vague_home):
    from vague.sdk.core.config import set_config_key
    set_config_key("telemetry", "local")
    result = runner.invoke(sdk_app, ["config-get", "telemetry"])
    assert result.exit_code == 0
    assert result.output.strip() == "local"
