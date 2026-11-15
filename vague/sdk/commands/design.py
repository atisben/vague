"""vague design-check command: run the Impeccable source detector on UI files."""

from __future__ import annotations

import json
import os
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import typer

from vague.sdk.core.logging import get_logger

# Vendored, generated or tool-owned trees: findings there are not the user's to fix.
_SKIPPED_DIRS = frozenset({"node_modules", "dist", "build"})

_SUPPRESS_HINT = (
    "Fix each finding. To keep a deliberate one, put `/* impeccable-disable-next-line <rule>: <reason> */` "
    "(or `<!-- ... -->` in markup) on the line above it."
)


def _ui_files(root: Path) -> Iterator[Path]:
    """UI source files under `root`, sorted, skipping hidden and vendor directories."""
    from vague.sdk.core.design_rules import UI_EXTENSIONS

    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if not d.startswith(".") and d not in _SKIPPED_DIRS)
        for name in sorted(filenames):
            path = Path(dirpath) / name
            if path.suffix.lower() in UI_EXTENSIONS:
                yield path


def _display(path: Path, base: Path) -> str:
    """`path` relative to `base` when it sits under it, else absolute."""
    try:
        return str(path.relative_to(base))
    except ValueError:
        return str(path)


def cmd_design_check(paths: list[str], hook: bool) -> None:
    if hook:
        _run_hook()
        return
    if not paths:
        print("vague design-check: missing PATHS: give one or more files or directories, "
              "or --hook to read a hook payload",
              file=sys.stderr)
        raise typer.Exit(code=2)
    missing = [p for p in paths if not Path(p).exists()]
    if missing:
        for p in missing:
            print(f"vague design-check: no such file or directory: {p}", file=sys.stderr)
        raise typer.Exit(code=2)

    from vague.sdk.core.design_rules import brand_fonts_from_memory, check

    brand_fonts = brand_fonts_from_memory()
    count = 0
    for arg in paths:
        root = Path(arg)
        files = _ui_files(root=root) if root.is_dir() else iter([root])
        for path in files:
            for finding in check(path=path, brand_fonts=brand_fonts):
                # normpath drops the leading `./` a `.` argument would add to every line.
                print(f"{os.path.normpath(path)}:{finding.line}: {finding.rule_id}: {finding.message}")
                count += 1
    if count:
        print(f"FAILED: {count} finding(s)")
        raise typer.Exit(code=1)
    print("OK: no findings")


def _edited_file(payload: dict[str, Any]) -> tuple[Path, Path] | None:
    """The file a Write/Edit touched, resolved against the session cwd, and that cwd."""
    tool_input = payload.get("tool_input")
    file_path = tool_input.get("file_path") if isinstance(tool_input, dict) else None
    if not isinstance(file_path, str) or not file_path:
        return None
    cwd_raw = payload.get("cwd")
    cwd = Path(os.path.realpath(cwd_raw)) if isinstance(cwd_raw, str) and cwd_raw else Path.cwd()
    return Path(os.path.realpath(cwd / file_path)), cwd


def _run_hook() -> None:
    """PostToolUse hook: findings go to stderr with exit 2, which Claude Code feeds back to Claude.

    Runs after every Edit and Write while /impeccable is loaded, so anything other than a
    finding (no payload, bad JSON, a non-UI file, a crash) exits 0 silently.
    """
    lines: list[str] = []
    try:
        raw = sys.stdin.read()
        if not raw.strip():
            return
        payload = json.loads(raw)
        if not isinstance(payload, dict):
            return
        edited = _edited_file(payload=payload)
        if edited is None:
            return
        path, cwd = edited

        from vague.sdk.core import design_rules

        if path.suffix.lower() not in design_rules.UI_EXTENSIONS or not path.is_file():
            return
        # The session's project is the payload cwd, not the hook process's own cwd.
        from vague.sdk.core.slug import get_scope
        brand_fonts = design_rules.brand_fonts_from_memory(scope=get_scope(cwd=cwd))
        findings = design_rules.check(path=path, brand_fonts=brand_fonts)
        if findings:
            shown = _display(path=path, base=cwd)
            lines.append(f"vague design-check: {len(findings)} finding(s) in {shown}")
            lines += [f"{shown}:{f.line}: {f.rule_id}: {f.message}" for f in findings]
            lines.append(_SUPPRESS_HINT)
    except json.JSONDecodeError:
        return
    except Exception as e:
        get_logger().warning("design-check hook failed: %s", e)
        return

    # Exit outside the try block so `except Exception` cannot swallow it.
    if lines:
        print("\n".join(lines), file=sys.stderr)
        raise typer.Exit(code=2)
