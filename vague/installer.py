"""vague-install entry point — installs skills into LLM runtime directories."""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path
from typing import Optional

import typer

_install_app = typer.Typer(name="vague-install", help="Install vague skills into LLM runtimes.")

RUNTIME_DIRS = {
    "claude": ("~/.claude/", "~/.claude/skills/"),
    "copilot": ("~/.copilot/", "~/.copilot/skills/"),
    "cursor": ("~/.cursor/", "~/.cursor/skills/"),
    "windsurf": ("~/.codeium/windsurf/", "~/.codeium/windsurf/skills/"),
    "generic": (None, "~/skills/"),
}


def _detect_runtime() -> str:
    """Auto-detect the LLM runtime."""
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


@_install_app.command()
def install_cmd(
    runtime: Optional[str] = typer.Option(None, "--runtime", help="claude|copilot|cursor|windsurf|generic"),
    scope: str = typer.Option("local", "--scope", help="local|global"),
) -> None:
    """Install vague skills into LLM runtime directories."""
    if runtime is None:
        runtime = _detect_runtime()
        print(f"Detected runtime: {runtime}", file=sys.stderr)

    if runtime not in RUNTIME_DIRS:
        print(f"Error: unknown runtime '{runtime}'. Choose from: {', '.join(RUNTIME_DIRS)}", file=sys.stderr)
        raise typer.Exit(1)

    _, skills_target_str = RUNTIME_DIRS[runtime]
    skills_target = Path(skills_target_str).expanduser()
    skills_target.mkdir(parents=True, exist_ok=True)

    assets = _get_assets_dir()
    skills_src = assets / "skills"

    if skills_src.exists():
        count = 0
        for skill_dir in skills_src.iterdir():
            if not skill_dir.is_dir():
                continue
            dest = skills_target / skill_dir.name
            if dest.exists():
                shutil.rmtree(dest)
            shutil.copytree(skill_dir, dest)
            count += 1
        print(f"Installed {count} skill(s) → {skills_target}", file=sys.stderr)
    else:
        print(f"Warning: no skills found in {skills_src}", file=sys.stderr)

    agents_src = assets / "agents"
    if agents_src.exists() and any(f for f in agents_src.iterdir() if f.name != ".gitkeep"):
        # Determine agents target (same parent as skills, agents subdir)
        agents_target = skills_target.parent / "agents"
        agents_target.mkdir(parents=True, exist_ok=True)
        for agent_file in agents_src.iterdir():
            if agent_file.name == ".gitkeep":
                continue
            shutil.copy2(agent_file, agents_target / agent_file.name)
        print(f"Installed agents → {agents_target}", file=sys.stderr)

    # Verify vague is on $PATH
    vague_path = shutil.which("vague")
    if vague_path is None:
        print("Warning: 'vague' is not on $PATH. Run: pip install vague", file=sys.stderr)
    else:
        print(f"vague found at: {vague_path}", file=sys.stderr)

    print("Installation complete.", file=sys.stderr)


def install_app() -> None:
    """Entry point for vague-install."""
    _install_app()
