"""Tests for vague/ui_server.py."""

import json
import re
import threading
import urllib.error
import urllib.request
from importlib import resources

import pytest

from vague import ui_server


@pytest.fixture
def server(vague_home, monkeypatch, tmp_path):
    repo = tmp_path / "repo"
    (repo / "src").mkdir(parents=True)
    (repo / "src" / "a.py").write_text("x = 1\n")
    (vague_home / "memory.jsonl").write_text(json.dumps({
        "ts": "2026-11-11T10:05:00Z", "scope": "me-repo", "key": "k", "kind": "learning", "text": "t",
        "files": ["src/a.py"], "skill": "dev-ship", "status": "active",
    }) + "\n")
    (vague_home / "events").mkdir()
    (vague_home / "events" / "2026-11.jsonl").write_text(json.dumps({
        "ts": "2026-11-11T10:00:00Z", "session": "s", "event": "skill_start", "cwd": str(repo), "repo": "me-repo",
        "branch": "main", "root": str(repo), "main_root": str(repo), "is_worktree": False, "runtime": "claude",
        "skill": "dev-ship", "source": "tool",
    }) + "\n")
    opened: list[list[str]] = []
    monkeypatch.setattr(ui_server, "_launch", lambda argv: opened.append(argv))

    httpd = ui_server.make_server(port=0)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{httpd.server_port}", opened, repo
    httpd.shutdown()


def _post(url, body, origin=None):
    headers = {"Content-Type": "application/json"}
    if origin:
        headers["Origin"] = origin
    request = urllib.request.Request(url, data=json.dumps(body).encode(), headers=headers, method="POST")
    return urllib.request.urlopen(request)


def test_root_serves_the_html_page(server):
    base, _, _ = server

    body = urllib.request.urlopen(base + "/").read().decode()

    assert "<title>vague" in body


def test_graph_endpoint_returns_nodes_and_links(server):
    base, _, _ = server

    graph = json.load(urllib.request.urlopen(base + "/api/graph"))

    assert {n["type"] for n in graph["nodes"]} == {"project", "branch", "memory", "file"}
    assert graph["links"]


def test_graph_endpoint_reports_global_skill_usage_and_activity(server):
    base, _, _ = server

    payload = json.load(urllib.request.urlopen(base + "/api/graph"))

    assert [(u["skill"], u["count"]) for u in payload["skills"]] == [("dev-ship", 1)]
    assert payload["activity"] == [{"day": "2026-11-11", "count": 2}]


def test_graph_endpoint_filters_by_date(server):
    base, _, _ = server

    payload = json.load(urllib.request.urlopen(base + "/api/graph?until=2026-11-01"))

    assert payload["nodes"] == []
    assert payload["skills"] == []
    assert payload["activity"]


def test_graph_endpoint_ignores_a_malformed_date(server):
    base, _, _ = server

    payload = json.load(urllib.request.urlopen(base + "/api/graph?since=garbage"))

    assert payload["nodes"]


def _append_event(vague_home, **fields):
    row = {
        "session": "s", "cwd": "/x", "repo": "me-repo", "branch": "main", "root": "/x", "main_root": "/x",
        "is_worktree": False, "runtime": "claude", **fields,
    }
    with (vague_home / "events" / "2026-11.jsonl").open("a") as handle:
        handle.write(json.dumps(row) + "\n")


def test_runs_endpoint_lists_each_run_with_the_memories_it_was_served(server, vague_home):
    base, _, repo = server
    _append_event(vague_home, ts="2026-11-11T10:00:05Z", event="context_read", command="context", ids=["me-repo/k"])
    _append_event(
        vague_home, ts="2026-11-11T10:01:00Z", event="file_write", skill="dev-ship",
        path=str(repo / "src" / "a.py"), root=str(repo),
    )

    payload = json.load(urllib.request.urlopen(base + "/api/runs"))

    (run,) = payload["runs"]
    assert run["skill"] == "dev-ship"
    assert run["served"] == [{"id": "me-repo/k", "count": 1}]
    assert payload["memories"]["me-repo/k"]["text"] == "t"
    assert run["files"][0]["exists"] is True


def test_graph_marks_file_existence(server):
    base, _, _ = server

    graph = json.load(urllib.request.urlopen(base + "/api/graph"))

    (file_node,) = [n for n in graph["nodes"] if n["type"] == "file"]
    assert file_node["exists"] is True


def test_graph_flags_files_a_skill_wrote_in_the_vault(server, vague_home, monkeypatch, tmp_path):
    base, opened, _ = server
    vault = tmp_path / "Obsidian"
    (vault / "6. Atomic Notes").mkdir(parents=True)
    note = vault / "6. Atomic Notes" / "Note.md"
    note.write_text("x")
    monkeypatch.setenv("VAGUE_VAULT", str(vault))
    with (vague_home / "memory.jsonl").open("a") as ledger:
        ledger.write(json.dumps({
            "ts": "2026-11-11T11:00:00Z", "scope": "me-repo", "key": "vault-note", "kind": "learning",
            "text": "Saved Note.", "files": [str(note)], "skill": "vault", "status": "active",
        }) + "\n")

    graph = json.load(urllib.request.urlopen(base + "/api/graph"))

    (vault_file,) = [n for n in graph["nodes"] if n["type"] == "file" and n["area"] == "vault"]
    found = (vault_file["relative"], vault_file["skill"], vault_file["exists"])
    assert found == ("6. Atomic Notes/Note.md", "vault", True)
    _post(base + "/api/open", {"path": str(note)}, origin=base)
    assert opened


def test_open_launches_a_file_the_graph_knows(server):
    base, opened, repo = server

    _post(base + "/api/open", {"path": str(repo / "src" / "a.py")}, origin=base)

    assert opened and opened[0][-1] == str(repo / "src" / "a.py")


def test_open_refuses_a_path_outside_the_graph(server):
    base, opened, _ = server

    with pytest.raises(urllib.error.HTTPError) as error:
        _post(base + "/api/open", {"path": "/etc/passwd"}, origin=base)

    assert error.value.code == 403
    assert opened == []


def test_open_refuses_a_foreign_origin(server):
    base, opened, repo = server

    with pytest.raises(urllib.error.HTTPError) as error:
        _post(base + "/api/open", {"path": str(repo / "src" / "a.py")}, origin="http://evil.example")

    assert error.value.code == 403
    assert opened == []


def test_unknown_route_is_404(server):
    base, _, _ = server

    with pytest.raises(urllib.error.HTTPError) as error:
        urllib.request.urlopen(base + "/nope")

    assert error.value.code == 404


@pytest.fixture(scope="module")
def page() -> str:
    return resources.files("vague").joinpath("assets/ui/index.html").read_text(encoding="utf-8")


def test_sidebar_lists_obsidian_writes_before_projects_and_skills(page):
    assert page.index('id="h-vault"') < page.index('id="h-projects"') < page.index('id="h-skills"')


def test_vault_stays_reachable_when_the_sidebar_collapses(page):
    narrow_rules = page.split("@media (max-width: 760px)")[1].split("@media (prefers-reduced-motion")[0]

    assert not re.search(r"aside\s*\{[^}]*display:\s*none", narrow_rules)
    assert 'id="vault-badge"' in page


def test_sidebar_rows_are_buttons_not_clickable_divs(page):
    assert 'el("button", { type: "button", className: "chip"' in page
    assert 'el("button", { type: "button", className: "vf"' in page
    assert 'el("a",' not in page


def test_keyboard_focus_has_a_themed_ring(page):
    assert re.search(r":focus-visible\s*\{[^}]*outline:[^}]*var\(--accent\)", page)


def test_motion_has_a_reduced_motion_path(page):
    assert "@media (prefers-reduced-motion: reduce)" in page
    assert "REDUCED.matches" in page


def test_native_controls_follow_the_theme(page):
    assert re.search(r":root\s*\{[^}]*color-scheme:\s*light dark", page)
    assert "::selection" in page
    assert "caret-color" in page


def test_failed_load_names_the_problem_and_offers_a_retry(page):
    assert "Can't reach the vague server" in page
    assert 'id="retry"' in page
    assert 'id="banner-retry"' in page


def test_toast_is_announced_to_screen_readers(page):
    assert re.search(r'id="toast"[^>]*aria-live="polite"', page)


def test_search_has_a_label_and_a_results_list(page):
    assert re.search(r'<label[^>]*for="q"', page)
    assert 'id="results"' in page


def test_labels_are_not_uppercase_eyebrows(page):
    assert "text-transform: uppercase" not in page


def test_colour_has_one_meaning_per_channel(page):
    assert "EXT_HUE" not in page
    assert "#2563eb" not in page


def test_legend_uses_the_shapes_the_canvas_draws(page):
    assert "function glyph(" in page
    assert not set("●▪▣○◐") & set(page)


def test_canvas_labels_are_placed_without_overlap(page):
    assert "function drawLabels(" in page
    assert re.search(r"placed\.some\(", page)


def test_project_hues_are_capped_below_electric_saturation(page):
    assert re.search(r"hsla\(\$\{h\},(\d+)%", page)
    assert int(re.search(r"hsla\(\$\{h\},(\d+)%", page).group(1)) <= 40


def test_timeline_spends_accent_only_on_hover_and_brush(page):
    in_range_rule = re.search(r"#hist i\.in\s*\{([^}]*)\}", page).group(1)

    assert "--accent" not in in_range_rule
    assert re.search(r"#hist\.brushing i\.in[^{]*\{[^}]*var\(--accent\)", page)


def test_layer_toggles_move_onto_the_canvas_on_narrow_screens(page):
    assert "function placeLayers()" in page
    assert 'id="viewctl"' in page


def test_keyboard_shortcuts_are_listed_in_the_page(page):
    assert 'id="keys"' in page
    assert 'id="keys-btn"' in page


def test_page_offers_live_history_graph_and_guide_tabs(page):
    tabs = re.findall(r'role="tab" id="tab-(\w+)"', page)

    assert tabs == ["live", "history", "graph", "guide"]
    assert 'addEventListener("hashchange"' in page


def test_run_views_read_runs_from_the_runs_endpoint(page):
    assert 'fetch("/api/runs")' in page
    assert page.index('id="runs-pane"') < page.index('id="graph-pane"')


def test_run_list_opens_from_the_sheet_on_narrow_screens(page):
    assert 'className: "btn open-runs"' in page
    assert '.closest("aside, #vault-badge, .open-runs")' in page
