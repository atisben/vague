"""Tests for vague status and the context --skill telemetry side effect."""

import json
import os

from typer.testing import CliRunner

from vague.sdk.cli import sdk_app

runner = CliRunner()


def _chdir(path):
    os.chdir(str(path))


def test_status_empty_home(vague_home):
    result = runner.invoke(sdk_app, ["status"])
    assert result.exit_code == 0
    assert "No projects yet" in result.output


def test_status_json_empty(vague_home):
    result = runner.invoke(sdk_app, ["status", "--json"])
    assert result.exit_code == 0
    assert json.loads(result.output) == []


def test_context_skill_records_usage_and_path(vague_home, git_repo, monkeypatch):
    monkeypatch.chdir(git_repo)
    result = runner.invoke(sdk_app, ["context", "--shell", "--skill", "dev-ship"])
    assert result.exit_code == 0
    assert "SLUG=" in result.output

    usage = vague_home / "analytics" / "skill-usage.md"
    assert usage.exists()
    assert "dev-ship" in usage.read_text()

    meta = vague_home / "projects" / "repo" / "project.md"
    assert meta.exists()
    content = meta.read_text()
    assert str(git_repo) in content
    assert "last_seen" in content


def test_context_without_skill_writes_nothing(vague_home, git_repo, monkeypatch):
    monkeypatch.chdir(git_repo)
    result = runner.invoke(sdk_app, ["context", "--shell"])
    assert result.exit_code == 0
    assert not (vague_home / "analytics" / "skill-usage.md").exists()
    assert not (vague_home / "projects" / "repo" / "project.md").exists()


def test_context_skill_capture_failure_still_outputs(vague_home, git_repo, monkeypatch):
    import vague.sdk.commands.init as init_mod

    def boom(**kwargs):
        raise OSError("disk full")

    monkeypatch.chdir(git_repo)
    monkeypatch.setattr(init_mod, "record_skill_start", boom)
    monkeypatch.setattr(init_mod, "upsert_project_meta", boom)
    result = runner.invoke(sdk_app, ["context", "--shell", "--skill", "dev-ship"])
    assert result.exit_code == 0
    assert "SLUG=" in result.output


def test_status_rows_live_stale_and_unknown(vague_home, git_repo, monkeypatch):
    # live project: captured via context --skill
    monkeypatch.chdir(git_repo)
    runner.invoke(sdk_app, ["context", "--shell", "--skill", "dev-ship"])

    # stale project: recorded path no longer exists
    from vague.sdk.core.frontmatter import write_md
    stale_dir = vague_home / "projects" / "gone-project"
    write_md(stale_dir / "project.md", {"path": "/nonexistent/repo", "last_seen": "2026-01-01T00:00:00+00:00"})

    # pre-upgrade project: state but no project.md
    legacy_dir = vague_home / "projects" / "legacy-project"
    legacy_dir.mkdir(parents=True)

    result = runner.invoke(sdk_app, ["status", "--json"])
    assert result.exit_code == 0
    rows = {r["slug"]: r for r in json.loads(result.output)}

    assert rows["repo"]["path_state"] == "live"
    assert rows["repo"]["branch"]
    assert rows["repo"]["dirty"] is False

    assert rows["gone-project"]["path_state"] == "stale"
    assert rows["legacy-project"]["path_state"] == "unknown"


def test_status_counts_inflight_designs(vague_home):
    from vague.sdk.core.frontmatter import write_md

    project_dir = vague_home / "projects" / "planned-project"
    write_md(project_dir / "timeline.md", {
        "entries": [
            {"skill": "ship", "event": "completed", "branch": "main",
             "session": "s1", "outcome": "success", "ts": "2026-01-01T00:00:00Z"},
        ]
    })
    designs = project_dir / "designs"
    designs.mkdir(parents=True)
    (designs / "new-plan-eng-20260612.md").write_text("# plan")

    result = runner.invoke(sdk_app, ["status", "--json"])
    rows = {r["slug"]: r for r in json.loads(result.output)}
    assert rows["planned-project"]["inflight_designs"] == 1


def test_analytics_cap_evicts_oldest(vague_home, monkeypatch):
    from datetime import UTC, datetime

    import vague.sdk.core.analytics as analytics_mod
    from vague.models import AnalyticsEntry

    monkeypatch.setattr(analytics_mod, "MAX_ENTRIES", 3)
    for i in range(5):
        analytics_mod.append_analytics(
            AnalyticsEntry(skill=f"skill-{i}", ts=datetime.now(UTC), repo="r")
        )
    entries = analytics_mod.get_analytics("all")
    assert len(entries) == 3
    assert [e.skill for e in entries] == ["skill-2", "skill-3", "skill-4"]
