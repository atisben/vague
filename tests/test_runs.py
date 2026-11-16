"""Tests for vague/runs.py: events grouped into agent runs with the context each one read and wrote."""

from vague.runs import agent_runs


def _event(**over):
    base = {
        "ts": "2026-11-11T10:00:00Z", "session": "s1", "event": "skill_start", "cwd": "/r", "repo": "me-repo",
        "branch": "main", "root": "/r", "main_root": "/r", "is_worktree": False, "runtime": "claude",
        "skill": "impeccable", "source": "tool",
    }
    return {**base, **over}


def _read(ts, ids, command="context", **over):
    return _event(ts=ts, event="context_read", skill=None, command=command, path="memory.jsonl", ids=ids, **over)


def _wrote(ts, ids, **over):
    return _event(ts=ts, event="context_write", skill=None, command="memory-log", path="memory.jsonl", ids=ids, **over)


def _memory(key, **over):
    base = {
        "ts": "2026-11-10T09:00:00Z", "scope": "me-repo", "key": key, "kind": "learning", "text": f"fact {key}",
        "files": [], "skill": "dev-ship", "status": "active",
    }
    return {**base, **over}


def test_a_skill_start_owns_the_reads_and_writes_until_the_next_start():
    events = [
        _event(ts="2026-11-11T10:00:00Z"),
        _read("2026-11-11T10:00:05Z", ["me-repo/a", "me-repo/b"]),
        _wrote("2026-11-11T10:03:00Z", ["me-repo/c"]),
        _event(ts="2026-11-11T10:10:00Z", skill="vault"),
        _wrote("2026-11-11T10:11:00Z", ["me-repo/d"]),
    ]

    runs = agent_runs(events=events, memories=[])["runs"]

    assert [r["skill"] for r in runs] == ["vault", "impeccable"]
    impeccable = runs[1]
    assert [s["id"] for s in impeccable["served"]] == ["me-repo/a", "me-repo/b"]
    assert [c["id"] for c in impeccable["created"]] == ["me-repo/c"]
    assert impeccable["end"] == "2026-11-11T10:03:00+00:00"


def test_sessions_never_share_a_run():
    events = [
        _event(ts="2026-11-11T10:00:00Z", session="s1"),
        _event(ts="2026-11-11T10:01:00Z", session="s2", skill="vault"),
        _read("2026-11-11T10:02:00Z", ["me-repo/a"], session="s1"),
    ]

    runs = {r["skill"]: r for r in agent_runs(events=events, memories=[])["runs"]}

    assert [s["id"] for s in runs["impeccable"]["served"]] == ["me-repo/a"]
    assert runs["vault"]["served"] == []


def test_a_memory_served_twice_in_one_run_is_listed_once_with_a_count():
    events = [
        _event(),
        _read("2026-11-11T10:00:05Z", ["me-repo/a"]),
        _read("2026-11-11T10:00:09Z", ["me-repo/a"], command="memory-search"),
    ]

    (run,) = agent_runs(events=events, memories=[])["runs"]

    assert run["served"] == [{"id": "me-repo/a", "count": 2}]


def test_context_read_before_any_skill_becomes_a_run_without_a_skill():
    events = [_read("2026-11-11T09:00:00Z", ["me-repo/a"]), _event()]

    runs = agent_runs(events=events, memories=[])["runs"]

    assert [r["skill"] for r in runs] == ["impeccable", None]


def test_steps_keep_the_order_and_the_command_of_each_event():
    events = [_event(), _read("2026-11-11T10:00:05Z", ["me-repo/a"]), _wrote("2026-11-11T10:03:00Z", ["me-repo/c"])]

    (run,) = agent_runs(events=events, memories=[])["runs"]

    assert [(s["event"], s["command"], s["ids"]) for s in run["steps"]] == [
        ("context_read", "context", ["me-repo/a"]), ("context_write", "memory-log", ["me-repo/c"]),
    ]


def test_files_a_run_wrote_are_counted_per_path_with_their_area(tmp_path):
    vault = tmp_path / "Obsidian"
    note = str(vault / "Note.md")
    events = [
        _event(),
        _event(ts="2026-11-11T10:01:00Z", event="file_write", path="/r/src/a.py"),
        _event(ts="2026-11-11T10:02:00Z", event="file_write", path="/r/src/a.py"),
        _event(ts="2026-11-11T10:03:00Z", event="file_write", path=note, agent_id="sub1"),
    ]

    (run,) = agent_runs(events=events, memories=[], vault_root=str(vault))["runs"]

    by_area = {f["area"]: f for f in run["files"]}
    assert by_area["repo"]["count"] == 2 and by_area["repo"]["relative"] == "src/a.py"
    assert by_area["vault"]["relative"] == "Note.md" and by_area["vault"]["subagent"] is True
    assert run["files"][0]["area"] == "vault"


def test_memories_named_by_runs_come_with_their_ledger_text():
    events = [_event(), _read("2026-11-11T10:00:05Z", ["me-repo/a"])]

    payload = agent_runs(events=events, memories=[_memory("a"), _memory("unrelated")])

    assert set(payload["memories"]) == {"me-repo/a"}
    assert payload["memories"]["me-repo/a"]["text"] == "fact a"


def test_a_created_memory_counts_the_later_runs_it_was_served_to():
    events = [
        _event(ts="2026-11-11T10:00:00Z"), _wrote("2026-11-11T10:01:00Z", ["me-repo/c"]),
        _event(ts="2026-11-12T10:00:00Z", session="s2"), _read("2026-11-12T10:00:05Z", ["me-repo/c"], session="s2"),
        _event(ts="2026-11-13T10:00:00Z", session="s3"), _read("2026-11-13T10:00:05Z", ["me-repo/c"], session="s3"),
    ]

    runs = agent_runs(events=events, memories=[])["runs"]

    assert runs[-1]["created"] == [{"id": "me-repo/c", "served_later": 2}]


def test_a_served_memory_names_the_run_that_last_wrote_it_before():
    events = [
        _event(ts="2026-11-11T10:00:00Z", skill="dev-ship"), _wrote("2026-11-11T10:01:00Z", ["me-repo/c"]),
        _event(ts="2026-11-12T10:00:00Z", session="s2"), _read("2026-11-12T10:00:05Z", ["me-repo/c"], session="s2"),
    ]

    runs = agent_runs(events=events, memories=[])["runs"]

    assert runs[0]["served"] == [{"id": "me-repo/c", "count": 1, "from_run": runs[1]["id"]}]
