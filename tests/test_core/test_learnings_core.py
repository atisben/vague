"""Tests for core/learnings.py"""

import pytest
from datetime import datetime, timezone

from vague.models import LearningEntry
from vague.sdk.core.learnings import append_learning, search_learnings, get_top_learnings


def _make_entry(**kwargs):
    defaults = {
        "skill": "test",
        "type": "pitfall",
        "key": "test-key",
        "insight": "Test insight",
        "confidence": 7,
        "source": "observed",
        "ts": datetime(2024, 1, 1, tzinfo=timezone.utc),
    }
    defaults.update(kwargs)
    return LearningEntry(**defaults)


def test_append_learning_creates_file(vague_home):
    entry = _make_entry()
    append_learning("test-slug", entry)
    path = vague_home / "projects" / "test-slug" / "learnings.md"
    assert path.exists()


def test_search_learnings_returns_appended(vague_home):
    entry = _make_entry(key="my-key", insight="My insight")
    append_learning("test-slug", entry)
    results = search_learnings("test-slug")
    assert len(results) == 1
    assert results[0].key == "my-key"


def test_search_learnings_deduplicates_by_key_type_keeps_latest(vague_home):
    old = _make_entry(
        key="dup-key",
        insight="Old insight",
        ts=datetime(2024, 1, 1, tzinfo=timezone.utc),
    )
    new = _make_entry(
        key="dup-key",
        insight="New insight",
        ts=datetime(2024, 6, 1, tzinfo=timezone.utc),
    )
    append_learning("test-slug", old)
    append_learning("test-slug", new)
    results = search_learnings("test-slug")
    assert len(results) == 1
    assert results[0].insight == "New insight"


def test_search_learnings_type_filter(vague_home):
    append_learning("test-slug", _make_entry(key="k1", type="pitfall"))
    append_learning("test-slug", _make_entry(key="k2", type="pattern"))
    results = search_learnings("test-slug", type_filter="pitfall")
    assert len(results) == 1
    assert results[0].type == "pitfall"


def test_get_top_learnings_returns_all_when_lte_5(vague_home):
    for i in range(3):
        append_learning("test-slug", _make_entry(key=f"key-{i}", confidence=i + 5))
    results = get_top_learnings("test-slug", n=3)
    assert len(results) == 3


def test_get_top_learnings_returns_top_3_when_gt_5(vague_home):
    for i in range(8):
        append_learning("test-slug", _make_entry(key=f"key-{i}", confidence=i + 1))
    results = get_top_learnings("test-slug", n=3)
    assert len(results) == 3
    # Should return highest confidence
    confidences = [e.confidence for e in results]
    assert all(c >= 6 for c in confidences)


def test_prune_to_500_on_write(vague_home):
    for i in range(510):
        entry = _make_entry(key=f"key-{i}", confidence=(i % 10) + 1)
        append_learning("test-slug", entry)

    from vague.sdk.core.learnings import _read_entries, _get_learnings_path
    path = _get_learnings_path("test-slug")
    entries = _read_entries(path)
    assert len(entries) <= 500
