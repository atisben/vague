"""Planning state management."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from vague.sdk.core.frontmatter import read_md, update_md


def _get_planning_dir(slug: str) -> Path:
    home = Path(os.environ.get("VAGUE_HOME", Path.home() / ".vague"))
    return home / "projects" / slug / "planning"


def get_state(slug: str, key: str) -> Any:
    """Read field from planning/state.md."""
    state_path = _get_planning_dir(slug) / "state.md"
    data = read_md(state_path)
    return data.get(key)


def set_state(slug: str, key: str, value: Any) -> None:
    """Atomic update to planning/state.md."""
    state_path = _get_planning_dir(slug) / "state.md"

    def updater(data: dict) -> dict:
        data[key] = value
        return data

    update_md(state_path, updater)


def list_plans(slug: str, phase: str) -> list[dict]:
    """List PLAN.md files in phases/{phase}/, return frontmatter + path."""
    phases_dir = _get_planning_dir(slug) / "phases" / phase
    if not phases_dir.exists():
        return []

    plans = []
    for plan_file in sorted(phases_dir.glob("*.md")):
        data = read_md(plan_file)
        data["_path"] = str(plan_file)
        plans.append(data)
    return plans


def get_plan_status(slug: str, plan_id: str) -> dict:
    """Return frontmatter of PLAN.md as dict."""
    planning_dir = _get_planning_dir(slug)
    for plan_file in planning_dir.rglob(f"{plan_id}.md"):
        return read_md(plan_file)
    return {}


def complete_plan(slug: str, plan_id: str) -> None:
    """Set status=completed in PLAN.md + update roadmap.md."""
    planning_dir = _get_planning_dir(slug)
    plan_file = None
    for f in planning_dir.rglob(f"{plan_id}.md"):
        plan_file = f
        break

    if plan_file is None:
        raise FileNotFoundError(f"Plan {plan_id} not found")

    def updater(data: dict) -> dict:
        data["status"] = "completed"
        return data

    update_md(plan_file, updater)

    # Update roadmap.md
    roadmap_path = planning_dir / "roadmap.md"

    def roadmap_updater(data: dict) -> dict:
        completed = data.get("completed", [])
        if not isinstance(completed, list):
            completed = []
        if plan_id not in completed:
            completed.append(plan_id)
        data["completed"] = completed
        return data

    update_md(roadmap_path, roadmap_updater)
