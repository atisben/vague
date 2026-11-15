"""Reading Claude Code hook payloads."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any


def edited_file(payload: dict[str, Any]) -> Path | None:
    """The file a Write or Edit touched, absolute and symlink-resolved, or None for any other payload.

    A relative path resolves against the payload's `cwd`, the session's directory, not the hook's.
    Resolving symlinks lets an edit through an installed link (~/.claude*/skills/<name>) match the
    bundled source, and matches git's resolved roots (/private/var on macOS).
    """
    if payload.get("tool_name") not in ("Write", "Edit"):
        return None
    tool_input = payload.get("tool_input")
    file_path = tool_input.get("file_path") if isinstance(tool_input, dict) else None
    if not isinstance(file_path, str) or not file_path:
        return None
    cwd = payload.get("cwd")
    return Path(os.path.realpath(os.path.join(cwd, file_path) if isinstance(cwd, str) and cwd else file_path))
