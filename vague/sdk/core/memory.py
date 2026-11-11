"""Global memory ledger in $VAGUE_HOME/memory.jsonl, plus per-scope scratchpads, folded per (scope, key)."""

from __future__ import annotations

import os
import subprocess
from collections.abc import Iterable
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Literal, NamedTuple, get_args

from pydantic import BaseModel, field_validator

from vague.sdk.core.logging import get_logger
from vague.sdk.core.slug import get_git_context

Kind = Literal["learning", "observation"]
Status = Literal["active", "forgotten", "actioned", "declined"]
KINDS: tuple[str, ...] = get_args(Kind)
STATUSES: tuple[str, ...] = get_args(Status)

MAX_TEXT = 600
# Preamble budget of 1,500 tokens at about 4 characters per token.
BLOCK_LIMIT = 6_000
FULL_LIMIT = 4_800
SCRATCH_LIMIT = 1_200
SCRATCH_TTL = timedelta(days=7)


class Memory(BaseModel):
    ts: datetime
    scope: str
    key: str
    kind: Kind
    text: str | None = None
    files: list[str] = []
    skill: str | None = None
    status: Status = "active"

    @field_validator("ts")
    @classmethod
    def _aware(cls, value: datetime) -> datetime:
        # Ranking compares timestamps, and Python refuses to compare naive with aware ones.
        return value if value.tzinfo else value.replace(tzinfo=UTC)

    @property
    def id(self) -> str:
        return f"{self.scope}/{self.key}"


class Block(NamedTuple):
    text: str
    ids: list[str]
    scratch_ids: list[str]


def vague_home() -> Path:
    return Path(os.environ.get("VAGUE_HOME", Path.home() / ".vague"))


def ledger_path() -> Path:
    return vague_home() / "memory.jsonl"


def scratch_path(scope: str) -> Path:
    return vague_home() / "scratch" / f"{scope}.jsonl"


def one_line(text: str | None) -> str:
    return " ".join((text or "").split())


def append_memory(memory: Memory, scratch: bool = False) -> Path:
    """Append one line in a single O_APPEND write, without a lock, the same guarantee events.py relies on."""
    if memory.text is not None and len(memory.text) > MAX_TEXT:
        raise ValueError(f"text is {len(memory.text)} characters, the limit is {MAX_TEXT}")
    path = scratch_path(scope=memory.scope) if scratch else ledger_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o644)
    try:
        os.write(fd, (memory.model_dump_json(exclude_none=True) + "\n").encode("utf-8"))
    finally:
        os.close(fd)
    return path


def read_lines(path: Path) -> list[Memory]:
    """Every parseable line, in file order. A torn line from a crash is skipped, not fatal."""
    if not path.exists():
        return []
    memories = []
    # A torn line can end inside a multi-byte character.
    for number, line in enumerate(path.read_bytes().decode("utf-8", errors="replace").splitlines(), start=1):
        try:
            memories.append(Memory.model_validate_json(line))
        except ValueError as e:
            if line.strip():
                get_logger().warning("skipping unparseable memory line %s:%d: %s", path, number, e)
    return memories


def fold(lines: Iterable[Memory]) -> list[Memory]:
    """Merge lines per (scope, key) in file order: the latest non-empty value of each field wins."""
    merged: dict[tuple[str, str], dict] = {}
    for line in lines:
        fields = {name: value for name, value in line.model_dump().items() if value not in (None, "", [])}
        merged.setdefault((line.scope, line.key), {}).update(fields)
    return [Memory(**fields) for fields in merged.values()]


def load_ledger() -> list[Memory]:
    return fold(lines=read_lines(path=ledger_path()))


def _live(memory: Memory) -> bool:
    return memory.status == "active" and bool(memory.text)


def load_scratch(scope: str, now: datetime | None = None) -> list[Memory]:
    """Active notes of one scope touched in the last 7 days, newest first."""
    cutoff = (now or datetime.now(UTC)) - SCRATCH_TTL
    notes = [m for m in fold(lines=read_lines(path=scratch_path(scope=scope))) if _live(m) and m.ts >= cutoff]
    return sorted(notes, key=lambda m: m.ts, reverse=True)


def normalize_files(values: list[str], cwd: Path | None = None) -> list[str]:
    """Turn `--files` values into the paths a memory stores.

    A skill may report any file it wrote, inside the repo or not (an Obsidian note, say). Inside the repo
    a path is stored repo-relative, so one file is one graph node however it was spelled. Outside it, the
    path is stored absolute. A value that exists on disk stays whole, which keeps a filename with a comma
    intact. Any other value is split on commas.
    """
    base = cwd or Path.cwd()
    git = get_git_context(cwd=base)
    root = Path(os.path.realpath(git.root)) if git.in_repo else None
    found: list[str] = []
    for value in values:
        whole = Path(value).expanduser()
        exists = whole.exists() or (base / whole).exists()
        parts = [value] if exists else value.split(",")
        for part in (p.strip() for p in parts):
            if not part:
                continue
            path = Path(part).expanduser()
            if path.is_absolute() and root:
                try:
                    path = Path(os.path.realpath(path)).relative_to(root)
                except ValueError:
                    pass
            found.append(os.path.normpath(path))
    return list(dict.fromkeys(found))


def changed_files(cwd: Path | None = None) -> list[str]:
    """Repo-relative paths changed since HEAD plus untracked ones. Empty outside a repo or on git failure."""
    git = get_git_context(cwd=cwd)
    if not git.in_repo:
        return []
    found: set[str] = set()
    for args in (["diff", "--name-only", "HEAD"], ["ls-files", "--others", "--exclude-standard"]):
        try:
            result = subprocess.run(["git", *args], capture_output=True, text=True, cwd=git.root, timeout=5)
        except (OSError, subprocess.SubprocessError):
            continue
        if result.returncode == 0:
            found.update(line for line in result.stdout.splitlines() if line)
    return sorted(found)


def rank(memories: Iterable[Memory], skill: str | None, changed_files: Iterable[str]) -> list[Memory]:
    """Shared files first, then a skill match, then newest. Deterministic, no score to tune."""
    changed = set(changed_files)
    return sorted(memories, reverse=True,
                  key=lambda m: (len(changed.intersection(m.files)), skill is not None and m.skill == skill, m.ts))


def _line(memory: Memory, scope: str | None, full: bool = True) -> str:
    label = memory.key if memory.scope == scope else memory.id
    return f"- [{label}] {one_line(text=memory.text)}" if full else f"- [{label}]"


def logging_hint(skill: str | None) -> str:
    """One reminder line, so every skill gets the logging rule without repeating it in its own file."""
    return (
        f'To log a learning: vague memory-log <key> "<fact>" --skill {skill or "<skill>"} [--files <paths>] '
        "[--global]. Add --scratch for a note other agents on this project need."
    )


def render_block(
    scope: str | None, skill: str | None, changed_files: Iterable[str], now: datetime | None = None
) -> Block:
    """Preamble block: scratch notes, ranked full lines (global capped at a third), key-only index, search pointer."""
    learnings = [m for m in load_ledger() if m.scope in {scope, "global"} and m.kind == "learning" and _live(m)]
    notes = load_scratch(scope=scope, now=now) if scope else []
    hint = logging_hint(skill=skill)
    lines = [f"vague memory · scope {scope or 'none (global only)'} · {len(learnings)} memories", hint]
    if not learnings and not notes:
        lines.append("No memories yet.")
        return Block(text="\n".join(lines), ids=[], scratch_ids=[])
    ids: list[str] = []
    scratch_ids: list[str] = []
    rest: list[Memory] = []

    def used() -> int:
        return sum(len(line) + 1 for line in lines)

    scratch_header = "Scratch (shared by this scope's agents, last 7 days):"
    budget = SCRATCH_LIMIT - len(scratch_header)
    for note in notes:
        line = _line(memory=note, scope=scope)
        if len(line) + 1 <= budget:
            lines.extend([scratch_header, line] if not scratch_ids else [line])
            scratch_ids.append(note.id)
            budget -= len(line) + 1

    if learnings:
        lines.append("Memories (most relevant first):")
        global_budget = (FULL_LIMIT - used()) // 3
        for memory in rank(memories=learnings, skill=skill, changed_files=changed_files):
            line = _line(memory=memory, scope=scope)
            capped = memory.scope == "global" and scope != "global"
            if used() + len(line) + 1 <= FULL_LIMIT and (not capped or len(line) + 1 <= global_budget):
                lines.append(line)
                ids.append(memory.id)
                global_budget -= len(line) + 1 if capped else 0
            else:
                rest.append(memory)

    if rest:
        lines.append("Index (key only):")
        reserve = len(f"+{len(rest)} more: vague memory-search <words>") + 1 + len(hint) + 1
        shown = 0
        for memory in rest:
            line = _line(memory=memory, scope=scope, full=False)
            if used() + len(line) + 1 + reserve > BLOCK_LIMIT:
                break
            lines.append(line)
            ids.append(memory.id)
            shown += 1
        if shown < len(rest):
            lines.append(f"+{len(rest) - shown} more: vague memory-search <words>")
    return Block(text="\n".join(lines), ids=ids, scratch_ids=scratch_ids)


def search(
    words: Iterable[str], scopes: Iterable[str] | None, kind: str | None = None, scratch: bool = False,
    now: datetime | None = None,
) -> list[Memory]:
    """Active memories containing every word across key, text, files and skill, newest first. `scopes=None`: all."""
    needles = [w.lower() for w in words if w.strip()]
    if scratch:
        names = sorted(scopes) if scopes is not None else sorted(p.stem for p in vague_home().glob("scratch/*.jsonl"))
        pool = [note for name in names for note in load_scratch(scope=name, now=now)]
    else:
        wanted = None if scopes is None else set(scopes)
        pool = [m for m in load_ledger() if _live(m) and (wanted is None or m.scope in wanted)]
    hits = [m for m in pool if (kind is None or m.kind == kind)
            and all(n in " ".join([m.key, m.text or "", *m.files, m.skill or ""]).lower() for n in needles)]
    return sorted(hits, key=lambda m: m.ts, reverse=True)
