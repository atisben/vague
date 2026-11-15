"""Rules every bundled skill and the docs that list them must follow.

Pure functions: they return findings and never print or exit, so the CLI and hooks
can share them.
"""

from __future__ import annotations

import re
from functools import cache
from pathlib import Path

from pydantic import ValidationError

from vague.models import SkillManifest
from vague.sdk.core.frontmatter import FrontmatterError, read_md

REQUIRED_FIELDS = ("name", "version", "description", "sdk_commands", "requires_slug", "allowed-tools")

# A reference to one of these is a broken instruction: the command no longer exists.
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
    "skill-validate",
    "skill-audit",
)

# Old bash tooling that predates the vague CLI.
BS_PATTERNS = (
    r"\bbs-config\b",
    r"\bbs-learnings-log\b",
    r"\bbs-learnings-search\b",
    r"\bbs-slug\b",
    r"\bbs-timeline-log\b",
    r"\bbs-analytics\b",
    r'source\s+["\']?.*_preamble\.sh',
)

_REMOVED_PATTERN = re.compile(rf"\bvague ({'|'.join(re.escape(c) for c in REMOVED_COMMANDS)})(?![\w-])")
_CODE_PATTERN = re.compile(r"```.*?```|`[^`\n]+`", re.DOTALL)
# `vague` only counts at the start of a shell command, so prose like "the vague repo" is ignored.
_COMMAND_PATTERN = re.compile(r"(?:^|\$\(|\||&&|;)\s*vague ([a-z][a-z0-9-]*)", re.MULTILINE)


def default_repo_root() -> Path:
    """The repo holding this package: README.md, CLAUDE.md and vague/assets/skills/ live there."""
    return Path(__file__).resolve().parents[3]


def skill_dirs(repo_root: Path) -> list[Path]:
    """Bundled skill directories, sorted by name."""
    skills_root = repo_root / "vague" / "assets" / "skills"
    if not skills_root.is_dir():
        return []
    return sorted(d for d in skills_root.iterdir() if (d / "SKILL.md").is_file())


def skill_dir_for(path: Path) -> Path | None:
    """The nearest directory at or above `path` that holds a SKILL.md, or None."""
    resolved = path.resolve()
    start = resolved if resolved.is_dir() else resolved.parent
    for candidate in (start, *start.parents):
        if (candidate / "SKILL.md").is_file():
            return candidate
    return None


@cache
def registered_commands() -> frozenset[str]:
    # Imported here because the CLI imports this module through the skill commands.
    import typer

    from vague.sdk.cli import sdk_app

    return frozenset(typer.main.get_command(sdk_app).commands)


def vague_commands_in(text: str) -> set[str]:
    """Each `vague <command>` written in code (fenced blocks or inline code)."""
    return {
        command for code in _CODE_PATTERN.findall(text) for command in _COMMAND_PATTERN.findall(code.strip("`"))
    }


def removed_commands_in(text: str) -> list[str]:
    """Removed vague commands and legacy bash tooling the text still mentions."""
    hits = [f"vague {c}" for c in sorted(set(_REMOVED_PATTERN.findall(text)))]
    hits += [match for pattern in BS_PATTERNS for match in sorted(set(re.findall(pattern, text)))]
    return hits


def frontmatter_commands(frontmatter: dict) -> set[str]:
    """The vague commands a skill declares in its `sdk_commands` list."""
    declared = frontmatter.get("sdk_commands") or []
    return {m.group(1) for entry in declared if (m := re.match(r"vague ([a-z][a-z0-9-]*)", str(entry)))}


def check_skill(skill_dir: Path) -> list[str]:
    """Findings for one skill directory, each as `<file>: <rule>: <detail>`. Empty means it passes."""
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.is_file():
        return [f"{skill_md}: structure: SKILL.md not found"]
    try:
        frontmatter = read_md(path=skill_md)
    except FrontmatterError as e:
        return [f"{skill_md}: frontmatter: {e}"]

    text = skill_md.read_text(encoding="utf-8")
    name = skill_dir.name
    findings: list[str] = []

    missing = [field for field in REQUIRED_FIELDS if field not in frontmatter]
    findings += [f"{skill_md}: frontmatter: missing required field `{field}`" for field in missing]
    if not missing:
        try:
            SkillManifest(**{k: v for k, v in frontmatter.items() if k in SkillManifest.model_fields})
        except ValidationError as e:
            findings.append(f"{skill_md}: frontmatter: invalid manifest: {e}")

    findings += [f"{skill_md}: removed-command: `{hit}` no longer exists" for hit in removed_commands_in(text=text)]

    if not re.search(rf"vague context --shell --skill {re.escape(name)}(?![\w-])", text):
        findings.append(f"{skill_md}: preamble: must run `vague context --shell --skill {name}`")

    used = vague_commands_in(text=text)
    declared = frontmatter_commands(frontmatter=frontmatter)
    registered = registered_commands()
    findings += [
        f"{skill_md}: unknown-command: `vague {c}` is not a vague command" for c in sorted(used - registered)
    ]
    findings += [
        f"{skill_md}: unknown-command: sdk_commands lists `vague {c}`, which is not a vague command"
        for c in sorted(declared - registered)
    ]
    findings += [
        f"{skill_md}: undeclared-command: `vague {c}` is used but missing from sdk_commands"
        for c in sorted(c for c in used - declared if c.startswith("memory-"))
    ]
    return findings


def _instruction_files(repo_root: Path) -> list[Path]:
    """Files outside the skills that tell an agent or a reader which vague commands to run."""
    assets = repo_root / "vague" / "assets"
    candidates = [
        assets / "templates" / "SKILL.template.md",
        assets / "claude" / "guidelines.md",
        repo_root / "CLAUDE.md",
        repo_root / "README.md",
        *sorted((repo_root / "docs").glob("*.md")),
    ]
    return [path for path in candidates if path.is_file()]


def check_repo(repo_root: Path) -> list[str]:
    """Findings for every bundled skill plus the docs that list them. Empty means it passes."""
    dirs = skill_dirs(repo_root=repo_root)
    findings = [finding for directory in dirs for finding in check_skill(skill_dir=directory)]

    for path in _instruction_files(repo_root=repo_root):
        hits = removed_commands_in(text=path.read_text(encoding="utf-8"))
        findings += [f"{path}: removed-command: `{hit}` no longer exists" for hit in hits]

    names = [d.name for d in dirs]
    readme, claude_md = repo_root / "README.md", repo_root / "CLAUDE.md"
    readme_text = readme.read_text(encoding="utf-8") if readme.is_file() else ""
    claude_text = claude_md.read_text(encoding="utf-8") if claude_md.is_file() else ""

    findings += [f"{readme}: skill-list: missing `/{n}`" for n in names if f"/{n}" not in readme_text]
    findings += [f"{claude_md}: skill-list: missing `/{n}`" for n in names if f"`/{n}`" not in claude_text]
    # The lookbehind stops "21 skills" from satisfying a count of 1.
    if not re.search(rf"(?<!\d){len(names)} markdown-based LLM skills", readme_text):
        findings.append(f"{readme}: skill-count: must state `{len(names)} markdown-based LLM skills`")
    if not re.search(rf"(?<!\d){len(names)} skills", claude_text):
        findings.append(f"{claude_md}: skill-count: must state `{len(names)} skills`")
    return findings
