"""Drift guards: docs must list every bundled skill."""

from pathlib import Path

from vague.sdk.commands.skill import _get_assets_skills_dir

REPO_ROOT = Path(__file__).parent.parent


def _skill_names() -> list[str]:
    return sorted(d.name for d in _get_assets_skills_dir().iterdir() if d.is_dir())


def test_readme_lists_every_skill():
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    missing = [name for name in _skill_names() if f"/{name}" not in readme]
    assert not missing, f"README.md skill map is missing: {missing}"


def _vague_commands_called_by_skills() -> dict[str, set[str]]:
    """Map each `vague <command>` written in a skill's code (fenced blocks, inline code) to the skills using it."""
    import re

    code_pattern = re.compile(r"```.*?```|`[^`\n]+`", re.DOTALL)
    # `vague` only counts at the start of a shell command, so prose like "the vague repo" is ignored.
    command_pattern = re.compile(r"(?:^|\$\(|\||&&|;)\s*vague ([a-z][a-z0-9-]*)", re.MULTILINE)
    calls: dict[str, set[str]] = {}
    for skill_md in _get_assets_skills_dir().glob("*/SKILL.md"):
        text = skill_md.read_text(encoding="utf-8")
        for code in code_pattern.findall(text):
            for command in command_pattern.findall(code.strip("`")):
                calls.setdefault(command, set()).add(skill_md.parent.name)
    return calls


def test_skills_only_call_existing_vague_commands():
    import typer

    from vague.sdk.cli import sdk_app

    registered = set(typer.main.get_command(sdk_app).commands)
    unknown = {
        command: sorted(skills)
        for command, skills in _vague_commands_called_by_skills().items()
        if command not in registered
    }
    assert not unknown, f"skills call vague commands that do not exist: {unknown}"


def test_readme_skill_count_matches():
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    count = len(_skill_names())
    assert f"{count} markdown-based LLM skills" in readme, (
        f"README intro should state the real skill count ({count})"
    )
