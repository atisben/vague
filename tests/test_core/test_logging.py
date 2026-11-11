"""Tests for local logging (vague/sdk/core/logging.py)."""

import os

import pytest

from vague.sdk.core.logging import get_logger, reset_logging


@pytest.fixture(autouse=True)
def _clean_logging():
    reset_logging()
    saved = os.environ.get("VAGUE_LOG")
    yield
    reset_logging()
    if saved is None:
        os.environ.pop("VAGUE_LOG", None)
    else:
        os.environ["VAGUE_LOG"] = saved


def test_off_by_default_writes_no_file(vague_home):
    os.environ.pop("VAGUE_LOG", None)
    get_logger().info("hello")
    assert not (vague_home / "logs" / "vague.log").exists()


def test_debug_writes_log_file(vague_home):
    os.environ["VAGUE_LOG"] = "debug"
    get_logger().info("a message")
    log = vague_home / "logs" / "vague.log"
    assert log.exists()
    assert "a message" in log.read_text()


def test_level_filters_below_threshold(vague_home):
    os.environ["VAGUE_LOG"] = "warning"
    get_logger().info("should not appear")
    get_logger().warning("should appear")
    text = (vague_home / "logs" / "vague.log").read_text()
    assert "should appear" in text
    assert "should not appear" not in text
