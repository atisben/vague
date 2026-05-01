"""Tests for core/principles.py"""

import pytest

from vague.models import PrincipleEntry
from vague.sdk.core.principles import (
    append_principle,
    list_principles,
    update_principle_status,
)


def _make_principle(**kwargs):
    defaults = {
        "id": 1,
        "title": "Pre-flight verification",
        "requirement": "Every skill with rules must include a verification step",
        "applies_to": "all",
        "propagation": "opportunistic",
        "status": "active",
        "added": "2026-05-01",
    }
    defaults.update(kwargs)
    return PrincipleEntry(**defaults)


def test_append_creates_file(vague_home):
    append_principle("test-slug", _make_principle())
    path = vague_home / "projects" / "test-slug" / "principles.md"
    assert path.exists()


def test_list_returns_appended(vague_home):
    append_principle("test-slug", _make_principle(id=1, title="P1"))
    results = list_principles("test-slug")
    assert len(results) == 1
    assert results[0].title == "P1"


def test_list_filters_by_status(vague_home):
    append_principle("test-slug", _make_principle(id=1, status="active"))
    append_principle("test-slug", _make_principle(id=2, status="retired"))

    active = list_principles("test-slug", status_filter="active")
    assert len(active) == 1

    retired = list_principles("test-slug", status_filter="retired")
    assert len(retired) == 1

    all_principles = list_principles("test-slug", status_filter=None)
    assert len(all_principles) == 2


def test_update_status(vague_home):
    append_principle("test-slug", _make_principle(id=1, status="active"))
    found = update_principle_status("test-slug", principle_id=1, new_status="retired")
    assert found is True

    results = list_principles("test-slug", status_filter="retired")
    assert len(results) == 1


def test_update_status_not_found(vague_home):
    append_principle("test-slug", _make_principle(id=1))
    found = update_principle_status("test-slug", principle_id=99, new_status="retired")
    assert found is False


def test_list_empty_returns_empty(vague_home):
    results = list_principles("test-slug")
    assert results == []
