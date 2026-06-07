"""Tests for core/observations.py"""

from datetime import UTC, datetime

from vague.models import ObservationEntry
from vague.sdk.core.observations import (
    append_observation,
    list_observations,
    next_observation_id,
    update_observation_status,
)


def _make_entry(**kwargs):
    defaults = {
        "id": 1,
        "skill": "dev-ship",
        "type": "improvement",
        "issue": "Test issue",
        "suggestion": "Test suggestion",
        "principle": "Test principle",
        "status": "open",
        "source_skill": "dev-ship",
        "session": "test-session",
        "ts": datetime(2026, 5, 1, tzinfo=UTC),
    }
    defaults.update(kwargs)
    return ObservationEntry(**defaults)


def test_append_creates_file(vague_home):
    append_observation("test-slug", _make_entry())
    path = vague_home / "projects" / "test-slug" / "observations.md"
    assert path.exists()


def test_list_returns_appended(vague_home):
    append_observation("test-slug", _make_entry(id=1, issue="First issue"))
    results = list_observations("test-slug")
    assert len(results) == 1
    assert results[0].issue == "First issue"


def test_list_filters_by_status(vague_home):
    append_observation("test-slug", _make_entry(id=1, status="open"))
    append_observation("test-slug", _make_entry(id=2, status="actioned"))
    append_observation("test-slug", _make_entry(id=3, status="open"))

    open_results = list_observations("test-slug", status_filter="open")
    assert len(open_results) == 2

    actioned_results = list_observations("test-slug", status_filter="actioned")
    assert len(actioned_results) == 1


def test_update_status(vague_home):
    append_observation("test-slug", _make_entry(id=1, status="open"))
    found = update_observation_status("test-slug", obs_id=1, new_status="actioned")
    assert found is True

    results = list_observations("test-slug")
    assert results[0].status == "actioned"


def test_update_status_not_found(vague_home):
    append_observation("test-slug", _make_entry(id=1))
    found = update_observation_status("test-slug", obs_id=99, new_status="actioned")
    assert found is False


def test_next_id_empty(vague_home):
    assert next_observation_id("test-slug") == 1


def test_next_id_increments(vague_home):
    append_observation("test-slug", _make_entry(id=1))
    append_observation("test-slug", _make_entry(id=2))
    assert next_observation_id("test-slug") == 3


def test_next_id_handles_gaps(vague_home):
    append_observation("test-slug", _make_entry(id=1))
    append_observation("test-slug", _make_entry(id=5))
    assert next_observation_id("test-slug") == 6


def test_multiple_skills(vague_home):
    append_observation("test-slug", _make_entry(id=1, skill="dev-ship"))
    append_observation("test-slug", _make_entry(id=2, skill="dev-review"))
    append_observation("test-slug", _make_entry(id=3, skill="dev-ship"))

    results = list_observations("test-slug")
    assert len(results) == 3


def test_list_empty_returns_empty(vague_home):
    results = list_observations("test-slug")
    assert results == []
