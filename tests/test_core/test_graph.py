"""The usage graph: events and memories folded into nodes and links for the UI."""

from datetime import UTC, datetime

from vague.sdk.core.graph import activity_by_day, build_graph, skill_usage

NOW = datetime(2026, 11, 11, 12, 0, tzinfo=UTC)


def _event(**over):
    base = {
        "ts": "2026-11-11T10:00:00Z", "session": "s1", "event": "skill_start", "cwd": "/r", "repo": "me-repo",
        "branch": "feat/x", "root": "/r", "main_root": "/r", "is_worktree": False, "runtime": "claude",
        "skill": "dev-ship", "source": "tool",
    }
    return {**base, **over}


def _memory(**over):
    base = {
        "ts": "2026-11-11T10:05:00Z", "scope": "me-repo", "key": "tests-need-docker", "kind": "learning",
        "text": "Run docker first.", "files": [], "skill": None, "status": "active",
    }
    return {**base, **over}


def _ids(graph, kind):
    return {n["id"] for n in graph["nodes"] if n["type"] == kind}


def _links(graph, kind):
    return {(link["source"], link["target"]) for link in graph["links"] if link["kind"] == kind}


def test_skills_are_not_graph_nodes():
    graph = build_graph(events=[_event()], memories=[_memory(skill="dev-ship")])

    assert _ids(graph, "skill") == set()


def test_skill_start_links_project_to_branch():
    graph = build_graph(events=[_event()], memories=[])

    assert _ids(graph, "project") == {"project:me-repo"}
    assert _links(graph, "has_branch") == {("project:me-repo", "branch:me-repo:feat/x")}


def test_memory_attaches_to_its_project():
    graph = build_graph(events=[_event()], memories=[_memory()])

    assert _links(graph, "has_memory") == {("project:me-repo", "memory:me-repo/tests-need-docker")}


def test_global_scope_becomes_the_global_project():
    graph = build_graph(events=[], memories=[_memory(scope="global")])

    assert "project:global" in _ids(graph, "project")


def test_memory_files_resolve_against_the_repo_main_root():
    memory = _memory(files=["src/a.py"])
    graph = build_graph(events=[_event(main_root="/work/me-repo")], memories=[memory])

    (file_node,) = [n for n in graph["nodes"] if n["type"] == "file"]
    assert file_node["path"] == "/work/me-repo/src/a.py"
    assert file_node["label"] == "a.py"
    assert _links(graph, "touches") == {("memory:me-repo/tests-need-docker", file_node["id"])}


def test_file_without_a_known_repo_root_has_no_absolute_path():
    graph = build_graph(events=[], memories=[_memory(files=["src/a.py"])])

    (file_node,) = [n for n in graph["nodes"] if n["type"] == "file"]
    assert file_node["path"] is None


def test_forgotten_memories_are_left_out():
    graph = build_graph(events=[], memories=[_memory(status="forgotten")])

    assert _ids(graph, "memory") == set()


def test_date_range_keeps_only_memories_inside_it():
    old = _memory(key="old", ts="2026-01-01T00:00:00Z")
    new = _memory(key="new")
    graph = build_graph(events=[], memories=[old, new], since=datetime(2026, 11, 1, tzinfo=UTC))

    assert _ids(graph, "memory") == {"memory:me-repo/new"}


def test_until_is_inclusive_of_the_whole_day():
    memory = _memory(ts="2026-11-05T23:30:00Z")
    graph = build_graph(events=[], memories=[memory], until=datetime(2026, 11, 5, tzinfo=UTC))

    assert _ids(graph, "memory") == {"memory:me-repo/tests-need-docker"}


def test_until_drops_later_events():
    graph = build_graph(events=[_event()], memories=[], until=datetime(2026, 11, 10, tzinfo=UTC))

    assert _ids(graph, "project") == set()


def test_files_in_one_memory_link_to_each_other():
    memory = _memory(files=["src/a.py", "src/b.py"])
    graph = build_graph(events=[], memories=[memory])

    assert _links(graph, "co_mentioned") == {("file:me-repo:src/a.py", "file:me-repo:src/b.py")}


def test_co_mention_weight_counts_shared_memories():
    memories = [_memory(key="m1", files=["a.py", "b.py"]), _memory(key="m2", files=["b.py", "a.py"])]
    graph = build_graph(events=[], memories=memories)

    (link,) = [link for link in graph["links"] if link["kind"] == "co_mentioned"]
    assert link["weight"] == 2


def test_file_links_to_its_project():
    graph = build_graph(events=[], memories=[_memory(files=["a.py"])])

    assert _links(graph, "has_file") == {("project:me-repo", "file:me-repo:a.py")}


def test_projects_report_a_stable_color_hue():
    first = build_graph(events=[_event()], memories=[])
    second = build_graph(events=[_event()], memories=[])

    (a,) = [n for n in first["nodes"] if n["type"] == "project"]
    (b,) = [n for n in second["nodes"] if n["type"] == "project"]
    assert a["hue"] == b["hue"]
    assert 0 <= a["hue"] < 360


def test_projects_get_visibly_distinct_hues():
    slugs = ["alma-ai_ml", "atisben-crimson-silk", "atisben-vague", "purple-rain", "alma-main", "llm", "datadog"]
    graph = build_graph(events=[_event(repo=slug) for slug in slugs], memories=[])

    hues = sorted(n["hue"] for n in graph["nodes"] if n["type"] == "project")
    gaps = [b - a for a, b in zip(hues, hues[1:], strict=False)]
    assert min(gaps) >= 20


def test_hues_do_not_depend_on_event_order():
    forward = build_graph(events=[_event(repo="a"), _event(repo="b")], memories=[])
    backward = build_graph(events=[_event(repo="b"), _event(repo="a")], memories=[])

    def hues(g):
        return {n["id"]: n["hue"] for n in g["nodes"] if n["type"] == "project"}

    assert hues(forward) == hues(backward)


def test_skill_usage_counts_starts_per_skill_and_project():
    events = [_event(), _event(), _event(repo="other"), _event(skill="meta")]
    usage = skill_usage(events=events)

    top = usage[0]
    assert (top["skill"], top["count"]) == ("dev-ship", 3)
    assert top["projects"] == {"me-repo": 2, "other": 1}


def test_skill_usage_ignores_context_events_and_other_dates():
    read = _event(event="context_read", skill=None)
    old = _event(ts="2026-01-01T00:00:00Z")
    usage = skill_usage(events=[read, old, _event()], since=datetime(2026, 11, 1, tzinfo=UTC))

    assert [(u["skill"], u["count"]) for u in usage] == [("dev-ship", 1)]


def test_activity_by_day_counts_skill_starts_and_memories():
    events = [_event(), _event(ts="2026-11-10T09:00:00Z")]
    days = activity_by_day(events=events, memories=[_memory()])

    assert days == [{"day": "2026-11-10", "count": 1}, {"day": "2026-11-11", "count": 2}]


def _file_node(graph):
    (node,) = [n for n in graph["nodes"] if n["type"] == "file"]
    return node


def test_absolute_file_path_is_used_as_is():
    graph = build_graph(events=[], memories=[_memory(files=["/Users/me/notes/Note.md"])])

    node = _file_node(graph)
    assert node["path"] == "/Users/me/notes/Note.md"
    assert node["label"] == "Note.md"


def test_repo_file_has_the_repo_area():
    graph = build_graph(events=[_event(main_root="/r")], memories=[_memory(files=["src/a.py"])])

    assert _file_node(graph)["area"] == "repo"


def test_file_under_the_vault_root_has_the_vault_area_and_a_vault_relative_name():
    memory = _memory(files=["/Users/me/Obsidian/6. Atomic Notes/Note.md"], skill="vault")
    graph = build_graph(events=[], memories=[memory], vault_root="/Users/me/Obsidian")

    node = _file_node(graph)
    assert node["area"] == "vault"
    assert node["relative"] == "6. Atomic Notes/Note.md"
    assert node["skill"] == "vault"


def test_absolute_file_outside_repo_and_vault_has_the_external_area():
    graph = build_graph(events=[], memories=[_memory(files=["/tmp/deck.html"])], vault_root="/Users/me/Obsidian")

    assert _file_node(graph)["area"] == "external"


def test_a_sibling_folder_with_the_vault_name_prefix_is_not_the_vault():
    graph = build_graph(events=[], memories=[_memory(files=["/Users/me/Obsidian-old/a.md"])],
                        vault_root="/Users/me/Obsidian")

    assert _file_node(graph)["area"] == "external"
