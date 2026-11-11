"""One-time move of the pre-ledger per-project stores into memory.jsonl and the events log.

Reads projects/<slug>/{learnings,observations,timeline,principles,project}.md and never
changes them. `--archive` moves them aside later, once the marker proves the move ran.
"""

from __future__ import annotations

import shutil
from collections import Counter
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any, NamedTuple

from vague.sdk.core.events import Event, append_event
from vague.sdk.core.frontmatter import read_md
from vague.sdk.core.memory import MAX_TEXT, Memory, append_memory, vague_home

# Old skill names, renamed since the entries were written.
SKILL_MAP = {
    "plan-eng-review": "plan-eng", "investigate": "dev-investigate", "develop": "dev-develop",
    "ship": "dev-ship", "plan-ceo-review": "plan-ideation", "ops-vault": "vault",
}
# Owner decision 2026-11-11: the learnings logged from $HOME are mgmt-review notes about the vault.
SCOPE_MAP = {"bastien": "Obsidian"}
STATUS_MAP = {"open": "active", "actioned": "actioned", "declined": "declined"}
DROPPED = "learnings: confidence, type, source · observations: type, source_skill, session · timeline: outcome"
OLD_STORES = ("learnings.md", "observations.md", "timeline.md", "principles.md", "project.md")


class MigrationError(Exception):
    pass


class Plan(NamedTuple):
    memories: list[Memory]
    events: list[Event]
    found: Counter[str]
    skill_remaps: Counter[str]
    scope_remaps: Counter[str]


def marker_path() -> Path:
    return vague_home() / ".migrated"


def _project_dirs() -> list[Path]:
    projects = vague_home() / "projects"
    return sorted(p for p in projects.iterdir() if p.is_dir()) if projects.is_dir() else []


def _entries(path: Path) -> list[dict[str, Any]]:
    entries = read_md(path).get("entries") or []
    return [e for e in entries if isinstance(e, dict)] if isinstance(entries, list) else []


def _ts(value: Any) -> datetime:
    # YAML turns an unquoted timestamp into a datetime, a quoted one stays a string.
    moment = value if isinstance(value, datetime) else datetime.fromisoformat(str(value))
    return moment if moment.tzinfo else moment.replace(tzinfo=UTC)


def _files(value: Any) -> list[str]:
    if isinstance(value, str):
        return [f.strip() for f in value.split(",") if f.strip()]
    return [str(f) for f in value or []]


def _skill(plan: Plan, name: Any) -> str | None:
    if not name:
        return None
    new = SKILL_MAP.get(str(name), str(name))
    if new != name:
        plan.skill_remaps[f"{name} → {new}"] += 1
    return new


def _observation_text(entry: dict[str, Any]) -> str:
    text = str(entry["issue"])
    if entry.get("suggestion"):
        text += f" → {entry['suggestion']}"
    if entry.get("principle"):
        text += f" ({entry['principle']})"
    return text


def _event(ts: datetime, slug: str, path: str, skill: str | None, session: Any, branch: Any) -> Event:
    return Event(
        ts=ts, session=str(session or "migrated"), event="skill_start", cwd=path, repo=slug,
        branch=str(branch or "unknown"), root=path, main_root=path, is_worktree=False, runtime="migrated",
        skill=skill, source="migrated",
    )


def _project(plan: Plan, project: Path) -> None:
    slug = project.name
    scope = SCOPE_MAP.get(slug, slug)
    meta = read_md(project / "project.md")
    path = str(meta.get("path") or "")

    for e in _entries(project / "learnings.md"):
        plan.found["learnings"] += 1
        if scope != slug:
            plan.scope_remaps[f"{slug} → {scope}"] += 1
        plan.memories.append(Memory(
            ts=_ts(e.get("ts")), scope=scope, key=str(e["key"]), kind="learning", text=str(e["insight"]),
            files=_files(e.get("files")), skill=_skill(plan=plan, name=e.get("skill")),
        ))
    for e in _entries(project / "observations.md"):
        plan.found["observations"] += 1
        plan.memories.append(Memory(
            ts=_ts(e.get("ts")), scope="global", key=f"obs-{slug}-{e['id']}", kind="observation",
            text=_observation_text(entry=e), skill=_skill(plan=plan, name=e.get("skill")),
            status=STATUS_MAP[str(e.get("status") or "open")],
        ))
    for e in _entries(project / "timeline.md"):
        plan.found["timeline"] += 1
        plan.events.append(_event(ts=_ts(e.get("ts")), slug=slug, path=path,
                                  skill=_skill(plan=plan, name=e.get("skill")), session=e.get("session"),
                                  branch=e.get("branch")))
    if path:
        plan.found["project"] += 1
        plan.events.append(_event(ts=_ts(meta.get("last_seen")), slug=slug, path=path, skill=None,
                                  session=None, branch=None))
    plan.found["principles"] += len(_entries(project / "principles.md"))
    plan.found["planning"] += (project / "planning").is_dir()


def build_plan() -> Plan:
    """Everything a migration would write, without writing it. Raises on a malformed entry."""
    plan = Plan(memories=[], events=[], found=Counter(), skill_remaps=Counter(), scope_remaps=Counter())
    for project in _project_dirs():
        try:
            _project(plan=plan, project=project)
        except (KeyError, ValueError, TypeError) as e:
            raise MigrationError(f"{project.name}: malformed entry ({type(e).__name__}: {e})") from e
    # File order is what the fold reads, so oldest first keeps the newest duplicate winning.
    plan.memories.sort(key=lambda m: m.ts)
    plan.events.sort(key=lambda e: e.ts)
    return plan


def long_texts(plan: Plan) -> list[str]:
    return [f"{m.id} ({len(m.text or '')} chars)" for m in plan.memories if len(m.text or "") > MAX_TEXT]


def report(plan: Plan) -> list[str]:
    """The summary line, then remaps, dropped fields and over-limit texts."""
    made = Counter(m.kind for m in plan.memories)
    made["project"] = sum(1 for e in plan.events if e.skill is None)
    made["timeline"] = len(plan.events) - made["project"]
    f = plan.found
    lines = [
        f"learnings {f['learnings']} → {made['learning']} lines · observations {f['observations']} → "
        f"{made['observation']} lines · timeline {f['timeline']} → {made['timeline']} events · "
        f"project.md {f['project']} → {made['project']} events · principles {f['principles']} · "
        f"planning {f['planning']}",
        "skill remaps: " + (", ".join(f"{k} ×{n}" for k, n in sorted(plan.skill_remaps.items())) or "none"),
        "scope remaps: " + (", ".join(f"{k} ×{n}" for k, n in sorted(plan.scope_remaps.items())) or "none"),
        f"dropped fields: {DROPPED}",
    ]
    over = long_texts(plan=plan)
    if over:
        lines.append(f"over {MAX_TEXT} chars, kept whole (cap lifted for migration only): {', '.join(over)}")
    return lines


def migrate() -> Plan:
    """Append the plan to the ledger and the monthly events files, then write the marker."""
    plan = build_plan()
    for memory in plan.memories:
        append_memory(memory=memory, max_text=None)
    for event in plan.events:
        append_event(event=event)
    marker_path().write_text(datetime.now(UTC).isoformat() + "\n", encoding="utf-8")
    return plan


def archive(today: date | None = None) -> list[Path]:
    """Move the old stores, their lock files and planning/ under archive/<date>/. Deletes nothing."""
    if not marker_path().exists():
        raise MigrationError("nothing archived: run `vague migrate` first, its marker is missing")
    target = vague_home() / "archive" / f"{today or date.today():%Y-%m-%d}" / "projects"
    moved = []
    for project in _project_dirs():
        sources = [project / n for n in OLD_STORES] + sorted(project.glob("*.lock")) + [project / "planning"]
        for source in (s for s in sources if s.exists()):
            dest = target / project.name / source.name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(src=str(source), dst=str(dest))
            moved.append(dest)
    return moved
