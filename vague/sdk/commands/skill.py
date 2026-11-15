"""vague skill commands."""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import typer

from vague.sdk.core.events import log_context_access
from vague.sdk.core.skill_rules import check_repo, check_skill, default_repo_root, skill_dir_for


def _get_assets_skills_dir() -> Path:
    return Path(__file__).parent.parent.parent / "assets" / "skills"


def cmd_skill_list(validate: bool = False) -> None:
    """List skills in installed skill dirs."""
    skills_dir = _get_assets_skills_dir()
    if not skills_dir.exists():
        typer.echo("[]")
        return

    results = []
    for skill_dir in sorted(skills_dir.iterdir()):
        if not skill_dir.is_dir():
            continue
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            continue
        entry: dict = {"name": skill_dir.name, "path": str(skill_md)}
        if validate:
            errors = check_skill(skill_dir=skill_dir)
            entry["valid"] = not errors
            entry["errors"] = errors
        results.append(entry)

    typer.echo(json.dumps(results))


def cmd_skill_check(paths: list[str]) -> None:
    """Check the given skills, or every bundled skill and the docs listing them when no path is given."""
    if paths:
        findings: list[str] = []
        checked: set[Path] = set()
        for raw in paths:
            directory = skill_dir_for(path=Path(raw))
            if directory is None:
                findings.append(f"{raw}: structure: no SKILL.md at or above this path")
            elif directory not in checked:
                checked.add(directory)
                findings += check_skill(skill_dir=directory)
    else:
        findings = check_repo(repo_root=default_repo_root())

    for finding in findings:
        typer.echo(finding)
    if findings:
        typer.echo(f"FAILED: {len(findings)} finding(s)")
        raise typer.Exit(1)
    typer.echo("OK: no findings")


def cmd_skill_add(skill_dir: str) -> None:
    """Copy external skill to vague assets."""
    src = Path(skill_dir)
    if not src.exists():
        print(f"Error: {skill_dir} does not exist", file=sys.stderr)
        raise typer.Exit(1)

    skill_md = src / "SKILL.md"
    if not skill_md.exists():
        print(f"Error: SKILL.md not found in {skill_dir}", file=sys.stderr)
        raise typer.Exit(1)

    dest = _get_assets_skills_dir() / src.name
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(src, dest)
    log_context_access(kind="write", path=dest)
    typer.echo(f"OK: copied {src.name} to assets/skills/")
