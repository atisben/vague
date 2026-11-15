"""Append-only JSON-lines files: the memory ledger and the monthly event logs."""

from __future__ import annotations

import json
import os
from pathlib import Path

from vague.log import get_logger


def append(path: Path, line: str) -> None:
    """Append one line in a single write, without a lock.

    One os.write on an O_APPEND fd lands contiguously on local filesystems, so concurrent
    writers do not interleave. Only a write beyond PIPE_BUF loses that guarantee, and one line
    stays far below it.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o644)
    try:
        os.write(fd, (line + "\n").encode("utf-8"))
    finally:
        os.close(fd)


def read(path: Path) -> list[dict]:
    """Every line that parses as a JSON object, in file order. A torn line from a crash is skipped, not fatal."""
    if not path.exists():
        return []
    rows = []
    # A torn line can end inside a multi-byte character.
    for number, line in enumerate(path.read_bytes().decode("utf-8", errors="replace").splitlines(), start=1):
        try:
            row = json.loads(line)
        except ValueError as e:
            if line.strip():
                get_logger().warning("skipping unparseable line %s:%d: %s", path, number, e)
            continue
        if isinstance(row, dict):
            rows.append(row)
    return rows
