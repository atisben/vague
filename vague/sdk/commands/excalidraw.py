"""vague excalidraw-render command."""

from __future__ import annotations

import json
from pathlib import Path

import typer
from pydantic import ValidationError

from vague.sdk.core.excalidraw import DrawingFileError, parse_spec, read_drawing, render, write_drawing

SUFFIX = ".excalidraw.md"


def _embed(out: Path) -> str:
    # Obsidian embeds drop the trailing .md; the parent folder disambiguates same-named drawings.
    return f"![[{out.parent.name}/{out.name.removesuffix('.md')}]]"


def cmd_excalidraw_render(spec_path: Path, out: Path) -> None:
    """Render a diagram spec (JSON file) into an Obsidian Excalidraw drawing."""
    if not out.name.endswith(SUFFIX):
        typer.echo(f"Error: --out must end with {SUFFIX} so the Excalidraw plugin opens it")
        raise typer.Exit(1)
    try:
        spec = parse_spec(json.loads(spec_path.read_text(encoding="utf-8")))
        result = write_drawing(out, render(spec))
    except (ValidationError, DrawingFileError, ValueError, OSError) as e:
        typer.echo(f"Error: {e}")
        raise typer.Exit(1) from e
    typer.echo(
        json.dumps(
            {
                "path": str(out),
                "mode": result.mode,
                "elements_added": result.elements_added,
                "elements_total": result.elements_total,
                "embed": _embed(out),
            }
        )
    )


def cmd_excalidraw_inspect(path: Path) -> None:
    """Report how many live elements a drawing holds, so callers know whether a render will append."""
    try:
        doc = read_drawing(path)
    except (DrawingFileError, ValueError, OSError) as e:
        typer.echo(f"Error: {e}")
        raise typer.Exit(1) from e
    live = [el for el in doc.get("elements", []) if not el.get("isDeleted")]
    typer.echo(json.dumps({"path": str(path), "elements": len(live)}))
