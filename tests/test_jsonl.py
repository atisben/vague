"""Tests for vague.jsonl: the append-only line files behind memory and events."""

from vague import jsonl


def test_append_then_read_round_trips_one_object_per_line(tmp_path):
    path = tmp_path / "events" / "2026-11.jsonl"
    jsonl.append(path=path, line='{"a": 1}')
    jsonl.append(path=path, line='{"b": 2}')
    assert path.read_text() == '{"a": 1}\n{"b": 2}\n'
    assert jsonl.read(path=path) == [{"a": 1}, {"b": 2}]


def test_read_skips_torn_and_non_object_lines(tmp_path):
    path = tmp_path / "x.jsonl"
    path.write_bytes(b'{"a": 1}\n[1, 2]\n\n{"torn": "\xc3')
    assert jsonl.read(path=path) == [{"a": 1}]


def test_read_missing_file_returns_empty(tmp_path):
    assert jsonl.read(path=tmp_path / "nope.jsonl") == []
