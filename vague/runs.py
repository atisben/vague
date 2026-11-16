"""Agent runs: the event log cut into one run per skill start, with the context each run read and wrote.

    session s1: skill_start ─ context_read ─ context_write ─ file_write ─ skill_start ─ ...
                └──────────────── run 1 ────────────────────────────────┘ └── run 2 ──

A skill sends no end signal, so a run lasts until the next skill start in the same session.
Reads in a session before its first skill start form a run with no skill.

Pure functions, no I/O: the server feeds them rows and the tests feed them dicts.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from pathlib import PurePosixPath
from typing import Any

from vague.events import event_ts
from vague.graph import locate

_AREA_ORDER = {"vault": 0, "repo": 1, "external": 2}


def _new_run(session: str, moment: datetime, row: dict, skill: str | None) -> dict[str, Any]:
    return {
        "id": f"{session}@{moment.isoformat()}", "session": session, "skill": skill, "repo": row.get("repo"),
        "branch": row.get("branch"), "start": moment.isoformat(), "end": moment.isoformat(),
        "served": {}, "created": {}, "files": {}, "steps": [],
    }


def _segment(events: list[dict]) -> list[tuple[dict[str, Any], list[tuple[datetime, dict]]]]:
    """Runs in time order, each with its own timed rows."""
    per_session: dict[str, list[tuple[datetime, dict]]] = defaultdict(list)
    for row in events:
        moment = event_ts(row.get("ts"))
        if moment and row.get("event"):
            per_session[str(row.get("session") or "unknown")].append((moment, row))
    runs = []
    for session, rows in per_session.items():
        current = None
        for moment, row in sorted(rows, key=lambda pair: pair[0]):
            if row["event"] == "skill_start":
                current = (_new_run(session=session, moment=moment, row=row, skill=row.get("skill")), [])
                runs.append(current)
            elif current is None:
                current = (_new_run(session=session, moment=moment, row=row, skill=None), [])
                runs.append(current)
            if row["event"] != "skill_start":
                current[1].append((moment, row))
    return sorted(runs, key=lambda run: run[0]["start"])


def _fill(run: dict[str, Any], rows: list[tuple[datetime, dict]], vault_root: str | None) -> None:
    for moment, row in rows:
        run["end"] = max(run["end"], moment.isoformat())
        kind, ids = row["event"], [i for i in row.get("ids") or [] if isinstance(i, str)]
        if kind == "context_read":
            for memory_id in ids:
                run["served"][memory_id] = run["served"].get(memory_id, 0) + 1
        elif kind == "context_write":
            for memory_id in ids:
                run["created"].setdefault(memory_id, 0)
        elif kind == "file_write" and row.get("path"):
            absolute, shown, area = locate(row["path"], root=row.get("root"), vault_root=vault_root)
            key = absolute or row["path"]
            entry = run["files"].setdefault(key, {
                "path": absolute, "relative": shown, "name": PurePosixPath(row["path"]).name, "area": area,
                "count": 0, "last_ts": None, "subagent": False,
            })
            entry["count"] += 1
            entry["last_ts"] = moment.isoformat()
            entry["subagent"] = entry["subagent"] or bool(row.get("agent_id"))
        else:
            continue
        step = {"ts": moment.isoformat(), "event": kind, "command": row.get("command"), "ids": ids}
        if kind == "file_write":
            step["path"] = row.get("path")
        run["steps"].append(step)


def _provenance(timed: list[tuple[dict[str, Any], list[tuple[datetime, dict]]]]) -> dict[str, dict[str, Any]]:
    """Per run: which earlier run last wrote each served memory, and how many later runs read each created one."""
    writes: dict[str, list[tuple[datetime, str]]] = defaultdict(list)
    reads: dict[str, list[tuple[datetime, str]]] = defaultdict(list)
    for run, rows in timed:
        for moment, row in rows:
            target = {"context_write": writes, "context_read": reads}.get(row["event"])
            if target is None:
                continue
            for memory_id in row.get("ids") or []:
                target[memory_id].append((moment, run["id"]))
    out: dict[str, dict[str, Any]] = {}
    for run, rows in timed:
        first_read = {}
        for moment, row in rows:
            if row["event"] == "context_read":
                for memory_id in row.get("ids") or []:
                    first_read.setdefault(memory_id, moment)
        sources = {}
        for memory_id, moment in first_read.items():
            earlier = [rid for at, rid in writes[memory_id] if at < moment and rid != run["id"]]
            if earlier:
                sources[memory_id] = earlier[-1]
        later = {}
        for memory_id in run["created"]:
            readers = {rid for at, rid in reads[memory_id] if rid != run["id"] and at.isoformat() > run["start"]}
            later[memory_id] = len(readers)
        out[run["id"]] = {"from": sources, "later": later}
    return out


def _memory_view(memory: dict) -> dict[str, Any]:
    fields = ("scope", "key", "kind", "text", "skill", "ts", "status", "files")
    return {name: memory.get(name) for name in fields}


def agent_runs(events: list[dict], memories: list[dict], vault_root: str | None = None) -> dict[str, Any]:
    """Every run, newest first, plus the ledger entries they name, keyed `scope/key`.

    The page picks the window itself. Provenance needs every run anyway: a memory served today may date from last month.
    """
    timed = _segment(events=events)
    for run, rows in timed:
        _fill(run=run, rows=rows, vault_root=vault_root)
    links = _provenance(timed=timed)
    runs = []
    for run, _ in reversed(timed):
        sources, later = links[run["id"]]["from"], links[run["id"]]["later"]
        run["served"] = [
            {"id": i, "count": n, **({"from_run": sources[i]} if i in sources else {})}
            for i, n in run["served"].items()
        ]
        run["created"] = [{"id": i, "served_later": later.get(i, 0)} for i in run["created"]]
        run["files"] = sorted(run["files"].values(), key=lambda f: (_AREA_ORDER[f["area"]], -_ts_key(f["last_ts"])))
        runs.append(run)
    named = {e["id"] for run in runs for e in run["served"] + run["created"]}
    ledger = {f"{m['scope']}/{m['key']}": _memory_view(memory=m) for m in memories}
    return {"runs": runs, "memories": {i: ledger[i] for i in sorted(named) if i in ledger}}


def _ts_key(iso: str | None) -> float:
    moment = event_ts(iso)
    return moment.timestamp() if moment else 0.0
