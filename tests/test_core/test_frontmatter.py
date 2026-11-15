"""Tests for core/frontmatter.py"""


import pytest

from vague.sdk.core.frontmatter import FrontmatterError, read_md


def test_read_md_nonexistent(tmp_path):
    result = read_md(tmp_path / "nonexistent.md")
    assert result == {}


def test_frontmatter_error_on_corrupt(tmp_path):
    path = tmp_path / "corrupt.md"
    # Write corrupt frontmatter
    path.write_text("---\nkey: [\nbad yaml\n---\n")
    with pytest.raises(FrontmatterError):
        read_md(path)
