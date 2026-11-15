"""Tests for vague/status.py."""

import json

from typer.testing import CliRunner

from vague.cli import app

runner = CliRunner()


def test_status_empty_home(vague_home):
    result = runner.invoke(app, ["status"])
    assert result.exit_code == 0
    assert "No projects yet" in result.output


def test_status_json_empty(vague_home):
    result = runner.invoke(app, ["status", "--json"])
    assert result.exit_code == 0
    assert json.loads(result.output) == []


def test_context_skill_writes_no_project_meta(vague_home, git_repo, monkeypatch):
    monkeypatch.chdir(git_repo)
    result = runner.invoke(app, ["context", "--shell", "--skill", "dev-ship"])
    assert result.exit_code == 0
    assert "SLUG=" in result.output
    assert not (vague_home / "projects").exists()


def _event(home, repo, ts, main_root="", skill=None, event="skill_start"):
    """One event line, written the way the hook writes it."""
    from datetime import datetime

    from vague.events import Event, append_event

    append_event(event=Event(
        ts=datetime.fromisoformat(ts), session="s", event=event, cwd=main_root, repo=repo, branch="main",
        root=main_root, main_root=main_root, is_worktree=False, runtime="claude", skill=skill,
        source="tool" if skill else None,
    ))


def _rows():
    result = runner.invoke(app, ["status", "--json"])
    assert result.exit_code == 0, result.output
    return {r["slug"]: r for r in json.loads(result.output)}


def test_status_rows_live_stale_and_unknown_from_events(vague_home, git_repo):
    _event(vague_home, repo="repo", ts="2026-10-01T10:00:00+00:00", main_root=str(git_repo), skill="dev-ship")
    _event(vague_home, repo="gone-project", ts="2026-09-01T10:00:00+00:00", main_root="/nonexistent/repo")
    _event(vague_home, repo="pathless", ts="2026-08-01T10:00:00+00:00", event="context_read")

    rows = _rows()
    assert rows["repo"]["path_state"] == "live"
    assert rows["repo"]["path"] == str(git_repo)
    assert rows["repo"]["branch"]
    assert rows["repo"]["dirty"] is False
    assert rows["gone-project"]["path_state"] == "stale"
    assert rows["gone-project"]["branch"] is None
    assert rows["pathless"]["path_state"] == "unknown"
    assert list(rows) == ["repo", "gone-project", "pathless"]


def test_status_uses_latest_event_for_path_and_activity(vague_home, tmp_path):
    old, new = tmp_path / "old", tmp_path / "new"
    new.mkdir()
    _event(vague_home, repo="moved", ts="2026-09-01T10:00:00+00:00", main_root=str(old), skill="plan-eng")
    _event(vague_home, repo="moved", ts="2026-11-02T10:00:00+00:00", main_root=str(new), skill="dev-develop")
    _event(vague_home, repo="moved", ts="2026-11-03T10:00:00+00:00", event="context_read")

    row = _rows()["moved"]
    assert row["path"] == str(new)
    assert row["last_seen"].startswith("2026-11-03T10:00:00")
    assert row["last_event"]["skill"] == "dev-develop"


def test_inflight_designs_counts_doc_memories(vague_home, make_memory):
    from datetime import datetime

    from vague.memory import append_memory

    _event(vague_home, repo="planned", ts="2026-10-01T10:00:00+00:00", skill="dev-ship")

    def doc(key, ts, **over):
        fields = {"scope": "planned", "key": key, "kind": "doc", "skill": "plan-eng", "files": ["/p.md"],
                  "ts": datetime.fromisoformat(ts), **over}
        append_memory(memory=make_memory(**fields))

    doc(key="eng-plan-old", ts="2026-09-01T00:00:00+00:00")
    doc(key="eng-plan-feat-a", ts="2026-10-02T00:00:00+00:00")
    doc(key="eng-plan-feat-b", ts="2026-10-03T00:00:00+00:00")
    doc(key="eng-plan-feat-b", ts="2026-10-04T00:00:00+00:00")
    doc(key="ceo-plan", ts="2026-10-02T00:00:00+00:00", skill="plan-ideation")
    doc(key="fact", ts="2026-10-02T00:00:00+00:00", kind="learning")
    doc(key="dropped", ts="2026-10-02T00:00:00+00:00")
    doc(key="dropped", ts="2026-10-05T00:00:00+00:00", text=None, status="forgotten")
    doc(key="elsewhere", ts="2026-10-02T00:00:00+00:00", scope="other")
    designs = vague_home / "projects" / "planned" / "designs"
    designs.mkdir(parents=True)
    (designs / "stray.md").write_text("# not counted")

    assert _rows()["planned"]["inflight_designs"] == 2


def test_status_counts_active_memories_for_scope(vague_home, make_memory):
    from vague.memory import append_memory

    _event(vague_home, repo="o-r", ts="2026-10-01T10:00:00+00:00")
    append_memory(memory=make_memory(key="a"))
    append_memory(memory=make_memory(key="b"))
    append_memory(memory=make_memory(key="b", text=None, status="forgotten"))
    append_memory(memory=make_memory(key="c", scope="other"))

    assert _rows()["o-r"]["memories"] == 1


def test_status_table_shows_memories_column(vague_home, make_memory):
    from vague.memory import append_memory

    _event(vague_home, repo="o-r", ts="2026-10-01T10:00:00+00:00", skill="plan-eng")
    append_memory(memory=make_memory(key="a"))
    result = runner.invoke(app, ["status"])
    assert result.exit_code == 0
    assert "o-r" in result.output
    assert "Memories" in result.output
    assert "plan-eng" in result.output


def test_status_lists_ledger_scopes_without_events_but_not_global(vague_home, make_memory):
    from vague.memory import append_memory

    _event(vague_home, repo="o-r", ts="2026-10-01T10:00:00+00:00", main_root="/nonexistent/o-r")
    append_memory(memory=make_memory(scope="Obsidian", key="a"))
    append_memory(memory=make_memory(scope="global", key="g"))

    rows = _rows()
    assert list(rows) == ["o-r", "Obsidian"]
    assert rows["Obsidian"]["memories"] == 1
    assert rows["Obsidian"]["path"] is None and rows["Obsidian"]["path_state"] == "unknown"
    assert rows["Obsidian"]["last_seen"] is None


def test_status_table_shows_path_column(vague_home, make_memory):
    from vague.memory import append_memory

    _event(vague_home, repo="o-r", ts="2026-10-01T10:00:00+00:00", main_root="/srv/o-r")
    append_memory(memory=make_memory(scope="Obsidian", key="a"))
    result = runner.invoke(app, ["status"])
    assert result.exit_code == 0
    assert "Path" in result.output and "/srv/o-r" in result.output
    (obsidian,) = [line for line in result.output.splitlines() if "Obsidian" in line]
    assert " - " in obsidian
