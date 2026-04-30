"""Tests for slug command."""

import pytest
from typer.testing import CliRunner

from vague.sdk.cli import sdk_app

runner = CliRunner()


def test_slug_outputs_slug_and_branch(vague_home):
    result = runner.invoke(sdk_app, ["slug"])
    assert result.exit_code == 0
    assert "SLUG=" in result.output
    assert "BRANCH=" in result.output
