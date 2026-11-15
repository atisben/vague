"""vague install — installs skills into LLM runtime directories."""

from __future__ import annotations

import json
import os
import re
import shlex
import shutil
from pathlib import Path

import typer

from vague.config import claude_dirs, profile_name_for
from vague.paths import atomic_write
from vague.sdk.core.frontmatter import FrontmatterError, read_md

RUNTIME_DIRS: dict[str, tuple[str | None, str, str | None]] = {
    # (base_dir, skills_dir, instruction_file)
    "claude": ("~/.claude/", "~/.claude/skills/", "~/.claude/CLAUDE.md"),
    "cursor": ("~/.cursor/", "~/.cursor/skills/", "~/.cursor/rules/vague.mdc"),
    "windsurf": ("~/.codeium/windsurf/", "~/.codeium/windsurf/skills/", None),
    "generic": (None, "~/skills/", None),
}

MARKER_START = "<!-- vague:start -->"
MARKER_END = "<!-- vague:end -->"

CLAUDE_RUNTIME = "claude"


def _effective_runtime_dirs() -> dict[str, tuple[str | None, str, str | None]]:
    """Return RUNTIME_DIRS with the claude entry expanded into one key per profile.

    A user running several Claude profiles (work and personal, say) declares
    them in VAGUE_CLAUDE_DIRS. Each becomes its own runtime key —
    ``claude:work``, ``claude:personal`` — so every profile gets its own
    skills directory and its own CLAUDE.md. When nothing is
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


def _detect_runtimes() -> list[str]:
    """Return all runtimes whose base_dir exists on this machine."""
    found = []
    for key, (base_dir, _, _) in _effective_runtime_dirs().items():
        if base_dir is None:
            continue
        if Path(base_dir).expanduser().exists():
            found.append(key)
    return found


def _get_assets_dir() -> Path:
    return Path(__file__).parent / "assets"


def _get_guidelines_file() -> Path:
    return _get_assets_dir() / "claude" / "guidelines.md"


def _remove_existing(path: Path) -> None:
    """Remove a file, directory, or symlink at path (handles broken symlinks)."""
    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.is_dir():
        shutil.rmtree(path)


def _remove_dangling_skill_links(skills_target: Path, skills_src: Path) -> None:
    """Drop links left behind by renamed or deleted vague skills.

    Only broken symlinks that point into vague's own skills directory are
    removed, so the user's own skills and links survive.
    """
    src_root = skills_src.resolve()
    for entry in skills_target.iterdir():
        if not entry.is_symlink() or entry.exists():
            continue
        if Path(os.readlink(entry)).parent.resolve() == src_root:
            entry.unlink()


def _is_claude_runtime(runtime: str) -> bool:
    """True for `claude` and every `claude:<profile>` key."""
    return runtime.split(":")[0] == CLAUDE_RUNTIME


def _skill_supports_runtime(skill_dir: Path, runtime: str) -> bool:
    """Whether a skill belongs in this runtime, from the optional `runtimes` list in its SKILL.md.

    A skill without the key goes everywhere. A skill that needs Claude-only features, such as
    subagents, lists `runtimes: [claude]` so cursor and windsurf never see a skill they cannot run.
    An unreadable SKILL.md counts as unrestricted: `vague skill-check` reports it, install does not.
    """
    try:
        runtimes = read_md(path=skill_dir / "SKILL.md").get("runtimes")
    except FrontmatterError:
        return True
    if not runtimes:
        return True
    return runtime.split(":")[0] in runtimes


def _agent_files(assets: Path) -> list[Path]:
    """vague's bundled subagent definitions. Only Claude runtimes read an `agents/` directory."""
    agents_src = assets / "agents"
    if not agents_src.is_dir():
        return []
    return sorted(f for f in agents_src.iterdir() if f.is_file() and f.suffix == ".md")


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


def _get_instructions_block(runtime: str | None = None) -> str:
    """Assemble the managed block: public guidelines, then skill routing.

    Every runtime gets the same guidelines; the routing table lists only the skills linked into that
    runtime, so Claude-only skills stay out of cursor's rules. Private, per-profile content belongs in
    the user's own file outside the markers, which install never touches.
    A missing guidelines file degrades to the skill section alone rather than
    failing the install.
    """
    skill_section = _build_skill_section(runtime=runtime)
    guidelines_file = _get_guidelines_file()
    guidelines = guidelines_file.read_text().strip() if guidelines_file.is_file() else ""
    if not guidelines:
        return skill_section
    return guidelines + "\n\n" + skill_section


def _build_skill_section(runtime: str | None = None) -> str:
    """Build the vague skill routing section from skill metadata.

    With a runtime, only the skills linked into it are listed, so cursor is never routed to a
    Claude-only skill it does not have.
    """
    skills_src = _get_assets_dir() / "skills"
    skill_dirs = sorted(d for d in skills_src.iterdir() if d.is_dir()) if skills_src.exists() else []
    if runtime is not None:
        skill_dirs = [d for d in skill_dirs if _skill_supports_runtime(d, runtime)]
    skill_count = len(skill_dirs)

    rows: list[str] = []
    for skill_dir in skill_dirs:
        trigger = _parse_skill_trigger(skill_dir)
        if trigger:
            rows.append(f"| {trigger} | `/{skill_dir.name}` |")

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

    block_content = _get_instructions_block(runtime=runtime)
    if not block_content:
        return

    wrapped_block = f"{MARKER_START}\n{block_content}\n{MARKER_END}"

    if instruction_file.exists():
        try:
            content = instruction_file.read_text()
        except PermissionError:
            typer.echo(f"Warning: cannot read {instruction_file} (permission denied)", err=True)
            return

        span = _find_marker_span(content, MARKER_START, MARKER_END)
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

    span = _find_marker_span(content, MARKER_START, MARKER_END)
    if span is None:
        return
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


def _install_to_runtime(runtime: str, assets: Path) -> int:
    """Install skills and instruction block to a single runtime. Returns count installed."""
    _, skills_target_str, _ = _effective_runtime_dirs()[runtime]
    skills_target = Path(skills_target_str).expanduser()
    skills_src = assets / "skills"

    skills_target.mkdir(parents=True, exist_ok=True)
    _remove_dangling_skill_links(skills_target, skills_src)

    count = 0
    for skill_dir in skills_src.iterdir():
        if not skill_dir.is_dir():
            continue
        dest = skills_target / skill_dir.name
        if not _skill_supports_runtime(skill_dir, runtime):
            # A link from an install that predates the restriction would keep the skill visible.
            if dest.is_symlink() and dest.resolve() == skill_dir.resolve():
                dest.unlink()
            continue
        _remove_existing(dest)
        dest.symlink_to(skill_dir.resolve(), target_is_directory=True)
        count += 1

    typer.echo(f"  {runtime}: {count} skill(s) symlinked → {skills_target}", err=True)

    agent_files = _agent_files(assets)
    if agent_files and _is_claude_runtime(runtime):
        agents_target = skills_target.parent / "agents"
        agents_target.mkdir(parents=True, exist_ok=True)
        for agent_file in agent_files:
            dest = agents_target / agent_file.name
            _remove_existing(dest)
            dest.symlink_to(agent_file.resolve())
        typer.echo(f"  {runtime}: {len(agent_files)} agent(s) symlinked → {agents_target}", err=True)

    _update_instruction_file(runtime, skills_target)
    if _is_claude_runtime(runtime):
        settings = skills_target.parent / "settings.json"
        if install_hooks(settings_path=settings, command=hook_command()):
            typer.echo(f"  {runtime}: usage hooks updated → {settings}", err=True)
    return count


HOOK_SUBCOMMAND = "log-event"
# (hook event, tool matcher). The matcher keeps the hook off Read, Bash and every other tool call:
# Skill marks a skill start, Write and Edit name a file written during one.
HOOKS: tuple[tuple[str, str | None], ...] = (("UserPromptSubmit", None), ("PostToolUse", "Skill|Write|Edit"))


def hook_command() -> str:
    """`vague log-event`, with an absolute path when known: a hook's PATH may not include `vague`."""
    found = shutil.which("vague")
    return f"{shlex.quote(found) if found else 'vague'} {HOOK_SUBCOMMAND}"


def _is_vague_hook(entry: object) -> bool:
    """Match by content, so a hand-added hook with another path to `vague` still counts."""
    command = entry.get("command") if isinstance(entry, dict) else None
    return isinstance(command, str) and f"vague {HOOK_SUBCOMMAND}" in command.replace("'", "")


def _load_settings(path: Path) -> dict | None:
    """The settings dict, {} when the file is absent, None when it cannot be trusted."""
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def install_hooks(settings_path: Path, command: str) -> bool:
    """Reconcile vague's hooks in a Claude settings.json with `HOOKS`. True when the file changed.

    A vague hook under the right event and matcher stays, so a hand-added one with another path to
    `vague` survives. Any other vague hook is removed, so a changed matcher reaches an existing file.
    Idempotent, keeps every other setting and hook, and refuses to touch a file it cannot parse:
    a broken settings.json is the user's to fix, not ours to overwrite.
    """
    settings = _load_settings(settings_path)
    if settings is None:
        typer.echo(f"  Skipped hooks: {settings_path} is not valid JSON.", err=True)
        return False
    hooks = settings.setdefault("hooks", {})
    wanted = {event: matcher for event, matcher in HOOKS}
    changed = False
    for event in list(hooks):
        groups = hooks[event] if isinstance(hooks[event], list) else []
        kept_groups = []
        for group in groups:
            current = event in wanted and isinstance(group, dict) and group.get("matcher") == wanted[event]
            if isinstance(group, dict) and not current:
                kept = [h for h in group.get("hooks", []) if not _is_vague_hook(h)]
                if len(kept) != len(group.get("hooks", [])):
                    changed = True
                    if not kept:
                        continue
                    group["hooks"] = kept
            kept_groups.append(group)
        if isinstance(hooks[event], list):
            hooks[event] = kept_groups
            if not kept_groups and event not in wanted:
                del hooks[event]
    for event, matcher in HOOKS:
        groups = hooks.setdefault(event, [])
        if any(
            _is_vague_hook(h) for g in groups if isinstance(g, dict) and g.get("matcher") == matcher
            for h in g.get("hooks", [])
        ):
            continue
        group: dict = {"hooks": [{"type": "command", "command": command}]}
        if matcher:
            group = {"matcher": matcher, **group}
        groups.append(group)
        changed = True
    if changed:
        atomic_write(path=settings_path, text=json.dumps(settings, indent=2) + "\n")
    return changed


def remove_hooks(settings_path: Path) -> bool:
    """Remove only vague's hooks, and any container left empty. True when the file changed."""
    settings = _load_settings(settings_path)
    hooks = settings.get("hooks") if settings else None
    if not isinstance(hooks, dict):
        return False
    changed = False
    for event in list(hooks):
        groups = hooks[event] if isinstance(hooks[event], list) else []
        for group in groups:
            if isinstance(group, dict):
                kept = [h for h in group.get("hooks", []) if not _is_vague_hook(h)]
                changed |= len(kept) != len(group.get("hooks", []))
                group["hooks"] = kept
        hooks[event] = [g for g in groups if not (isinstance(g, dict) and g.get("hooks") == [])]
        if not hooks[event]:
            del hooks[event]
    if not hooks:
        del settings["hooks"]
    if changed:
        atomic_write(path=settings_path, text=json.dumps(settings, indent=2) + "\n")
    return changed


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
            if not _skill_supports_runtime(skills_src / name, rt):
                continue
            dest = skills_target / name
            status = " (overwrite)" if dest.exists() else ""
            typer.echo(f"    - {name}{status}")
    typer.echo()

    if not typer.confirm("Proceed?"):
        typer.echo("Aborted.", err=True)
        raise typer.Exit(0)

    total = 0
    for rt in runtimes:
        total += _install_to_runtime(rt, assets)

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


def _remove_agent_links(agents_target: Path) -> None:
    """Remove the agent links install created, matched by name, so the user's own agents survive."""
    if not agents_target.is_dir():
        return
    for agent_file in _agent_files(_get_assets_dir()):
        dest = agents_target / agent_file.name
        if dest.is_symlink():
            dest.unlink()


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
        if _is_claude_runtime(rt):
            _remove_agent_links(agents_target=skills_target.parent / "agents")
            remove_hooks(settings_path=skills_target.parent / "settings.json")
        typer.echo(f"  {rt}: removed {len(names)} skill(s)", err=True)

    typer.echo(f"\nRemoved {removed} skill(s) across {len(to_remove)} runtime(s).", err=True)
