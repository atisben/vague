"""Tests for core/frontmatter.py"""

import pytest
from pathlib import Path

from vague.sdk.core.frontmatter import read_md, write_md, update_md, FrontmatterError


def test_read_md_nonexistent(tmp_path):
    result = read_md(tmp_path / "nonexistent.md")
    assert result == {}


def test_write_md_creates_file(tmp_path):
    path = tmp_path / "test.md"
    write_md(path, {"key": "value"}, body="Hello")
    assert path.exists()
    content = path.read_text()
    assert "key: value" in content
    assert "Hello" in content


def test_write_md_creates_parent_dirs(tmp_path):
    path = tmp_path / "nested" / "dir" / "test.md"
    write_md(path, {"foo": "bar"})
    assert path.exists()


def test_write_md_roundtrip(tmp_path):
    path = tmp_path / "test.md"
    data = {"proactive": True, "telemetry": "local"}
    write_md(path, data)
    result = read_md(path)
    assert result["proactive"] == True
    assert result["telemetry"] == "local"


def test_write_md_atomic(tmp_path):
    """write_md should not leave partial files."""
    path = tmp_path / "test.md"
    write_md(path, {"step": 1})
    write_md(path, {"step": 2})
    result = read_md(path)
    assert result["step"] == 2


def test_update_md_merges(tmp_path):
    path = tmp_path / "test.md"
    write_md(path, {"a": 1, "b": 2})
    update_md(path, lambda d: {**d, "b": 99, "c": 3})
    result = read_md(path)
    assert result["a"] == 1
    assert result["b"] == 99
    assert result["c"] == 3


def test_update_md_creates_file(tmp_path):
    path = tmp_path / "new.md"
    update_md(path, lambda d: {"created": True})
    result = read_md(path)
    assert result["created"] == True


def test_frontmatter_error_on_corrupt(tmp_path):
    path = tmp_path / "corrupt.md"
    # Write corrupt frontmatter
    path.write_text("---\nkey: [\nbad yaml\n---\n")
    with pytest.raises(FrontmatterError):
        read_md(path)
