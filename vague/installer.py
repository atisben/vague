"""vague install — installs skills into LLM runtime directories."""

from __future__ import annotations

import re
import shutil
from pathlib import Path

import typer

from vague.config import CLAUDE_DIRS_KEY as CLAUDE_DIRS_HINT
from vague.config import claude_d_dir, claude_dirs, profile_name_for

RUNTIME_DIRS: dict[str, tuple[str | None, str, str | None]] = {
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

CLAUDE_RUNTIME = "claude"
BASE_FRAGMENT = "base.md"
DEFAULT_PROFILE = "default"


def _effective_runtime_dirs() -> dict[str, tuple[str | None, str, str | None]]:
    """Return RUNTIME_DIRS with the claude entry expanded into one key per profile.

    A user running several Claude profiles (work and personal, say) declares
    them in VAGUE_CLAUDE_DIRS. Each becomes its own runtime key —
    ``claude:work``, ``claude:personal`` — so every profile gets its own
    skills directory and its own rendered CLAUDE.md. When nothing is
    configured the static default is returned unchanged.
    """
    dirs = dict(RUNTIME_DIRS)
    profiles = claude_dirs()
    if not profiles:
        return dirs

    dirs.pop(CLAUDE_RUNTIME, None)
    for profile_dir in profiles:
        key = f"{CLAUDE_RUNTIME}:{profile_name_for(profile_dir)}"
        dirs[key] = (
            str(profile_dir),
            str(profile_dir / "skills"),
            str(profile_dir / "CLAUDE.md"),
        )
    return dirs


def _resolve_requested_runtimes(runtime: str) -> list[str]:
    """Expand a user-supplied --runtime into concrete runtime keys.

    ``claude`` selects every configured profile; ``claude:work`` selects one.
    An unknown name yields an empty list so the caller can report it.
    """
    dirs = _effective_runtime_dirs()
    if runtime in dirs:
        return [runtime]
    prefix = f"{runtime}:"
    return [key for key in dirs if key.startswith(prefix)]


def _profile_for_runtime(runtime: str) -> str | None:
    """Return the claude.d profile name for a runtime key, or None for non-Claude ones."""
    base, _, profile = runtime.partition(":")
    if base != CLAUDE_RUNTIME:
        return None
    return profile or DEFAULT_PROFILE


def _detect_runtimes() -> list[str]:
    """Return all runtimes whose base_dir exists on this machine."""
    found = []
    for key, (base_dir, _, _) in _effective_runtime_dirs().items():
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


def _remove_existing(path: Path) -> None:
    """Remove a file, directory, or symlink at path (handles broken symlinks)."""
    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.is_dir():
        shutil.rmtree(path)


def _parse_skill_trigger(skill_dir: Path) -> str | None:
    """Extract the Trigger: line from a skill's SKILL.md description."""
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        return None
    content = skill_md.read_text()

    # Extract the full description block (YAML frontmatter between ---)
    match = re.search(r"^---\n(.*?)\n---", content, re.DOTALL)
    if not match:
        return None
    frontmatter = match.group(1)

    # Find the Trigger: line(s) within the description field
    # Triggers can span multiple lines in the YAML description
    # Match from "Trigger:" to the end of the line (or continuation lines indented with spaces)
    trigger_match = re.search(r"Trigger:\s*(.+?)(?:\.\n|\.\Z)", frontmatter, re.DOTALL)
    if not trigger_match:
        return None

    trigger_text = trigger_match.group(1).strip()
    # Clean up multiline triggers (remove newline + leading spaces)
    trigger_text = re.sub(r"\n\s+", " ", trigger_text)
    return trigger_text


def _find_marker_span(content: str, start_marker: str, end_marker: str) -> tuple[int, int] | None:
    """Locate a managed block, requiring each marker to sit alone on its line.

    Prose that quotes a marker — "everything below the vague:start line is
    generated" — is documentation, not a boundary. Matching it would splice
    the block in mid-sentence and silently destroy the user's own content
    after that point.
    """
    start_pattern = re.compile(rf"^[ \t]*{re.escape(start_marker)}[ \t]*$", re.MULTILINE)
    end_pattern = re.compile(rf"^[ \t]*{re.escape(end_marker)}[ \t]*$", re.MULTILINE)

    start_match = start_pattern.search(content)
    if start_match is None:
        return None
    end_match = end_pattern.search(content, start_match.end())
    if end_match is None:
        return None
    return start_match.start(), end_match.end()


def _read_fragment(path: Path) -> str:
    """Read a claude.d fragment, returning '' if absent, unreadable, or blank."""
    if not path.is_file():
        return ""
    try:
        return path.read_text().strip()
    except OSError:
        return ""


def _get_instructions_block(profile: str | None = None) -> str:
    """Assemble the managed block: shared base, profile overlay, then skill routing.

    ``profile`` selects which overlay in ``claude.d/`` is included. Passing
    None (non-Claude runtimes) yields the skill table alone, so personal
    content never leaks into runtimes that did not ask for it.
    """
    skill_section = _build_skill_section()
    if not skill_section:
        return ""

    sections: list[str] = []
    if profile:
        source = claude_d_dir()
        for fragment in (source / BASE_FRAGMENT, source / f"{profile}.md"):
            text = _read_fragment(fragment)
            if text:
                sections.append(text)
    sections.append(skill_section.strip())

    return "\n\n".join(sections) + "\n"


def _build_skill_section() -> str:
    """Build the vague skill routing section from skill metadata."""
    template = _get_assets_dir() / "templates" / "instructions-block.md"
    if not template.exists():
        return ""

    skills_src = _get_assets_dir() / "skills"
    if not skills_src.exists():
        return template.read_text()

    skill_dirs = sorted(d for d in skills_src.iterdir() if d.is_dir())
    skill_count = len(skill_dirs)

    # Build routing table rows
    rows: list[str] = []
    for skill_dir in skill_dirs:
        trigger = _parse_skill_trigger(skill_dir)
        if trigger:
            rows.append(f"| {trigger} | `/{skill_dir.name}` |")

    # Build the full block
    lines = [
        "# vague",
        "",
        f"Personal development workflow toolkit. {skill_count} skills for the full software development lifecycle.",
        "",
        "## Skill Routing",
        "",
        "When the user's request matches a skill below, invoke it using the Skill tool as your FIRST action. Do NOT answer directly first.",  # noqa: E501
        "",
        "| Trigger | Skill |",
        "|---------|-------|",
        *rows,
        "",
        "## Skills Location",
        "",
        "Skills are symlinked into each configured runtime's `skills/` directory by `vague install`, pointing at this package's bundled `assets/skills/`. Edits to the bundled assets propagate live; re-run `vague install` only to add new runtimes or relink after reinstalling the package.",  # noqa: E501
        "",
        "## State",
        "",
        "All persistent state lives in `~/.vague/`. Never hardcode paths — always use `$VAGUE_HOME` or the default `~/.vague`.",  # noqa: E501
    ]
    return "\n".join(lines) + "\n"


def _update_instruction_file(runtime: str, skills_path: Path) -> None:
    """Insert or replace the vague instructions block in the runtime's instruction file."""
    _, _, instruction_file_str = _effective_runtime_dirs()[runtime]
    if instruction_file_str is None:
        return

    instruction_file = Path(instruction_file_str).expanduser()
    if not instruction_file.parent.exists():
        return

    block_content = _get_instructions_block(profile=_profile_for_runtime(runtime))
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
            span = _find_marker_span(content, start_marker, end_marker)
            if span is not None:
                start_idx, end_idx = span
                content = content[:start_idx] + wrapped_block + content[end_idx:]
                try:
                    instruction_file.write_text(content)
                except PermissionError:
                    typer.echo(f"Warning: cannot write {instruction_file} (permission denied)", err=True)
                    return
                typer.echo(f"Updated {instruction_file}", err=True)
                return

        # No markers found — append
        if content and not content.endswith("\n\n"):
            separator = "\n\n"
        elif content and not content.endswith("\n"):
            separator = "\n"
        else:
            separator = ""
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
    _, _, instruction_file_str = _effective_runtime_dirs()[runtime]
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
        span = _find_marker_span(content, start_marker, end_marker)
        if span is not None:
            start_idx, end_idx = span
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
    _, skills_target_str, _ = _effective_runtime_dirs()[runtime]
    skills_target = Path(skills_target_str).expanduser()
    skills_src = assets / "skills"

    skills_target.mkdir(parents=True, exist_ok=True)

    count = 0
    for skill_dir in skills_src.iterdir():
        if not skill_dir.is_dir():
            continue
        dest = skills_target / skill_dir.name
        _remove_existing(dest)
        dest.symlink_to(skill_dir.resolve(), target_is_directory=True)
        count += 1

    typer.echo(f"  {runtime}: {count} skill(s) symlinked → {skills_target}", err=True)

    agents_src = assets / "agents"
    if agents_src.exists() and any(f for f in agents_src.iterdir() if f.name != ".gitkeep"):
        agents_target = skills_target.parent / "agents"
        agents_target.mkdir(parents=True, exist_ok=True)
        for agent_file in agents_src.iterdir():
            if agent_file.name == ".gitkeep":
                continue
            dest = agents_target / agent_file.name
            _remove_existing(dest)
            dest.symlink_to(agent_file.resolve())
        typer.echo(f"  {runtime}: agents symlinked → {agents_target}", err=True)

    _update_instruction_file(runtime, skills_target)
    return count


BANNER = r"""
'||'  '|'                                  
 '|.  .'   ....     ... . ... ...    ....  
  ||  |   '' .||   || ||   ||  ||  .|...|| 
   |||    .|' ||    |''    ||  ||  ||      
    |     '|..'|'  '||||.  '|..'|.  '|...' 
                  .|....'                  
                                           
"""


def cmd_install(
    runtime: str | None = None,
) -> None:
    """Install vague skills into LLM runtime directories."""
    typer.echo(BANNER)

    assets = _get_assets_dir()
    skills_src = assets / "skills"

    if not skills_src.exists():
        typer.echo(f"Error: no skills found in {skills_src}", err=True)
        raise typer.Exit(1)

    skill_names = sorted(d.name for d in skills_src.iterdir() if d.is_dir())

    if runtime is not None:
        runtimes = _resolve_requested_runtimes(runtime)
        if not runtimes:
            typer.echo(
                f"Error: unknown runtime '{runtime}'. Choose from: {', '.join(_effective_runtime_dirs())}",
                err=True,
            )
            raise typer.Exit(1)
    else:
        runtimes = _detect_runtimes()
        if not runtimes:
            typer.echo("Error: no runtimes detected. Use --runtime to specify one.", err=True)
            raise typer.Exit(1)
        typer.echo(f"Detected runtimes: {', '.join(runtimes)}", err=True)

    effective = _effective_runtime_dirs()
    typer.echo(f"\nThis will install {len(skill_names)} skill(s) to {len(runtimes)} runtime(s):")
    for rt in runtimes:
        _, skills_target_str, _ = effective[rt]
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


def _strip_managed_block(content: str) -> str:
    """Return content with any vague-managed block removed."""
    for start_marker, end_marker in (
        (MARKER_START, MARKER_END),
        (LEGACY_MARKER_START, LEGACY_MARKER_END),
    ):
        span = _find_marker_span(content, start_marker, end_marker)
        if span is not None:
            start_idx, end_idx = span
            content = content[:start_idx] + content[end_idx:]
    return content.strip()


def cmd_claude_init(source: Path | None = None, force: bool = False) -> None:
    """Seed claude.d/ from an existing CLAUDE.md so nothing is lost on first sync.

    The pre-existing hand-written content becomes the shared ``base.md``; an
    empty overlay is created per configured profile, ready for anything that
    should apply to only one of them.
    """
    profiles = claude_dirs()
    if not profiles:
        typer.echo(
            f"Error: no Claude profiles configured. Set {CLAUDE_DIRS_HINT} in $VAGUE_HOME/config.env first.",
            err=True,
        )
        raise typer.Exit(1)

    if source is None:
        source = Path(profiles[0]) / "CLAUDE.md"

    target_dir = claude_d_dir()
    target_dir.mkdir(parents=True, exist_ok=True)

    base_file = target_dir / BASE_FRAGMENT
    if base_file.exists() and not force:
        typer.echo(f"Kept existing {base_file} (use --force to overwrite)", err=True)
    elif source.is_file():
        base_file.write_text(_strip_managed_block(source.read_text()) + "\n")
        typer.echo(f"Seeded {base_file} from {source}", err=True)
    else:
        base_file.write_text("")
        typer.echo(f"Created empty {base_file} ({source} not found)", err=True)

    for profile_dir in profiles:
        overlay = target_dir / f"{profile_name_for(profile_dir)}.md"
        if overlay.exists():
            continue
        overlay.write_text("")
        typer.echo(f"Created empty overlay {overlay}", err=True)

    typer.echo(
        "\nEdit these files, then run 'vague install' to render them into every profile.",
        err=True,
    )


def _get_vague_skill_names() -> set[str]:
    """Return the set of skill directory names bundled with vague."""
    skills_src = _get_assets_dir() / "skills"
    if not skills_src.exists():
        return set()
    return {d.name for d in skills_src.iterdir() if d.is_dir()}


def cmd_uninstall(
    runtime: str | None = None,
) -> None:
    """Remove vague skills from LLM runtime directories."""
    if runtime is not None:
        runtimes = _resolve_requested_runtimes(runtime)
        if not runtimes:
            typer.echo(
                f"Error: unknown runtime '{runtime}'. Choose from: {', '.join(_effective_runtime_dirs())}",
                err=True,
            )
            raise typer.Exit(1)
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
        _, skills_target_str, _ = _effective_runtime_dirs()[rt]
        skills_target = Path(skills_target_str).expanduser()
        installed = sorted(
            name for name in vague_skills if (skills_target / name).is_dir() or (skills_target / name).is_symlink()
        )
        if installed:
            to_remove[rt] = installed

    if not to_remove:
        typer.echo("No vague skills found to remove.", err=True)
        raise typer.Exit(0)

    total_skills = sum(len(v) for v in to_remove.values())
    typer.echo(f"\nThis will remove {total_skills} skill(s) from {len(to_remove)} runtime(s):")
    for rt, names in to_remove.items():
        _, skills_target_str, _ = _effective_runtime_dirs()[rt]
        typer.echo(f"\n  [{rt}] {Path(skills_target_str).expanduser()}")
        for name in names:
            typer.echo(f"    - {name}")
    typer.echo()

    if not typer.confirm("Proceed?"):
        typer.echo("Aborted.", err=True)
        raise typer.Exit(0)

    removed = 0
    for rt, names in to_remove.items():
        _, skills_target_str, _ = _effective_runtime_dirs()[rt]
        skills_target = Path(skills_target_str).expanduser()
        for name in names:
            _remove_existing(skills_target / name)
            removed += 1
        _remove_instruction_block(rt)
        typer.echo(f"  {rt}: removed {len(names)} skill(s)", err=True)

    typer.echo(f"\nRemoved {removed} skill(s) across {len(to_remove)} runtime(s).", err=True)
