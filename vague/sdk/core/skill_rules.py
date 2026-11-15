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

REQUIRED_FIELDS = ("name", "version", "description", "sdk_commands", "allowed-tools")

# Skills whose deliverable is a file the user must find later. Each logs it as a doc memory, which is how
# `vague status`, the preamble's document index and the usage graph learn the file exists.
FILE_WRITING_SKILLS = ("vault", "vault-clean", "vault-excalidraw", "slides", "plan-eng", "plan-ideation", "diagram")

# Hidden per-project document folders under $VAGUE_HOME, replaced by doc memories pointing at real files.
# Either the path is anchored on the vague home, or the slug segment is a placeholder a skill fills in.
_STATE_DIR_PATTERN = re.compile(
    r"(?:\.vague|VAGUE_HOME)[^\s`]*?/projects/[^\s/`]+/(?:designs|retros|diagrams)\b"
    r"|projects/(?:\$\{?SLUG\}?|\{slug\}|<slug>|\*|\.\.\.)/(?:designs|retros|diagrams)\b"
)
# A deliverable logged as a learning ("Saved X.") ranks among facts and never reaches the document index.
_SAVED_LEARNING_PATTERN = re.compile(r"memory-log\b(?![^\n]*--doc\b)[^\n]*?[\"'](?:Saved|Drew)\b")
_DOC_LOG_PATTERN = re.compile(r"vague memory-log\b[^\n]*--doc\b")

_CODE_PATTERN = re.compile(r"```.*?```|`[^`\n]+`", re.DOTALL)
# `vague` only counts at the start of a shell command, so prose like "the vague repo" is ignored.
# A command ends in a letter or digit, so a wildcard like `vague memory-*` is not read as a command.
_COMMAND_PATTERN = re.compile(r"(?:^|\$\(|\||&&|;)\s*vague ([a-z](?:[a-z0-9-]*[a-z0-9])?)(?![\w-])", re.MULTILINE)
# A fence tagged `text` shows sample output, such as the MEMORY block, not commands to run.
_TEXT_FENCE_PATTERN = re.compile(r"```text\n.*?```", re.DOTALL)


# A Markdown link target: `[text](target)` or `[text](target "title")`.
_LINK_PATTERN = re.compile(r"\]\(\s*<?([^)\s>]+)>?(?:\s+\"[^\"]*\")?\s*\)")
_URL_SCHEME_PATTERN = re.compile(r"^[a-z][a-z0-9+.-]*:", re.IGNORECASE)
_INLINE_CODE_PATTERN = re.compile(r"`([^`\n]+)`")


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
        command
        for code in _CODE_PATTERN.findall(_TEXT_FENCE_PATTERN.sub("", text))
        for command in _COMMAND_PATTERN.findall(code.strip("`"))
    }


def frontmatter_commands(frontmatter: dict) -> set[str]:
    """The vague commands a skill declares in its `sdk_commands` list."""
    declared = frontmatter.get("sdk_commands") or []
    return {m.group(1) for entry in declared if (m := re.match(r"vague ([a-z][a-z0-9-]*)", str(entry)))}


def memory_convention_findings(path: Path, text: str) -> list[str]:
    """Lines that still teach the old per-project document folders or log a deliverable as a learning."""
    findings: list[str] = []
    for number, line in enumerate(text.splitlines(), start=1):
        if match := _STATE_DIR_PATTERN.search(line):
            findings.append(f"{path}: reference-to-projects-state-dir: line {number}: `{match.group(0)}`, "
                            "log the document with `vague memory-log <key> ... --doc --files <path>` instead")
        if _SAVED_LEARNING_PATTERN.search(line):
            findings.append(f"{path}: saved-learning-convention: line {number}: a deliverable logged as a learning, "
                            "add --doc so it becomes a doc memory")
    return findings


def _strip_code(text: str) -> str:
    """Blank out code so an example link inside it is not checked, keeping line numbers intact."""
    return _CODE_PATTERN.sub(lambda m: re.sub(r"[^\n]", " ", m.group(0)), text)


def missing_reference_findings(skill_dir: Path) -> list[str]:
    """Rule `missing-reference`: every relative `.md` link in a skill's Markdown resolves inside the skill.

    Scans every `.md` file under the skill directory. A link counts when its target ends in `.md`,
    after dropping any `#anchor`. URLs (`https:`, `mailto:`), anchor-only links, absolute and home
    paths, and links written inside code are skipped. The target resolves against the linking file's
    own directory and must be an existing file under the skill directory: a link that climbs out of
    the skill breaks once the skill is symlinked into a runtime on its own.
    """
    root = skill_dir.resolve()
    findings: list[str] = []
    for path in sorted(skill_dir.rglob("*.md")):
        text = _strip_code(path.read_text(encoding="utf-8"))
        for number, line in enumerate(text.splitlines(), start=1):
            for target in _LINK_PATTERN.findall(line):
                relative = target.split("#", 1)[0]
                if not relative.endswith(".md") or _URL_SCHEME_PATTERN.match(relative):
                    continue
                if relative.startswith(("/", "~")):
                    continue
                resolved = (path.parent / relative).resolve()
                if not resolved.is_file() or not resolved.is_relative_to(root):
                    findings.append(f"{path}: missing-reference: line {number}: `{target}` does not exist in the skill")
    return findings


def missing_agent_findings(repo_root: Path, skill_dir: Path) -> list[str]:
    """Rule `missing-agent`: every agent a skill names is bundled in `vague/assets/agents/`.

    An agent name is an inline-code span that is exactly `<skill>-<word>[-<word>...]` in lowercase
    kebab case, on a line that contains the word "agent" (so "Agent tool", "subagent" and
    "subagent_type" count too). Example: "Spawn the `impeccable-motion-reviewer` agent" inside the
    impeccable skill. Every `.md` file under the skill directory is scanned. Other skill names
    (`vault-excalidraw` inside /vault) are skipped. Each remaining name must exist as
    `vague/assets/agents/<name>.md`, because the installer links only that directory into a
    runtime's `agents/`.

    `NOTICE.md` is skipped: a vendoring notice names the upstream agents that were dropped.

    Both conditions keep false positives out: a CSS class (`slides-container`) or an example key
    (`vault-perf-review-...`) sits in inline code but never on a line about agents. The cost is that
    an agent named in plain prose, or on a line without the word "agent", goes unchecked.
    """
    agents_dir = repo_root / "vague" / "assets" / "agents"
    agent_names = {p.stem for p in agents_dir.glob("*.md")} if agents_dir.is_dir() else set()
    skill_names = {d.name for d in skill_dirs(repo_root=repo_root)}
    pattern = re.compile(rf"{re.escape(skill_dir.name)}(?:-[a-z0-9]+)+")
    findings: list[str] = []
    for path in sorted(p for p in skill_dir.rglob("*.md") if p.name != "NOTICE.md"):
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if "agent" not in line.lower():
                continue
            for span in _INLINE_CODE_PATTERN.findall(line):
                if pattern.fullmatch(span) and span not in skill_names and span not in agent_names:
                    findings.append(f"{path}: missing-agent: line {number}: `{span}` is not in {agents_dir}")
    return findings


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

    findings += memory_convention_findings(path=skill_md, text=text)
    if name in FILE_WRITING_SKILLS and not _DOC_LOG_PATTERN.search(text):
        findings.append(f"{skill_md}: deliverable-doc-memory: a file-writing skill must log what it wrote with "
                        "`vague memory-log <key> ... --doc --files <path>`")

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
    findings += missing_reference_findings(skill_dir=skill_dir)
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
    findings += [f for directory in dirs for f in missing_agent_findings(repo_root=repo_root, skill_dir=directory)]

    for path in _instruction_files(repo_root=repo_root):
        text = path.read_text(encoding="utf-8")
        findings += [
            f"{path}: unknown-command: `vague {c}` is not a vague command"
            for c in sorted(vague_commands_in(text=text) - registered_commands())
        ]
        findings += memory_convention_findings(path=path, text=text)

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
