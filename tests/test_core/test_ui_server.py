"""The local UI server: serves the page, the graph JSON, and opens only files the graph knows."""

import json
import threading
import urllib.error
import urllib.request

import pytest

from vague.sdk.core import ui_server


@pytest.fixture
def server(vague_home_dir, monkeypatch, tmp_path):
    repo = tmp_path / "repo"
    (repo / "src").mkdir(parents=True)
    (repo / "src" / "a.py").write_text("x = 1\n")
    (vague_home_dir / "memory.jsonl").write_text(json.dumps({
        "ts": "2026-11-11T10:05:00Z", "scope": "me-repo", "key": "k", "kind": "learning", "text": "t",
        "files": ["src/a.py"], "skill": "dev-ship", "status": "active",
    }) + "\n")
    (vague_home_dir / "events").mkdir()
    (vague_home_dir / "events" / "2026-11.jsonl").write_text(json.dumps({
        "ts": "2026-11-11T10:00:00Z", "session": "s", "event": "skill_start", "cwd": str(repo), "repo": "me-repo",
        "branch": "main", "root": str(repo), "main_root": str(repo), "is_worktree": False, "runtime": "claude",
        "skill": "dev-ship", "source": "tool",
    }) + "\n")
    monkeypatch.setenv("VAGUE_HOME", str(vague_home_dir))
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


def test_graph_marks_file_existence(server):
    base, _, _ = server

    graph = json.load(urllib.request.urlopen(base + "/api/graph"))

    (file_node,) = [n for n in graph["nodes"] if n["type"] == "file"]
    assert file_node["exists"] is True


def test_graph_flags_files_a_skill_wrote_in_the_vault(server, vague_home_dir, monkeypatch, tmp_path):
    base, opened, _ = server
    vault = tmp_path / "Obsidian"
    (vault / "6. Atomic Notes").mkdir(parents=True)
    note = vault / "6. Atomic Notes" / "Note.md"
    note.write_text("x")
    monkeypatch.setenv("VAGUE_VAULT", str(vault))
    with (vague_home_dir / "memory.jsonl").open("a") as ledger:
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
