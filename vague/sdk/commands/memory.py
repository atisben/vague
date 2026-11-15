"""vague memory-log and memory-search."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import NoReturn

import typer

from vague.sdk.core import memory as mem
from vague.sdk.core.events import log_context_access
from vague.sdk.core.slug import get_scope

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
    if status is not None and status not in mem.STATUSES:
        _fail(f"--status must be one of {', '.join(mem.STATUSES)}")
    kind = _kind(about=about, scratch=scratch, doc=doc)
    normalized = mem.normalize_files(values=files or [])
    if doc and not normalized:
        _fail("--doc needs --files <path>: a doc memory points at the document a skill wrote")
    scope = get_scope(use_global=use_global or about is not None)
    if scope is None:
        _fail("no memory scope here (home folder or /). Run from a project folder, "
              "or pass --global for a fact that holds in every repo.")
    path = mem.ledger_path()
    folded = {m.id: m for m in mem.fold(lines=mem.read_lines(path=path))}
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
    memory = mem.Memory(ts=datetime.now(UTC), scope=scope, key=key, kind=kind, text=text, skill=about or skill,
                        files=normalized, status=status or "active")
    try:
        mem.append_memory(memory=memory)
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
    if kind is not None and kind not in mem.KINDS:
        _fail(f"--kind must be one of {'|'.join(mem.KINDS)}")
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
    hits = mem.search(words=words, scopes=scopes, kind=kind, skill=skill)
    if not hits:
        typer.echo("No memories match.")
        return
    for m in hits:
        files = f"  (files: {', '.join(m.files)})" if m.files else ""
        typer.echo(f"{m.id}{f'  [{m.skill}]' if m.skill else ''}  {mem.one_line(text=m.text)}{files}")
    log_context_access(kind="read", path=mem.ledger_path(), ids=[m.id for m in hits])
