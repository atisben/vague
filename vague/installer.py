"""vague install — installs skills into LLM runtime directories."""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path
from typing import Optional

import typer


RUNTIME_DIRS: dict[str, tuple[Optional[str], str, Optional[str]]] = {
    # (base_dir, skills_dir, instruction_file)
    "claude": ("~/.claude/", "~/.claude/skills/", "~/.claude/CLAUDE.md"),
    "copilot": ("~/.copilot/", "~/.copilot/skills/", "~/.copilot/instructions.md"),
    "cursor": ("~/.cursor/", "~/.cursor/skills/", "~/.cursor/rules/vague.mdc"),
    "windsurf": ("~/.codeium/windsurf/", "~/.codeium/windsurf/skills/", None),
    "generic": (None, "~/skills/", None),
}

MARKER_START = "<!-- vague:start -->"
MARKER_END = "<!-- vague:end -->"
LEGACY_MARKER_START = "<!-- bastack:start -->"
LEGACY_MARKER_END = "<!-- bastack:end -->"


def _detect_runtimes() -> list[str]:
    """Return all runtimes whose base_dir exists on this machine."""
    found = []
    for key, (base_dir, _, _) in RUNTIME_DIRS.items():
        if base_dir is None:
            continue
        if Path(base_dir).expanduser().exists():
            found.append(key)
    return found


def _detect_runtime() -> str:
    """Legacy single-runtime detection. Returns first detected or 'generic'."""
    runtimes = _detect_runtimes()
    return runtimes[0] if runtimes else "generic"


def _get_assets_dir() -> Path:
    return Path(__file__).parent / "assets"


def _get_instructions_block() -> str:
    """Read the instructions block template."""
    template = _get_assets_dir() / "templates" / "instructions-block.md"
    if not template.exists():
        return ""
    return template.read_text()


def _update_instruction_file(runtime: str, skills_path: Path) -> None:
    """Insert or replace the vague instructions block in the runtime's instruction file."""
    _, _, instruction_file_str = RUNTIME_DIRS[runtime]
    if instruction_file_str is None:
        return

    instruction_file = Path(instruction_file_str).expanduser()
    if not instruction_file.parent.exists():
        return

    block_content = _get_instructions_block()
    if not block_content:
        return

    wrapped_block = f"{MARKER_START}\n{block_content}\n{MARKER_END}"

    if instruction_file.exists():
        try:
            content = instruction_file.read_text()
        except PermissionError:
            typer.echo(f"Warning: cannot read {instruction_file} (permission denied)", err=True)
            return

        # Replace existing vague block
        for start_marker, end_marker in [
            (MARKER_START, MARKER_END),
            (LEGACY_MARKER_START, LEGACY_MARKER_END),
        ]:
            start_idx = content.find(start_marker)
            end_idx = content.find(end_marker)
            if start_idx != -1 and end_idx != -1:
                end_idx += len(end_marker)
                content = content[:start_idx] + wrapped_block + content[end_idx:]
                try:
                    instruction_file.write_text(content)
                except PermissionError:
                    typer.echo(f"Warning: cannot write {instruction_file} (permission denied)", err=True)
                    return
                typer.echo(f"Updated {instruction_file}", err=True)
                return

        # No markers found — append
        separator = "\n\n" if content and not content.endswith("\n\n") else ("\n" if content and not content.endswith("\n") else "")
        content = content + separator + wrapped_block + "\n"
        try:
            instruction_file.write_text(content)
        except PermissionError:
            typer.echo(f"Warning: cannot write {instruction_file} (permission denied)", err=True)
            return
        typer.echo(f"Updated {instruction_file}", err=True)
    else:
        # File doesn't exist — skip (non-fatal)
        typer.echo(f"Skipped {instruction_file} (does not exist)", err=True)


def _remove_instruction_block(runtime: str) -> None:
    """Remove the vague instructions block from the runtime's instruction file."""
    _, _, instruction_file_str = RUNTIME_DIRS[runtime]
    if instruction_file_str is None:
        return

    instruction_file = Path(instruction_file_str).expanduser()
    if not instruction_file.exists():
        return

    try:
        content = instruction_file.read_text()
    except PermissionError:
        typer.echo(f"Warning: cannot read {instruction_file} (permission denied)", err=True)
        return

    for start_marker, end_marker in [
        (MARKER_START, MARKER_END),
        (LEGACY_MARKER_START, LEGACY_MARKER_END),
    ]:
        start_idx = content.find(start_marker)
        end_idx = content.find(end_marker)
        if start_idx != -1 and end_idx != -1:
            end_idx += len(end_marker)
            # Remove block and surrounding blank lines
            before = content[:start_idx].rstrip("\n")
            after = content[end_idx:].lstrip("\n")
            separator = "\n\n" if before and after else ""
            content = before + separator + after
            if content and not content.endswith("\n"):
                content += "\n"
            try:
                instruction_file.write_text(content)
            except PermissionError:
                typer.echo(f"Warning: cannot write {instruction_file} (permission denied)", err=True)
                return
            typer.echo(f"Cleaned {instruction_file}", err=True)
            return


def _install_to_runtime(runtime: str, assets: Path, skill_names: list[str]) -> int:
    """Install skills and instruction block to a single runtime. Returns count installed."""
    _, skills_target_str, _ = RUNTIME_DIRS[runtime]
    skills_target = Path(skills_target_str).expanduser()
    skills_src = assets / "skills"

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

    typer.echo(f"  {runtime}: {count} skill(s) → {skills_target}", err=True)

    agents_src = assets / "agents"
    if agents_src.exists() and any(f for f in agents_src.iterdir() if f.name != ".gitkeep"):
        agents_target = skills_target.parent / "agents"
        agents_target.mkdir(parents=True, exist_ok=True)
        for agent_file in agents_src.iterdir():
            if agent_file.name == ".gitkeep":
                continue
            shutil.copy2(agent_file, agents_target / agent_file.name)
        typer.echo(f"  {runtime}: agents → {agents_target}", err=True)

    _update_instruction_file(runtime, skills_target)
    return count


def cmd_install(
    runtime: Optional[str] = None,
) -> None:
    """Install vague skills into LLM runtime directories."""
    assets = _get_assets_dir()
    skills_src = assets / "skills"

    if not skills_src.exists():
        typer.echo(f"Error: no skills found in {skills_src}", err=True)
        raise typer.Exit(1)

    skill_names = sorted(d.name for d in skills_src.iterdir() if d.is_dir())

    if runtime is not None:
        if runtime not in RUNTIME_DIRS:
            typer.echo(
                f"Error: unknown runtime '{runtime}'. Choose from: {', '.join(RUNTIME_DIRS)}",
                err=True,
            )
            raise typer.Exit(1)
        runtimes = [runtime]
    else:
        runtimes = _detect_runtimes()
        if not runtimes:
            typer.echo("Error: no runtimes detected. Use --runtime to specify one.", err=True)
            raise typer.Exit(1)
        typer.echo(f"Detected runtimes: {', '.join(runtimes)}", err=True)

    typer.echo(f"\nThis will install {len(skill_names)} skill(s) to {len(runtimes)} runtime(s):")
    for rt in runtimes:
        _, skills_target_str, _ = RUNTIME_DIRS[rt]
        skills_target = Path(skills_target_str).expanduser()
        typer.echo(f"\n  [{rt}] {skills_target}")
        for name in skill_names:
            dest = skills_target / name
            status = " (overwrite)" if dest.exists() else ""
            typer.echo(f"    - {name}{status}")
    typer.echo()

    if not typer.confirm("Proceed?"):
        typer.echo("Aborted.", err=True)
        raise typer.Exit(0)

    total = 0
    for rt in runtimes:
        total += _install_to_runtime(rt, assets, skill_names)

    vague_path = shutil.which("vague")
    if vague_path is None:
        typer.echo("Warning: 'vague' is not on $PATH.", err=True)
    else:
        typer.echo(f"vague found at: {vague_path}", err=True)

    typer.echo(f"\nInstalled {total} skill(s) across {len(runtimes)} runtime(s).", err=True)


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
    if runtime is not None:
        if runtime not in RUNTIME_DIRS:
            typer.echo(
                f"Error: unknown runtime '{runtime}'. Choose from: {', '.join(RUNTIME_DIRS)}",
                err=True,
            )
            raise typer.Exit(1)
        runtimes = [runtime]
    else:
        runtimes = _detect_runtimes()
        if not runtimes:
            typer.echo("Error: no runtimes detected. Use --runtime to specify one.", err=True)
            raise typer.Exit(1)
        typer.echo(f"Detected runtimes: {', '.join(runtimes)}", err=True)

    vague_skills = _get_vague_skill_names()

    # Collect what's installed per runtime
    to_remove: dict[str, list[str]] = {}
    for rt in runtimes:
        _, skills_target_str, _ = RUNTIME_DIRS[rt]
        skills_target = Path(skills_target_str).expanduser()
        installed = sorted(
            name for name in vague_skills
            if (skills_target / name).is_dir()
        )
        if installed:
            to_remove[rt] = installed

    if not to_remove:
        typer.echo("No vague skills found to remove.", err=True)
        raise typer.Exit(0)

    total_skills = sum(len(v) for v in to_remove.values())
    typer.echo(f"\nThis will remove {total_skills} skill(s) from {len(to_remove)} runtime(s):")
    for rt, names in to_remove.items():
        _, skills_target_str, _ = RUNTIME_DIRS[rt]
        typer.echo(f"\n  [{rt}] {Path(skills_target_str).expanduser()}")
        for name in names:
            typer.echo(f"    - {name}")
    typer.echo()

    if not typer.confirm("Proceed?"):
        typer.echo("Aborted.", err=True)
        raise typer.Exit(0)

    removed = 0
    for rt, names in to_remove.items():
        _, skills_target_str, _ = RUNTIME_DIRS[rt]
        skills_target = Path(skills_target_str).expanduser()
        for name in names:
            shutil.rmtree(skills_target / name)
            removed += 1
        _remove_instruction_block(rt)
        typer.echo(f"  {rt}: removed {len(names)} skill(s)", err=True)

    typer.echo(f"\nRemoved {removed} skill(s) across {len(to_remove)} runtime(s).", err=True)
