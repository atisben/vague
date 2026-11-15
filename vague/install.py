"""vague install: link the bundled skills and agents into each runtime, and write its instruction block."""

from __future__ import annotations

import json
import os
import re
import shlex
import shutil
from dataclasses import dataclass
from pathlib import Path

import typer

from vague.config import claude_dirs, profile_name_for
from vague.paths import atomic_write
from vague.skill_rules import skill_trigger

MARKER_START = "<!-- vague:start -->"
MARKER_END = "<!-- vague:end -->"


@dataclass(frozen=True)
class Runtime:
    """Where one runtime keeps what vague installs. The installer never names a runtime outside `runtimes()`."""

    key: str  # "claude:personal"
    root: Path  # the runtime's own config dir: it exists when the runtime is installed
    skills_dir: Path
    instruction_file: Path | None  # where the vague:start block goes
    agents_dir: Path | None  # None: this runtime has no subagents
    settings_file: Path | None  # None: this runtime has no hooks


def _claude_runtime(root: Path, key: str) -> Runtime:
    return Runtime(key=key, root=root, skills_dir=root / "skills", instruction_file=root / "CLAUDE.md",
                   agents_dir=root / "agents", settings_file=root / "settings.json")


def runtimes() -> list[Runtime]:
    """Every runtime vague can install into: one per configured Claude profile, else ~/.claude."""
    profiles = claude_dirs()
    if not profiles:
        return [_claude_runtime(root=Path("~/.claude").expanduser(), key="claude")]
    return [_claude_runtime(root=d, key=f"claude:{profile_name_for(d)}") for d in profiles]


def resolve_runtimes(requested: str | None) -> list[Runtime]:
    """The runtimes a `--runtime` value selects. Exits 1 when it selects none.

    `claude` selects every profile, `claude:work` one. No value selects every runtime whose root exists.
    """
    available = runtimes()
    if requested is None:
        found = [r for r in available if r.root.exists()]
        if not found:
            typer.echo("Error: no runtimes detected. Use --runtime to specify one.", err=True)
            raise typer.Exit(1)
        typer.echo(f"Detected runtimes: {', '.join(r.key for r in found)}", err=True)
        return found
    chosen = [r for r in available if r.key == requested or r.key.startswith(f"{requested}:")]
    if not chosen:
        choices = ", ".join(r.key for r in available)
        typer.echo(f"Error: unknown runtime '{requested}'. Choose from: {choices}", err=True)
        raise typer.Exit(1)
    return chosen


def _get_assets_dir() -> Path:
    return Path(__file__).parent / "assets"


def _get_guidelines_file() -> Path:
    return _get_assets_dir() / "claude" / "guidelines.md"


def _bundled_skills() -> list[Path]:
    skills_src = _get_assets_dir() / "skills"
    return sorted(d for d in skills_src.iterdir() if d.is_dir()) if skills_src.is_dir() else []


def _agent_files() -> list[Path]:
    """vague's bundled subagent definitions."""
    agents_src = _get_assets_dir() / "agents"
    return sorted(f for f in agents_src.glob("*.md") if f.is_file()) if agents_src.is_dir() else []


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


def replace_block(text: str, block: str, start: str = MARKER_START, end: str = MARKER_END) -> str:
    """`text` with its managed block set to `block`. An empty `block` removes the block; text outside never changes.

    With no block yet, a non-empty one is appended after a blank line.
    """
    span = _find_marker_span(text, start, end)
    if block:
        wrapped = f"{start}\n{block}\n{end}"
        if span is not None:
            return text[:span[0]] + wrapped + text[span[1]:]
        # One blank line between the user's text and the block, however the text ends.
        separator = "" if not text or text.endswith("\n\n") else "\n" if text.endswith("\n") else "\n\n"
        return text + separator + wrapped + "\n"
    if span is None:
        return text
    before, after = text[:span[0]].rstrip("\n"), text[span[1]:].lstrip("\n")
    joined = before + ("\n\n" if before and after else "") + after
    return joined + "\n" if joined and not joined.endswith("\n") else joined


def write_instruction_block(runtime: Runtime, block: str) -> None:
    """Set the vague block in the runtime's instruction file. A missing file is skipped: vague never creates it."""
    path = runtime.instruction_file
    if path is None or not path.exists():
        if path is not None and block:
            typer.echo(f"Skipped {path} (does not exist)", err=True)
        return
    try:
        text = path.read_text()
        updated = replace_block(text=text, block=block)
        if updated != text:
            path.write_text(updated)
            typer.echo(f"{'Updated' if block else 'Cleaned'} {path}", err=True)
    except PermissionError:
        typer.echo(f"Warning: cannot update {path} (permission denied)", err=True)


def _get_instructions_block() -> str:
    """Assemble the managed block: public guidelines, then skill routing.

    Private, per-profile content belongs in the user's own file outside the markers, which install never
    touches. A missing guidelines file degrades to the skill section alone rather than failing the install.
    """
    skill_section = _build_skill_section()
    guidelines_file = _get_guidelines_file()
    guidelines = guidelines_file.read_text().strip() if guidelines_file.is_file() else ""
    return guidelines + "\n\n" + skill_section if guidelines else skill_section


def _build_skill_section() -> str:
    """Build the vague skill routing section from each skill's `Trigger:` phrases."""
    skill_dirs = _bundled_skills()
    skill_count = len(skill_dirs)
    rows = [f"| {trigger} | `/{d.name}` |" for d in skill_dirs if (trigger := skill_trigger(skill_dir=d))]

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


def _install_to_runtime(runtime: Runtime) -> int:
    """Link skills and agents, write the instruction block, wire the hooks. Returns the number of skills linked."""
    skills = _bundled_skills()
    runtime.skills_dir.mkdir(parents=True, exist_ok=True)
    _remove_dangling_skill_links(runtime.skills_dir, _get_assets_dir() / "skills")
    for skill_dir in skills:
        dest = runtime.skills_dir / skill_dir.name
        _remove_existing(dest)
        dest.symlink_to(skill_dir.resolve(), target_is_directory=True)
    typer.echo(f"  {runtime.key}: {len(skills)} skill(s) symlinked → {runtime.skills_dir}", err=True)

    agents = _agent_files()
    if runtime.agents_dir is not None and agents:
        runtime.agents_dir.mkdir(parents=True, exist_ok=True)
        for agent_file in agents:
            dest = runtime.agents_dir / agent_file.name
            _remove_existing(dest)
            dest.symlink_to(agent_file.resolve())
        typer.echo(f"  {runtime.key}: {len(agents)} agent(s) symlinked → {runtime.agents_dir}", err=True)

    write_instruction_block(runtime=runtime, block=_get_instructions_block())
    if runtime.settings_file is not None and install_hooks(settings_path=runtime.settings_file,
                                                            command=hook_command()):
        typer.echo(f"  {runtime.key}: usage hooks updated → {runtime.settings_file}", err=True)
    return len(skills)


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


def cmd_install(runtime: str | None = None) -> None:
    """Install vague skills into LLM runtime directories."""
    typer.echo(BANNER)
    skills = _bundled_skills()
    if not skills:
        typer.echo(f"Error: no skills found in {_get_assets_dir() / 'skills'}", err=True)
        raise typer.Exit(1)
    targets = resolve_runtimes(requested=runtime)

    typer.echo(f"\nThis will install {len(skills)} skill(s) to {len(targets)} runtime(s):")
    for target in targets:
        typer.echo(f"\n  [{target.key}] {target.skills_dir}")
        for skill_dir in skills:
            overwrite = " (overwrite)" if (target.skills_dir / skill_dir.name).exists() else ""
            typer.echo(f"    - {skill_dir.name}{overwrite}")
    typer.echo()
    if not typer.confirm("Proceed?"):
        typer.echo("Aborted.", err=True)
        raise typer.Exit(0)

    total = sum(_install_to_runtime(runtime=target) for target in targets)
    vague_path = shutil.which("vague")
    typer.echo(f"vague found at: {vague_path}" if vague_path else "Warning: 'vague' is not on $PATH.", err=True)
    typer.echo(f"\nInstalled {total} skill(s) across {len(targets)} runtime(s).", err=True)


def cmd_uninstall(runtime: str | None = None) -> None:
    """Remove vague skills, agents, instruction block and hooks from LLM runtime directories."""
    targets = resolve_runtimes(requested=runtime)
    names = [d.name for d in _bundled_skills()]
    installed = {
        target: [n for n in names if (target.skills_dir / n).is_dir() or (target.skills_dir / n).is_symlink()]
        for target in targets
    }
    installed = {target: found for target, found in installed.items() if found}
    if not installed:
        typer.echo("No vague skills found to remove.", err=True)
        raise typer.Exit(0)

    total = sum(len(found) for found in installed.values())
    typer.echo(f"\nThis will remove {total} skill(s) from {len(installed)} runtime(s):")
    for target, found in installed.items():
        typer.echo(f"\n  [{target.key}] {target.skills_dir}")
        for name in found:
            typer.echo(f"    - {name}")
    typer.echo()
    if not typer.confirm("Proceed?"):
        typer.echo("Aborted.", err=True)
        raise typer.Exit(0)

    for target, found in installed.items():
        for name in found:
            _remove_existing(target.skills_dir / name)
        write_instruction_block(runtime=target, block="")
        if target.agents_dir is not None:
            # Matched by name, so the user's own agents survive.
            for agent_file in _agent_files():
                if (target.agents_dir / agent_file.name).is_symlink():
                    (target.agents_dir / agent_file.name).unlink()
        if target.settings_file is not None:
            remove_hooks(settings_path=target.settings_file)
        typer.echo(f"  {target.key}: removed {len(found)} skill(s)", err=True)
    typer.echo(f"\nRemoved {total} skill(s) across {len(installed)} runtime(s).", err=True)
