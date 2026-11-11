"""Local web server for `vague ui`: the page, the graph JSON, and an "open this file" action.

Binds to 127.0.0.1 only. Nothing leaves the machine, matching docs/telemetry.md.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib import resources
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from vague.sdk.core.events import read_events
from vague.sdk.core.graph import activity_by_day, build_graph, skill_usage
from vague.sdk.core.logging import get_logger
from vague.sdk.core.memory import load_ledger


def _page() -> bytes:
    return resources.files("vague").joinpath("assets/ui/index.html").read_bytes()


def _day(value: str | None) -> datetime | None:
    """`YYYY-MM-DD` as UTC midnight. A malformed value means no bound, not an error page."""
    try:
        return datetime.strptime(value or "", "%Y-%m-%d").replace(tzinfo=UTC)
    except ValueError:
        return None


def vault_root() -> str:
    """Where the Obsidian vault lives, so files written there are flagged. Skills assume ~/Obsidian too."""
    # Not resolved through symlinks: stored paths keep the spelling a skill used, `$HOME/Obsidian/...`.
    return os.path.normpath(os.environ.get("VAGUE_VAULT") or Path.home() / "Obsidian")


def graph_payload(since: str | None = None, until: str | None = None) -> dict:
    """Fresh payload per request: the logs are small and the page wants live data.

    `activity` ignores the range on purpose: it is the histogram the range is picked from.
    """
    events = read_events()
    memories = [m.model_dump(mode="json") for m in load_ledger()]
    start, end = _day(since), _day(until)
    graph = build_graph(events=events, memories=memories, since=start, until=end, vault_root=vault_root())
    for node in graph["nodes"]:
        if node["type"] == "file":
            node["exists"] = bool(node.get("path")) and Path(node["path"]).exists()
    graph["skills"] = skill_usage(events=events, since=start, until=end)
    graph["activity"] = activity_by_day(events=events, memories=memories)
    return graph


def _launch(argv: list[str]) -> None:
    subprocess.Popen(argv, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def _opener(path: str, reveal: bool) -> list[str]:
    if sys.platform == "darwin":
        return ["open", "-R", path] if reveal else ["open", path]
    return ["xdg-open", str(Path(path).parent if reveal else path)]


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args) -> None:  # noqa: A002 - signature fixed by the base class
        get_logger().debug("ui: " + format, *args)

    def _send(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, status: int, data: dict) -> None:
        self._send(status, json.dumps(data).encode(), "application/json")

    def do_GET(self) -> None:  # noqa: N802
        url = urlparse(self.path)
        if url.path == "/":
            self._send(200, _page(), "text/html; charset=utf-8")
        elif url.path == "/api/graph":
            query = parse_qs(url.query)
            self._json(200, graph_payload(since=query.get("since", [None])[0], until=query.get("until", [None])[0]))
        else:
            self._json(404, {"error": "not found"})

    def do_POST(self) -> None:  # noqa: N802
        if urlparse(self.path).path != "/api/open":
            return self._json(404, {"error": "not found"})
        # A web page on another origin could otherwise make this browser open files on this machine.
        origin = self.headers.get("Origin")
        if origin and origin != f"http://{self.headers.get('Host')}":
            return self._json(403, {"error": "foreign origin"})
        try:
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
        except ValueError:
            return self._json(400, {"error": "bad json"})
        path = body.get("path") if isinstance(body, dict) else None
        # Only files the graph lists: the endpoint is not a general "open anything" door.
        known = {n["path"] for n in graph_payload()["nodes"] if n["type"] == "file" and n.get("path")}
        if path not in known or not Path(path).exists():
            return self._json(403, {"error": "path is not a known, existing file"})
        _launch(_opener(path=path, reveal=bool(body.get("reveal"))))
        self._json(200, {"ok": True})


def make_server(port: int = 8765) -> ThreadingHTTPServer:
    return ThreadingHTTPServer(("127.0.0.1", port), Handler)
