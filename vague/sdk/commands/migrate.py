"""vague migrate: move the pre-ledger stores into memory.jsonl and the events log."""

from __future__ import annotations

import typer

from vague.sdk.core.migrate import MigrationError, archive, build_plan, marker_path, migrate, report


def cmd_migrate(dry_run: bool, do_archive: bool) -> None:
    try:
        if do_archive:
            moved = archive()
            typer.echo(f"archived {len(moved)} paths under {marker_path().parent / 'archive'}")
            return
        if marker_path().exists():
            typer.echo(f"already migrated ({marker_path().read_text(encoding='utf-8').strip()}): nothing written")
            return
        plan = build_plan() if dry_run else migrate()
    except MigrationError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1) from e
    typer.echo("\n".join(report(plan=plan)))
    typer.echo("dry run: nothing written" if dry_run else f"migrated: marker written to {marker_path()}")
