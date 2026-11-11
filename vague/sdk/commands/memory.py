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


def cmd_memory_log(key: str, text: str | None, files: list[str] | None, use_global: bool, about: str | None,
                   status: str | None, scratch: bool, skill: str | None) -> None:
    """Append one memory line to the ledger (or the scope's scratchpad) and print `OK scope/key`."""
    if not _KEY_RE.match(key):
        _fail(f"key {key!r} must be kebab-case: letters, digits, '.', '_' or '-', at most 100 characters")
    if text is not None and not text.strip():
        _fail("TEXT is empty")
    if text is None and status is None:
        _fail("give TEXT, --status, or both")
    if status is not None and status not in mem.STATUSES:
        _fail(f"--status must be one of {', '.join(mem.STATUSES)}")
    if about is not None and scratch:
        _fail("--about writes an observation for /meta, which never goes to the scratchpad")
    scope = get_scope(use_global=use_global or about is not None)
    if scope is None:
        _fail("no memory scope here (home folder or /). Run from a project folder, "
              "or pass --global for a fact that holds in every repo.")
    path = mem.scratch_path(scope=scope) if scratch else mem.ledger_path()
    kind = "observation" if about is not None else "learning"
    if text is None:
        # A status-only line copies scope and kind, and observations live in `global` so --global is optional.
        folded = {m.id: m for m in mem.fold(lines=mem.read_lines(path=path))}
        existing = folded.get(f"{scope}/{key}") or folded.get(f"global/{key}")
        if existing is None:
            _fail(f"no memory {scope}/{key} to update. Pass TEXT to create it")
        scope, kind = existing.scope, existing.kind
    memory = mem.Memory(ts=datetime.now(UTC), scope=scope, key=key, kind=kind, text=text, skill=about or skill,
                        files=mem.normalize_files(values=files or []), status=status or "active")
    try:
        mem.append_memory(memory=memory, scratch=scratch)
    except ValueError as e:
        _fail(str(e))
    log_context_access(kind="write", path=path, ids=[memory.id])
    typer.echo(f"OK {memory.id}")


def cmd_memory_search(words: list[str], scope: str | None, kind: str | None, scratch: bool) -> None:
    """Print `scope/key  [skill]  text` per active memory matching every word, newest first (no `[skill]` when unset).

    No words lists every memory that passes the filters. `scope`: a project name, `global`, or `all`.
    """
    if kind is not None and kind not in mem.KINDS:
        _fail(f"--kind must be one of {', '.join(mem.KINDS)}")
    scopes: list[str] | None
    if scope == "all":
        scopes = None
    elif scope is not None:
        scopes = [scope]
    elif kind == "observation":
        scopes = ["global"]
    else:
        scopes = [s for s in (get_scope(), "global") if s]
    hits = mem.search(words=words, scopes=scopes, kind=kind, scratch=scratch)
    if not hits:
        typer.echo("No memories match.")
        return
    for m in hits:
        files = f"  (files: {', '.join(m.files)})" if m.files else ""
        typer.echo(f"{m.id}{f'  [{m.skill}]' if m.skill else ''}  {mem.one_line(text=m.text)}{files}")
    if not scratch:
        log_context_access(kind="read", path=mem.ledger_path(), ids=[m.id for m in hits])
    for scope in dict.fromkeys(m.scope for m in hits if scratch):
        ids = [m.id for m in hits if m.scope == scope]
        log_context_access(kind="read", path=mem.scratch_path(scope=scope), ids=ids)
