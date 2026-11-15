"""Usage graph: events and memories folded into nodes and links for the UI.

Pure functions, no I/O: the server feeds them rows and the tests feed them dicts.

    project ─has_file──────────────▶ file ◀─co_mentioned─▶ file
        ├─has_memory─▶ memory ─touches─▶ file      (two files in one memory are related)
        └─has_branch─▶ branch

A file comes from a memory's `files` or from a `file_write` event, and carries the skill that
named or wrote it. A file with a known location is keyed on its resolved absolute path, so one
file named in a memory and written in an event is one node.

Skills are not nodes. A skill touches everything, so as a node it would pull unrelated
projects together. `skill_usage` reports them separately.
"""

from __future__ import annotations

import os
import zlib
from collections import Counter
from datetime import datetime, timedelta
from itertools import combinations
from pathlib import PurePosixPath
from typing import Any

from vague.sdk.core.events import event_ts

MIN_HUE_GAP = 24


def assign_hues(slugs: list[str]) -> dict[str, int]:
    """Stable, distinct hue per project.

    Start from crc32 (not hash(), which Python salts per process), then walk the slugs in
    alphabetical order and nudge any hue that lands near one already taken. A bare hash
    put two of the author's projects on the same magenta.
    """
    taken: list[int] = []
    hues: dict[str, int] = {}
    for slug in sorted(set(slugs)):
        hue = zlib.crc32(slug.encode("utf-8")) % 360
        for _ in range(360 // MIN_HUE_GAP):
            if all(min((hue - t) % 360, (t - hue) % 360) >= MIN_HUE_GAP for t in taken):
                break
            hue = (hue + MIN_HUE_GAP) % 360
        taken.append(hue)
        hues[slug] = hue
    return hues


class _Graph:
    def __init__(self) -> None:
        self.nodes: dict[str, dict[str, Any]] = {}
        self.links: dict[tuple[str, str, str], dict[str, Any]] = {}

    def node(self, id: str, type: str, label: str, project: str | None, ts: datetime | None, **extra: Any) -> None:
        node = self.nodes.setdefault(
            id, {"id": id, "type": type, "label": label, "project": project, "count": 0, "last_ts": None, **extra}
        )
        node["count"] += 1
        if ts and (node["last_ts"] is None or ts.isoformat() > node["last_ts"]):
            node["last_ts"] = ts.isoformat()
        for name, value in extra.items():
            if value is not None:
                node[name] = value

    def link(self, source: str, target: str, kind: str) -> None:
        key = (source, target, kind)
        link = self.links.setdefault(key, {"source": source, "target": target, "kind": kind, "weight": 0})
        link["weight"] += 1


def _roots_by_repo(events: list[dict]) -> dict[str, str]:
    """Latest known checkout path per repo slug, to turn a memory's repo-relative file into an absolute one."""
    roots: dict[str, tuple[datetime, str]] = {}
    for row in events:
        moment, repo, root = event_ts(row.get("ts")), row.get("repo"), row.get("main_root")
        if moment and repo and root and (repo not in roots or moment >= roots[repo][0]):
            roots[repo] = (moment, root)
    return {repo: root for repo, (_, root) in roots.items()}


def _window(since: datetime | None, until: datetime | None) -> tuple[datetime | None, datetime | None]:
    """`until` names a day, so it covers that whole day."""
    return since, until + timedelta(days=1) if until else None


def _in(moment: datetime, window: tuple[datetime | None, datetime | None]) -> bool:
    start, end = window
    return (start is None or moment >= start) and (end is None or moment < end)


def _under(path: str, base: str) -> str | None:
    """`path` relative to `base`, or None when it lies outside. A sibling like `Obsidian-old` is outside."""
    return str(PurePosixPath(path).relative_to(base)) if PurePosixPath(path).is_relative_to(base) else None


def _locate(stored: str, root: str | None, vault_root: str | None) -> tuple[str | None, str, str]:
    """(resolved absolute path or None, display name, area) of a file.

    A repo-relative path needs the repo's checkout to become absolute. An absolute path is already openable:
    inside the checkout it is a repo file, otherwise a file a skill wrote in the Obsidian vault or elsewhere.
    The path is resolved through symlinks because the hook logs resolved paths (/private/var on macOS)
    while a memory keeps the spelling a skill used (/var): only resolved paths can share one node id.
    """
    if not stored.startswith("/"):
        return (os.path.realpath(PurePosixPath(root) / stored) if root else None), stored, "repo"
    resolved = os.path.realpath(stored)
    if root and (inside := _under(resolved, os.path.realpath(root))) is not None:
        return resolved, inside, "repo"
    if vault_root:
        for path in (stored, resolved):
            for base in (vault_root, os.path.realpath(vault_root)):
                if (inside := _under(path, base)) is not None:
                    return resolved, inside, "vault"
    return resolved, stored, "external"


def _file_id(scope: str, stored: str, absolute: str | None) -> str:
    return f"file:{absolute}" if absolute else f"file:{scope}:{stored}"


def build_graph(
    events: list[dict], memories: list[dict], since: datetime | None = None, until: datetime | None = None,
    vault_root: str | None = None,
) -> dict[str, Any]:
    window = _window(since=since, until=until)
    graph = _Graph()
    roots = _roots_by_repo(events=events)

    for row in events:
        moment, repo, skill = event_ts(row.get("ts")), row.get("repo"), row.get("skill")
        if not skill or not repo or not moment or not _in(moment, window):
            continue
        if row.get("event") == "file_write" and row.get("path"):
            absolute, shown, area = _locate(row["path"], root=row.get("root"), vault_root=vault_root)
            file_id = _file_id(scope=repo, stored=row["path"], absolute=absolute)
            graph.node(f"project:{repo}", "project", repo, repo, moment, root=roots.get(repo))
            graph.node(
                file_id, "file", PurePosixPath(row["path"]).name, repo, moment, relative=shown, path=absolute,
                area=area, skill=skill,
            )
            graph.link(f"project:{repo}", file_id, "has_file")
            continue
        if row.get("event") != "skill_start":
            continue
        branch_id = f"branch:{repo}:{row.get('branch') or 'unknown'}"
        graph.node(f"project:{repo}", "project", repo, repo, moment, root=roots.get(repo))
        graph.node(branch_id, "branch", row.get("branch") or "unknown", repo, moment)
        graph.link(f"project:{repo}", branch_id, "has_branch")

    for memory in memories:
        moment = event_ts(memory.get("ts"))
        if memory.get("status") == "forgotten" or not moment or not _in(moment, window):
            continue
        scope, key = memory["scope"], memory["key"]
        project, memory_id = f"project:{scope}", f"memory:{scope}/{key}"
        root = roots.get(scope)
        graph.node(project, "project", scope, scope, moment, root=root)
        graph.node(
            memory_id, "memory", key, scope, moment, text=memory.get("text"), kind=memory.get("kind"),
            status=memory.get("status"), skill=memory.get("skill"),
        )
        graph.link(project, memory_id, "has_memory")
        file_ids = []
        for relative in dict.fromkeys(memory.get("files") or []):
            absolute, shown, area = _locate(relative, root=root, vault_root=vault_root)
            file_id = _file_id(scope=scope, stored=relative, absolute=absolute)
            graph.node(
                file_id, "file", PurePosixPath(relative).name, scope, moment, relative=shown, path=absolute,
                area=area, skill=memory.get("skill"),
            )
            graph.link(memory_id, file_id, "touches")
            graph.link(project, file_id, "has_file")
            file_ids.append(file_id)
        for first, second in combinations(sorted(file_ids), 2):
            graph.link(first, second, "co_mentioned")

    projects = [n for n in graph.nodes.values() if n["type"] == "project"]
    hues = assign_hues(slugs=[n["label"] for n in projects])
    for node in projects:
        node["hue"] = hues[node["label"]]
    return {"nodes": list(graph.nodes.values()), "links": list(graph.links.values())}


def _starts(events: list[dict], window: tuple[datetime | None, datetime | None]) -> list[tuple[datetime, dict]]:
    found = []
    for row in events:
        moment = event_ts(row.get("ts"))
        if row.get("event") == "skill_start" and row.get("skill") and moment and _in(moment, window):
            found.append((moment, row))
    return found


def skill_usage(events: list[dict], since: datetime | None = None, until: datetime | None = None) -> list[dict]:
    """Global skill usage, most used first: count, last use and the split per project."""
    per_skill: dict[str, dict[str, Any]] = {}
    for moment, row in _starts(events=events, window=_window(since=since, until=until)):
        fresh = {"skill": row["skill"], "count": 0, "last_ts": None, "projects": Counter()}
        entry = per_skill.setdefault(row["skill"], fresh)
        entry["count"] += 1
        entry["projects"][row.get("repo") or "unknown"] += 1
        if entry["last_ts"] is None or moment.isoformat() > entry["last_ts"]:
            entry["last_ts"] = moment.isoformat()
    usage = [{**e, "projects": dict(e["projects"].most_common())} for e in per_skill.values()]
    return sorted(usage, key=lambda e: (-e["count"], e["skill"]))


def activity_by_day(events: list[dict], memories: list[dict]) -> list[dict]:
    """Skill starts plus memories written per UTC day, over all time: the date picker's histogram."""
    moments = [m for m, _ in _starts(events=events, window=(None, None))]
    moments += [m for row in memories if row.get("status") != "forgotten" and (m := event_ts(row.get("ts")))]
    days = Counter(f"{m:%Y-%m-%d}" for m in moments)
    return [{"day": day, "count": count} for day, count in sorted(days.items())]
