"""Tests for vague.hooks.edited_file: the file a Write or Edit hook payload names."""

import pytest

from vague.hooks import edited_file


def test_edited_file_resolves_a_relative_path_against_the_payload_cwd(tmp_path, hook_payload):
    payload = hook_payload(tool_input={"file_path": "src/app.css"}, cwd=str(tmp_path))
    assert edited_file(payload=payload) == (tmp_path / "src" / "app.css").resolve()


def test_edited_file_follows_symlinks(tmp_path, hook_payload):
    real = tmp_path / "real"
    real.mkdir()
    (tmp_path / "link").symlink_to(real)
    payload = hook_payload(tool_input={"file_path": str(tmp_path / "link" / "a.md")})
    assert edited_file(payload=payload) == real.resolve() / "a.md"


@pytest.mark.parametrize("tool_name, tool_input", [
    ("Read", {"file_path": "/x/a.md"}), ("Write", {}), ("Edit", {"file_path": ""}), ("Write", None),
])
def test_edited_file_is_none_without_a_written_path(hook_payload, tool_name, tool_input):
    payload = {**hook_payload(tool_name=tool_name), "tool_input": tool_input}
    assert edited_file(payload=payload) is None
