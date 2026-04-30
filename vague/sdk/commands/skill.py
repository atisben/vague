"""vague skill commands."""

from __future__ import annotations

import json
import re
import shutil
import sys
from pathlib import Path
from typing import Optional

import typer

from vague.models import SkillManifest
from vague.sdk.core.frontmatter import read_md, FrontmatterError

# Patterns that indicate old bash tooling usage
BS_PATTERNS = [
    r"\bbs-config\b",
    r"\bbs-learnings-log\b",
    r"\bbs-learnings-search\b",
    r"\bbs-slug\b",
    r"\bbs-timeline-log\b",
    r"\bbs-analytics\b",
    r'source\s+["\']?.*_preamble\.sh',
]


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
            valid, errors = _validate_skill(skill_dir)
            entry["valid"] = valid
            entry["errors"] = errors
        results.append(entry)

    typer.echo(json.dumps(results))


def cmd_skill_validate(skill_dir: str) -> None:
    """Validate a skill dir against SkillManifest contract."""
    path = Path(skill_dir)
    valid, errors = _validate_skill(path)
    if valid:
        typer.echo(f"OK: {skill_dir}")
    else:
        for err in errors:
            print(f"Error: {err}", file=sys.stderr)
        raise typer.Exit(1)


def cmd_skill_audit(skill_dir: str, strict: bool = False) -> None:
    """Scan for raw bash patterns that should be vague commands."""
    path = Path(skill_dir)
    skill_md = path / "SKILL.md"
    if not skill_md.exists():
        print(f"Error: SKILL.md not found in {skill_dir}", file=sys.stderr)
        raise typer.Exit(1)

    content = skill_md.read_text(encoding="utf-8")
    findings = []
    for pattern in BS_PATTERNS:
        matches = re.findall(pattern, content)
        if matches:
            findings.append(f"Found legacy pattern '{pattern}': {matches[:3]}")

    if findings:
        for f in findings:
            print(f"Audit: {f}", file=sys.stderr)
        if strict:
            raise typer.Exit(1)
        typer.echo(f"WARNINGS: {len(findings)} legacy patterns found")
    else:
        typer.echo("OK: no legacy patterns found")


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
    typer.echo(f"OK: copied {src.name} to assets/skills/")


def _validate_skill(skill_dir: Path) -> tuple[bool, list[str]]:
    """Validate a skill directory. Returns (valid, errors)."""
    errors = []
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        return False, ["SKILL.md not found"]

    try:
        data = read_md(skill_md)
    except FrontmatterError as e:
        return False, [f"Frontmatter parse error: {e}"]

    required_fields = ["name", "version", "description"]
    for field in required_fields:
        if field not in data:
            errors.append(f"Missing required field: {field}")

    if not errors:
        try:
            SkillManifest(**{k: v for k, v in data.items() if k in SkillManifest.model_fields})
        except Exception as e:
            errors.append(f"Manifest validation error: {e}")

    return len(errors) == 0, errors
