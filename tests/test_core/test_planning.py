"""Tests for core/planning.py"""

import pytest
from vague.sdk.core.planning import get_state, set_state, list_plans, get_plan_status, complete_plan
from vague.sdk.core.frontmatter import write_md


def test_set_and_get_state(vague_home):
    set_state("my-slug", "phase", "alpha")
    value = get_state("my-slug", "phase")
    assert value == "alpha"


def test_get_state_missing_key(vague_home):
    value = get_state("my-slug", "nonexistent")
    assert value is None


def test_list_plans_empty(vague_home):
    plans = list_plans("my-slug", "phase-1")
    assert plans == []


def test_list_plans_with_files(vague_home):
    phase_dir = vague_home / "projects" / "my-slug" / "planning" / "phases" / "phase-1"
    phase_dir.mkdir(parents=True)
    write_md(phase_dir / "plan-a.md", {"title": "Plan A", "status": "pending"})
    plans = list_plans("my-slug", "phase-1")
    assert len(plans) == 1
    assert plans[0]["title"] == "Plan A"


def test_complete_plan(vague_home):
    phase_dir = vague_home / "projects" / "my-slug" / "planning" / "phases" / "phase-1"
    phase_dir.mkdir(parents=True)
    write_md(phase_dir / "plan-a.md", {"title": "Plan A", "status": "pending"})
    complete_plan("my-slug", "plan-a")
    status = get_plan_status("my-slug", "plan-a")
    assert status["status"] == "completed"
