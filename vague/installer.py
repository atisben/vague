"""vague install — installs skills into LLM runtime directories."""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path
from typing import Optional

import typer


RUNTIME_DIRS = {
    "claude": ("~/.claude/", "~/.claude/skills/"),
    "copilot": ("~/.copilot/", "~/.copilot/skills/"),
    "cursor": ("~/.cursor/", "~/.cursor/skills/"),
    "windsurf": ("~/.codeium/windsurf/", "~/.codeium/windsurf/skills/"),
    "generic": (None, "~/skills/"),
}


def _detect_runtime() -> str:
    if os.environ.get("CLAUDE_DIR") or Path("~/.claude/").expanduser().exists():
        return "claude"
    if Path("~/.copilot/").expanduser().exists():
        return "copilot"
    if Path("~/.cursor/").expanduser().exists():
        return "cursor"
    if Path("~/.codeium/windsurf/").expanduser().exists():
        return "windsurf"
    return "generic"


def _get_assets_dir() -> Path:
    return Path(__file__).parent / "assets"


def cmd_install(
    runtime: Optional[str] = None,
) -> None:
    """Install vague skills into LLM runtime directories."""
    if runtime is None:
        runtime = _detect_runtime()
        typer.echo(f"Detected runtime: {runtime}", err=True)

    if runtime not in RUNTIME_DIRS:
        typer.echo(
            f"Error: unknown runtime '{runtime}'. Choose from: {', '.join(RUNTIME_DIRS)}",
            err=True,
        )
        raise typer.Exit(1)

    _, skills_target_str = RUNTIME_DIRS[runtime]
    skills_target = Path(skills_target_str).expanduser()

    assets = _get_assets_dir()
    skills_src = assets / "skills"

    if not skills_src.exists():
        typer.echo(f"Error: no skills found in {skills_src}", err=True)
        raise typer.Exit(1)

    skill_names = sorted(d.name for d in skills_src.iterdir() if d.is_dir())

    typer.echo(f"\nThis will install {len(skill_names)} skill(s) to {skills_target}:")
    for name in skill_names:
        dest = skills_target / name
        status = " (overwrite)" if dest.exists() else ""
        typer.echo(f"  - {name}{status}")
    typer.echo()

    if not typer.confirm("Proceed?"):
        typer.echo("Aborted.", err=True)
        raise typer.Exit(0)

    skills_target.mkdir(parents=True, exist_ok=True)

    count = 0
    for skill_dir in skills_src.iterdir():
        if not skill_dir.is_dir():
            continue
        dest = skills_target / skill_dir.name
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(skill_dir, dest)
        count += 1

    typer.echo(f"Installed {count} skill(s) → {skills_target}", err=True)

    agents_src = assets / "agents"
    if agents_src.exists() and any(f for f in agents_src.iterdir() if f.name != ".gitkeep"):
        agents_target = skills_target.parent / "agents"
        agents_target.mkdir(parents=True, exist_ok=True)
        for agent_file in agents_src.iterdir():
            if agent_file.name == ".gitkeep":
                continue
            shutil.copy2(agent_file, agents_target / agent_file.name)
        typer.echo(f"Installed agents → {agents_target}", err=True)

    vague_path = shutil.which("vague")
    if vague_path is None:
        typer.echo("Warning: 'vague' is not on $PATH.", err=True)
    else:
        typer.echo(f"vague found at: {vague_path}", err=True)

    typer.echo("Installation complete.", err=True)


def _get_vague_skill_names() -> set[str]:
    """Return the set of skill directory names bundled with vague."""
    skills_src = _get_assets_dir() / "skills"
    if not skills_src.exists():
        return set()
    return {d.name for d in skills_src.iterdir() if d.is_dir()}


def cmd_uninstall(
    runtime: Optional[str] = None,
) -> None:
    """Remove vague skills from LLM runtime directories."""
    if runtime is None:
        runtime = _detect_runtime()
        typer.echo(f"Detected runtime: {runtime}", err=True)

    if runtime not in RUNTIME_DIRS:
        typer.echo(
            f"Error: unknown runtime '{runtime}'. Choose from: {', '.join(RUNTIME_DIRS)}",
            err=True,
        )
        raise typer.Exit(1)

    _, skills_target_str = RUNTIME_DIRS[runtime]
    skills_target = Path(skills_target_str).expanduser()

    vague_skills = _get_vague_skill_names()
    installed = sorted(
        name for name in vague_skills
        if (skills_target / name).is_dir()
    )

    if not installed:
        typer.echo("No vague skills found to remove.", err=True)
        raise typer.Exit(0)

    typer.echo(f"\nThis will remove {len(installed)} skill(s) from {skills_target}:")
    for name in installed:
        typer.echo(f"  - {name}")
    typer.echo()

    if not typer.confirm("Proceed?"):
        typer.echo("Aborted.", err=True)
        raise typer.Exit(0)

    for name in installed:
        shutil.rmtree(skills_target / name)

    typer.echo(f"Removed {len(installed)} skill(s).", err=True)
