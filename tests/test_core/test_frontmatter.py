"""Tests for core/frontmatter.py"""


import pytest

from vague.sdk.core.frontmatter import FrontmatterError, read_md, update_md


def test_read_md_nonexistent(tmp_path):
    result = read_md(tmp_path / "nonexistent.md")
    assert result == {}


def test_update_md_merges(tmp_path):
    path = tmp_path / "test.md"
    path.write_text("---\na: 1\nb: 2\n---\nbody\n")
    update_md(path, lambda d: {**d, "b": 99, "c": 3})
    result = read_md(path)
    assert result["a"] == 1
    assert result["b"] == 99
    assert result["c"] == 3
    assert path.read_text().rstrip().endswith("body")


def test_update_md_creates_file(tmp_path):
    path = tmp_path / "new.md"
    update_md(path, lambda d: {"created": True})
    result = read_md(path)
    assert result["created"] is True


def test_frontmatter_error_on_corrupt(tmp_path):
    path = tmp_path / "corrupt.md"
    # Write corrupt frontmatter
    path.write_text("---\nkey: [\nbad yaml\n---\n")
    with pytest.raises(FrontmatterError):
        read_md(path)
