"""Drift guards: docs must list every bundled skill, and skills may only call commands that exist."""

import re
from pathlib import Path

from vague.sdk.commands.skill import _get_assets_skills_dir

REPO_ROOT = Path(__file__).parent.parent

# Commands removed by the memory ledger redesign. A reference to one is a broken instruction.
REMOVED_COMMANDS = (
    "init",
    "learnings-log",
    "learnings-search",
    "observations-log",
    "observations-list",
    "observations-update",
    "timeline-log",
    "plan-list",
    "plan-status",
    "plan-complete",
    "state-get",
    "state-set",
    "memory-review",
    "memory-search --all",
)


def _skill_names() -> list[str]:
    return sorted(d.name for d in _get_assets_skills_dir().iterdir() if d.is_dir())


def test_readme_lists_every_skill():
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    missing = [name for name in _skill_names() if f"/{name}" not in readme]
    assert not missing, f"README.md skill map is missing: {missing}"


def _vague_commands_called_by_skills() -> dict[str, set[str]]:
    """Map each `vague <command>` written in a skill's code (fenced blocks, inline code) to the skills using it."""
    calls: dict[str, set[str]] = {}
    for skill_md in _get_assets_skills_dir().glob("*/SKILL.md"):
        for command in _vague_commands_in(text=skill_md.read_text(encoding="utf-8")):
            calls.setdefault(command, set()).add(skill_md.parent.name)
    return calls


def _vague_commands_in(text: str) -> set[str]:
    code_pattern = re.compile(r"```.*?```|`[^`\n]+`", re.DOTALL)
    # `vague` only counts at the start of a shell command, so prose like "the vague repo" is ignored.
    command_pattern = re.compile(r"(?:^|\$\(|\||&&|;)\s*vague ([a-z][a-z0-9-]*)", re.MULTILINE)
    return {command for code in code_pattern.findall(text) for command in command_pattern.findall(code.strip("`"))}


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


def _instruction_files() -> list[Path]:
    """Every file that tells an agent or a reader which vague commands to run."""
    assets = _get_assets_skills_dir().parent
    return [
        *sorted(assets.glob("skills/*/SKILL.md")),
        assets / "templates" / "SKILL.template.md",
        assets / "claude" / "guidelines.md",
        REPO_ROOT / "CLAUDE.md",
        REPO_ROOT / "README.md",
        *sorted((REPO_ROOT / "docs").glob("*.md")),
    ]


def test_no_file_references_a_removed_command():
    pattern = re.compile(rf"\bvague ({'|'.join(re.escape(c) for c in REMOVED_COMMANDS)})\b")
    hits = {
        str(path.relative_to(REPO_ROOT)): sorted(set(pattern.findall(path.read_text(encoding="utf-8"))))
        for path in _instruction_files()
    }
    hits = {path: commands for path, commands in hits.items() if commands}
    assert not hits, f"files reference removed vague commands: {hits}"


def test_no_file_passes_the_removed_all_flag_to_memory_search():
    pattern = re.compile(r"memory-search[^\n`|]*\s--all\b")
    files = [*_instruction_files(), *sorted((REPO_ROOT / "docs").glob("*.html"))]
    hits = [str(p.relative_to(REPO_ROOT)) for p in files if pattern.search(p.read_text(encoding="utf-8"))]
    assert not hits, f"files still pass --all to memory-search, use --scope all: {hits}"


def test_no_file_references_the_removed_learn_skill():
    pattern = re.compile(r"/learn\b")
    hits = [
        str(p.relative_to(REPO_ROOT)) for p in _instruction_files() if pattern.search(p.read_text(encoding="utf-8"))
    ]
    assert not hits, f"files still route to the deleted /learn skill: {hits}"


def _frontmatter_commands(skill_md: Path) -> set[str]:
    frontmatter = skill_md.read_text(encoding="utf-8").split("\n---", 1)[0]
    block = re.search(r"^sdk_commands:\n((?:  - .*\n?)*)", frontmatter, re.MULTILINE)
    return set(re.findall(r"- vague ([a-z][a-z0-9-]*)", block.group(1))) if block else set()


def test_skills_declare_the_memory_commands_they_call():
    undeclared = {}
    for skill_md in _get_assets_skills_dir().glob("*/SKILL.md"):
        used = {c for c in _vague_commands_in(text=skill_md.read_text(encoding="utf-8")) if c.startswith("memory-")}
        missing = used - _frontmatter_commands(skill_md=skill_md)
        if missing:
            undeclared[skill_md.parent.name] = sorted(missing)
    assert not undeclared, f"sdk_commands is missing memory commands the skill calls: {undeclared}"


def test_skill_frontmatter_lists_only_existing_commands():
    import typer

    from vague.sdk.cli import sdk_app

    registered = set(typer.main.get_command(sdk_app).commands)
    unknown = {
        skill_md.parent.name: sorted(_frontmatter_commands(skill_md=skill_md) - registered)
        for skill_md in _get_assets_skills_dir().glob("*/SKILL.md")
    }
    unknown = {name: commands for name, commands in unknown.items() if commands}
    assert not unknown, f"sdk_commands lists vague commands that do not exist: {unknown}"


def test_guidelines_have_memory_section():
    guidelines = (_get_assets_skills_dir().parent / "claude" / "guidelines.md").read_text(encoding="utf-8")
    assert "\n## Memory\n" in guidelines
    for flag in ("--global", "--about", "--scratch", "--files", "--skill"):
        assert flag in guidelines, f"guidelines Memory section should explain {flag}"


def test_claude_md_lists_every_skill_with_the_real_count():
    claude_md = (REPO_ROOT / "CLAUDE.md").read_text(encoding="utf-8")
    names = _skill_names()
    assert f"{len(names)} skills" in claude_md
    missing = [name for name in names if f"`/{name}`" not in claude_md]
    assert not missing, f"CLAUDE.md routing table is missing: {missing}"


def test_readme_skill_count_matches():
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    count = len(_skill_names())
    assert f"{count} markdown-based LLM skills" in readme, f"README intro should state the real skill count ({count})"


def _bold_pack_dir() -> Path:
    return _get_assets_skills_dir() / "slides" / "bold-template-pack"


def _bold_index() -> dict:
    import json

    return json.loads((_bold_pack_dir() / "selection-index.json").read_text(encoding="utf-8"))


def test_bold_index_matches_template_folders():
    index = _bold_index()
    slugs = sorted(t["slug"] for t in index["templates"])
    folders = sorted(d.name for d in (_bold_pack_dir() / "templates").iterdir() if d.is_dir())
    assert slugs == folders
    assert index["template_count"] == len(slugs)


def test_bold_index_paths_exist():
    skill_dir = _bold_pack_dir().parent
    missing = [
        path
        for t in _bold_index()["templates"]
        for path in (t["preview_md"], t["design_md"])
        if not (skill_dir / path).is_file()
    ]
    assert not missing, f"selection-index.json points at missing files: {missing}"


def test_slides_skill_lists_every_bold_template():
    skill_md = (_bold_pack_dir().parent / "SKILL.md").read_text(encoding="utf-8")
    index = _bold_index()
    count = index["template_count"]
    assert f"lists {count} bold templates" in skill_md
    missing = [t["name"] for t in index["templates"] if t["name"] not in skill_md]
    assert not missing, f"slides SKILL.md bold template list is missing: {missing}"


def test_every_skill_preamble_passes_its_own_name_to_context():
    wrong = [
        skill_md.parent.name
        for skill_md in _get_assets_skills_dir().glob("*/SKILL.md")
        if f"vague context --shell --skill {skill_md.parent.name})" not in skill_md.read_text(encoding="utf-8")
    ]
    assert not wrong, f"preamble must run `vague context --shell --skill <own name>`: {wrong}"


def test_dev_develop_briefs_hand_memory_to_subagents():
    text = (_get_assets_skills_dir() / "dev-develop" / "SKILL.md").read_text(encoding="utf-8")
    assert "--scratch" in text, "subagents never run the preamble, so their brief must explain the scratchpad"
