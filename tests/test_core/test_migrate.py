"""Tests for `vague migrate`: old per-project stores into the global ledger and events."""

from __future__ import annotations

import json

from typer.testing import CliRunner

from vague.sdk.cli import sdk_app
from vague.sdk.core.memory import read_lines

runner = CliRunner()

SUMMARY = (
    "learnings 3 → 3 lines · observations 2 → 2 lines · timeline 2 → 2 events · "
    "project.md 2 → 2 events · principles 0 · planning 0"
)


def _events(home, month: str) -> list[dict]:
    path = home / "events" / f"{month}.jsonl"
    return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []


def _by_key(home) -> dict:
    return {m.key: m for m in read_lines(path=home / "memory.jsonl")}


def test_dry_run_writes_nothing_and_prints_summary(old_stores, snapshot):
    before = snapshot(old_stores)
    result = runner.invoke(sdk_app, ["migrate", "--dry-run"])
    assert result.exit_code == 0, result.output
    assert SUMMARY in result.output
    assert snapshot(old_stores) == before


def test_dry_run_lists_remaps_dropped_fields_and_long_texts(old_stores):
    result = runner.invoke(sdk_app, ["migrate", "--dry-run"])
    assert "ship → dev-ship" in result.output
    assert "investigate → dev-investigate" in result.output
    assert "bastien → Obsidian" in result.output
    for field in ("confidence", "type", "source", "session", "outcome"):
        assert field in result.output
    assert "o-r/long-one (650 chars)" in result.output


def test_migrate_writes_learning_lines_with_remapped_skill_and_scope(old_stores):
    result = runner.invoke(sdk_app, ["migrate"])
    assert result.exit_code == 0, result.output
    memories = _by_key(old_stores)
    docker = memories["tests-need-docker"]
    assert (docker.scope, docker.kind, docker.skill) == ("o-r", "learning", "dev-ship")
    assert docker.text == "Run tests in docker."
    assert docker.files == ["Taskfile.yml"]
    assert docker.ts.isoformat() == "2026-09-01T10:00:00+00:00"
    assert memories["review-evidence"].scope == "Obsidian"
    # Kept whole: the 600-character cap is lifted for migration only.
    assert memories["long-one"].text == "x" * 650
    assert memories["long-one"].skill == "review"


def test_migrate_writes_observation_lines_with_key_text_and_status(old_stores):
    runner.invoke(sdk_app, ["migrate"])
    memories = _by_key(old_stores)
    first, second = memories["obs-o-r-1"], memories["obs-o-r-2"]
    assert (first.scope, first.kind, first.skill, first.status) == ("global", "observation", "dev-investigate",
                                                                    "active")
    assert first.text == "Skips repro → Add a repro step (evidence first)"
    assert (second.skill, second.status) == ("vault", "actioned")


def test_migrate_leaves_old_files_byte_identical(old_stores, snapshot):
    before = snapshot(old_stores / "projects")
    runner.invoke(sdk_app, ["migrate"])
    assert snapshot(old_stores / "projects") == before


def test_migrate_second_run_writes_nothing(old_stores, snapshot):
    runner.invoke(sdk_app, ["migrate"])
    assert (old_stores / ".migrated").exists()
    before = snapshot(old_stores)
    result = runner.invoke(sdk_app, ["migrate"])
    assert result.exit_code == 0
    assert "already migrated" in result.output
    assert snapshot(old_stores) == before


def test_migrate_writes_timeline_and_project_events_in_monthly_files(old_stores, tmp_path):
    runner.invoke(sdk_app, ["migrate"])
    september, october, august = (_events(old_stores, m) for m in ("2026-09", "2026-10", "2026-08"))
    live = str(tmp_path / "live-repo")

    assert len(september) == 1
    ship = september[0]
    assert (ship["event"], ship["source"], ship["skill"], ship["session"]) == ("skill_start", "migrated",
                                                                             "dev-ship", "s1")
    assert (ship["repo"], ship["branch"], ship["main_root"], ship["runtime"]) == ("o-r", "main", live, "migrated")

    develop, project = sorted(october, key=lambda e: e["ts"])
    assert (develop["skill"], develop["session"], develop["branch"]) == ("dev-develop", "migrated", "feat")
    assert "skill" not in project
    assert (project["cwd"], project["root"], project["main_root"]) == (live, live, live)
    assert (project["branch"], project["ts"]) == ("unknown", "2026-10-07T10:00:00Z")

    assert [e["main_root"] for e in august] == ["/nonexistent/bastien"]
    assert august[0]["repo"] == "bastien"


def test_archive_refuses_without_marker(old_stores, snapshot):
    before = snapshot(old_stores)
    result = runner.invoke(sdk_app, ["migrate", "--archive"])
    assert result.exit_code == 1
    assert "vague migrate" in result.output
    assert snapshot(old_stores) == before


def test_archive_moves_old_stores_and_keeps_designs(old_stores):
    runner.invoke(sdk_app, ["migrate"])
    (old_stores / "projects" / "o-r" / "planning").mkdir()
    (old_stores / "projects" / "o-r" / "planning" / "state.md").write_text("---\n---\n")
    result = runner.invoke(sdk_app, ["migrate", "--archive"])
    assert result.exit_code == 0, result.output

    [archive_day] = (old_stores / "archive").iterdir()
    moved = archive_day / "projects" / "o-r"
    for name in ("learnings.md", "observations.md", "timeline.md", "project.md", "learnings.md.lock",
                 "planning/state.md"):
        assert (moved / name).exists(), name
        assert not (old_stores / "projects" / "o-r" / name).exists(), name
    assert (archive_day / "projects" / "bastien" / "learnings.md").exists()
    assert (old_stores / "projects" / "o-r" / "designs" / "plan.md").exists()
    assert (old_stores / "projects" / "o-r" / "diagrams" / "map.html").exists()
    assert (old_stores / "memory.jsonl").exists()
