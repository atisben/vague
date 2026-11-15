"""Global memory ledger in $VAGUE_HOME/memory.jsonl, folded per (scope, key).

Four kinds share the one file:

| kind        | meaning                               | lifetime                  |
|-------------|---------------------------------------|---------------------------|
| learning    | a durable fact                        | forever                   |
| observation | feedback about a skill, for /retro    | until actioned            |
| note        | a working note for this scope's agents | hidden 7 days after `ts` |
| doc         | a pointer to a document a skill wrote | forever                   |
"""

from __future__ import annotations

import os
import re
from collections.abc import Iterable
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Literal, NamedTuple, NoReturn, get_args

import typer
from pydantic import BaseModel, ValidationError, field_validator

from vague import git as git_cli
from vague import jsonl
from vague.events import log_context_access
from vague.git import get_git_context, get_scope
from vague.log import get_logger
from vague.paths import vague_home

Kind = Literal["learning", "observation", "note", "doc"]
Status = Literal["active", "forgotten", "actioned", "declined"]
KINDS: tuple[str, ...] = get_args(Kind)
STATUSES: tuple[str, ...] = get_args(Status)

MAX_TEXT = 600
# Preamble budget of 1,500 tokens at about 4 characters per token.
BLOCK_LIMIT = 6_000
FULL_LIMIT = 4_800
SCRATCH_LIMIT = 1_200
SCRATCH_TTL = timedelta(days=7)
DOC_INDEX_SIZE = 5
DOC_HEADER = f"Documents (newest {DOC_INDEX_SIZE}, vague memory-search --kind doc for more):"


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


def ledger_path() -> Path:
    return vague_home() / "memory.jsonl"


def one_line(text: str | None) -> str:
    return " ".join((text or "").split())


def append_memory(memory: Memory) -> Path:
    """Append one line without a lock: concurrent writers never interleave (see jsonl.append)."""
    if memory.text is not None and len(memory.text) > MAX_TEXT:
        raise ValueError(f"text is {len(memory.text)} characters, the limit is {MAX_TEXT}")
    path = ledger_path()
    jsonl.append(path=path, line=memory.model_dump_json(exclude_none=True))
    return path


def read_lines(path: Path) -> list[Memory]:
    """Every valid memory, in file order. A torn or invalid line is skipped with a warning, not fatal."""
    memories = []
    for row in jsonl.read(path=path):
        try:
            memories.append(Memory.model_validate(row))
        except ValidationError as e:
            get_logger().warning("skipping invalid memory in %s: %s", path, e)
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


def _live(memory: Memory, now: datetime | None = None) -> bool:
    """Active, with text, and for a note touched in the last 7 days: a stale note no longer describes the work."""
    if memory.status != "active" or not memory.text:
        return False
    return memory.kind != "note" or memory.ts >= (now or datetime.now(UTC)) - SCRATCH_TTL


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
    for args in (("diff", "--name-only", "HEAD"), ("ls-files", "--others", "--exclude-standard")):
        found.update(line for line in (git_cli.run(*args, cwd=git.root) or "").splitlines() if line)
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
        "[--global]. Add --scratch for a note other agents on this project need, "
        "or --doc --files <path> for a document you wrote."
    )


def render_block(
    scope: str | None, skill: str | None, changed_files: Iterable[str], now: datetime | None = None
) -> Block:
    """Preamble block: notes, newest docs, ranked learnings (global capped at a third), key-only index, search pointer.

    Observations never appear: they are feedback for /retro, not context for the task.
    """
    visible = [m for m in load_ledger() if m.scope in {scope, "global"} and _live(memory=m, now=now)]
    learnings = [m for m in visible if m.kind == "learning"]
    # Notes are this project's working state, so a global note would leak into every repo.
    notes = sorted((m for m in visible if m.kind == "note" and m.scope == scope), key=lambda m: m.ts, reverse=True)
    docs = sorted((m for m in visible if m.kind == "doc" and m.files), key=lambda m: m.ts, reverse=True)
    hint = logging_hint(skill=skill)
    lines = [f"vague memory · scope {scope or 'none (global only)'} · {len(learnings)} memories", hint]
    if not learnings and not notes and not docs:
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

    if docs:
        # Key and path only: the doc itself holds the content, and a skill opens it when it needs it.
        lines.append(DOC_HEADER)
        for doc in docs[:DOC_INDEX_SIZE]:
            label = doc.key if doc.scope == scope else doc.id
            lines.append(f"- [{label}] {doc.files[0]}")
            ids.append(doc.id)

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
    words: Iterable[str], scopes: Iterable[str] | None, kind: str | None = None, skill: str | None = None,
    now: datetime | None = None,
) -> list[Memory]:
    """Active memories containing every word across key, text, files and skill, newest first. `scopes=None`: all.

    `skill` matches the skill field exactly, so `plan-eng` never returns a `plan-eng-lite` memory.
    """
    needles = [w.lower() for w in words if w.strip()]
    wanted = None if scopes is None else set(scopes)
    hits = [m for m in load_ledger() if _live(memory=m, now=now) and (wanted is None or m.scope in wanted)
            and (kind is None or m.kind == kind) and (skill is None or m.skill == skill)
            and all(n in " ".join([m.key, m.text or "", *m.files, m.skill or ""]).lower() for n in needles)]
    return sorted(hits, key=lambda m: m.ts, reverse=True)


_KEY_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,99}$")


def _fail(message: str) -> NoReturn:
    typer.echo(f"Error: {message}", err=True)
    raise typer.Exit(code=1)


def _kind(about: str | None, scratch: bool, doc: bool) -> str:
    """The kind a write asks for. The flags that pick one are mutually exclusive."""
    picked = [flag for flag, on in (("--about", about is not None), ("--scratch", scratch), ("--doc", doc)) if on]
    if len(picked) > 1:
        _fail(f"{' and '.join(picked)} pick different kinds: give one of them")
    if not picked:
        return "learning"
    return {"--about": "observation", "--scratch": "note", "--doc": "doc"}[picked[0]]


def cmd_memory_log(key: str, text: str | None, files: list[str] | None, use_global: bool, about: str | None,
                   status: str | None, scratch: bool, skill: str | None, doc: bool = False) -> None:
    """Append one memory line to the ledger and print `OK scope/key`."""
    if not _KEY_RE.match(key):
        _fail(f"key {key!r} must be kebab-case: letters, digits, '.', '_' or '-', at most 100 characters")
    if text is not None and not text.strip():
        _fail("TEXT is empty")
    if text is None and status is None:
        _fail("give TEXT, --status, or both")
    if status is not None and status not in STATUSES:
        _fail(f"--status must be one of {', '.join(STATUSES)}")
    kind = _kind(about=about, scratch=scratch, doc=doc)
    normalized = normalize_files(values=files or [])
    if doc and not normalized:
        _fail("--doc needs --files <path>: a doc memory points at the document a skill wrote")
    scope = get_scope(use_global=use_global or about is not None)
    if scope is None:
        _fail("no memory scope here (home folder or /). Run from a project folder, "
              "or pass --global for a fact that holds in every repo.")
    path = ledger_path()
    folded = {m.id: m for m in fold(lines=read_lines(path=path))}
    if text is None:
        # A status-only line copies scope and kind, and observations live in `global` so --global is optional.
        existing = folded.get(f"{scope}/{key}") or folded.get(f"global/{key}")
        if existing is None:
            _fail(f"no memory {scope}/{key} to update. Pass TEXT to create it")
        scope, kind = existing.scope, existing.kind
    elif (existing := folded.get(f"{scope}/{key}")) and (existing.kind == "note") != (kind == "note"):
        # A note expires after 7 days. Folding it with a durable kind would make a fact vanish, or a note stay.
        _fail(f"{scope}/{key} is a {existing.kind}, and a write may not turn a note into another kind or back. "
              "Use a new key")
    memory = Memory(ts=datetime.now(UTC), scope=scope, key=key, kind=kind, text=text, skill=about or skill,
                        files=normalized, status=status or "active")
    try:
        append_memory(memory=memory)
    except ValueError as e:
        _fail(str(e))
    log_context_access(kind="write", path=path, ids=[memory.id])
    typer.echo(f"OK {memory.id}")


def cmd_memory_search(words: list[str], scope: str | None, kind: str | None, scratch: bool,
                      skill: str | None = None) -> None:
    """Print `scope/key  [skill]  text` per active memory matching every word, newest first (no `[skill]` when unset).

    No words lists every memory that passes the filters. `scope`: a project name, `global`, or `all`.
    `scratch` is shorthand for `kind="note"`.
    """
    if kind is not None and kind not in KINDS:
        _fail(f"--kind must be one of {'|'.join(KINDS)}")
    if scratch and kind not in (None, "note"):
        _fail(f"--scratch means --kind note, which contradicts --kind {kind}")
    kind = "note" if scratch else kind
    scopes: list[str] | None
    if scope == "all":
        scopes = None
    elif scope is not None:
        scopes = [scope]
    elif kind == "observation":
        scopes = ["global"]
    else:
        scopes = [s for s in (get_scope(), "global") if s]
    hits = search(words=words, scopes=scopes, kind=kind, skill=skill)
    if not hits:
        typer.echo("No memories match.")
        return
    for m in hits:
        files = f"  (files: {', '.join(m.files)})" if m.files else ""
        typer.echo(f"{m.id}{f'  [{m.skill}]' if m.skill else ''}  {one_line(text=m.text)}{files}")
    log_context_access(kind="read", path=ledger_path(), ids=[m.id for m in hits])
