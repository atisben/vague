"""Drift guards: docs must list every bundled skill, and skills may only call commands that exist.

The skill and doc rules live in vague.skill_rules so `vague skill-check` and the
pre-commit hook enforce the same thing. The tests below cover what those rules do not.
"""

import re
from pathlib import Path

from vague.skill_rules import check_repo, check_skill, read_md, skill_dirs

REPO_ROOT = Path(__file__).parent.parent
SKILLS_DIR = REPO_ROOT / "vague" / "assets" / "skills"


def test_repo_passes_every_skill_rule():
    assert check_repo(repo_root=REPO_ROOT) == []


def test_every_bundled_skill_passes_check_skill():
    findings = [f for d in skill_dirs(repo_root=REPO_ROOT) for f in check_skill(skill_dir=d)]
    assert findings == []


def _instruction_files() -> list[Path]:
    """Every file that tells an agent or a reader which vague commands to run."""
    assets = SKILLS_DIR.parent
    return [
        *sorted(assets.glob("skills/*/SKILL.md")),
        assets / "templates" / "SKILL.template.md",
        assets / "claude" / "guidelines.md",
        REPO_ROOT / "CLAUDE.md",
        REPO_ROOT / "README.md",
        *sorted((REPO_ROOT / "docs").glob("*.md")),
    ]


def test_guidelines_have_memory_section():
    guidelines = (SKILLS_DIR.parent / "claude" / "guidelines.md").read_text(encoding="utf-8")
    assert "\n## Memory\n" in guidelines
    for flag in ("--global", "--about", "--scratch", "--doc", "--files", "--skill"):
        assert flag in guidelines, f"guidelines Memory section should explain {flag}"


def _bold_pack_dir() -> Path:
    return SKILLS_DIR / "slides" / "bold-template-pack"


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


def test_dev_implement_briefs_hand_memory_to_subagents():
    text = (SKILLS_DIR / "dev-implement" / "SKILL.md").read_text(encoding="utf-8")
    assert "--scratch" in text, "subagents never run the preamble, so their brief must explain note memories"


def test_dev_implement_isolates_parallel_implementers_and_ends_with_dev_review():
    # Parallel implementers in one checkout share an index and HEAD, so each one gets its own worktree.
    text = (SKILLS_DIR / "dev-implement" / "SKILL.md").read_text(encoding="utf-8")
    assert "git worktree add" in text
    assert "integration branch" in text
    assert "/dev-review" in text


def test_retro_reads_the_session_log_and_the_observations():
    text = (SKILLS_DIR / "retro" / "SKILL.md").read_text(encoding="utf-8")
    assert "vague memory-search --kind observation" in text
    assert ".jsonl" in text, "the session log is the primary source a retro reads"


def test_adapted_upstream_skills_ship_license_and_notice():
    for name in ("dev-review", "dev-implement", "retro"):
        skill = SKILLS_DIR / name
        assert "MIT License" in (skill / "LICENSE").read_text(encoding="utf-8"), name
        assert "mattpocock/skills" in (skill / "NOTICE.md").read_text(encoding="utf-8"), name


def test_guidelines_tell_skills_to_record_files_written_outside_the_repo():
    guidelines = (SKILLS_DIR.parent / "claude" / "guidelines.md").read_text(encoding="utf-8")
    assert "Obsidian" in guidelines.split("\n## Memory\n", 1)[1]


IMPECCABLE_AGENTS = ("impeccable-finish-reviewer", "impeccable-motion-reviewer")


def _impeccable_dir() -> Path:
    return SKILLS_DIR / "impeccable"


def _impeccable_files() -> list[Path]:
    """The vendored skill and its reviewer agents. NOTICE.md is exempt: it describes what upstream ships."""
    agents_dir = SKILLS_DIR.parent / "agents"
    files = [p for p in sorted(_impeccable_dir().rglob("*.md")) if p.name != "NOTICE.md"]
    return [*files, *(agents_dir / f"{name}.md" for name in IMPECCABLE_AGENTS)]


def test_impeccable_does_not_call_the_upstream_launcher():
    # vague vendors neither the Rust engine nor its launcher, and the brief lives in memory, not in repo files.
    pattern = re.compile(r"scripts/impeccable|scripts_path|PRODUCT\.md|DESIGN\.md|\.impeccable/")
    files = _impeccable_files()
    assert files, "the impeccable skill is not vendored"
    hits = [
        f"{p.relative_to(REPO_ROOT)}:{n}: {line.strip()}"
        for p in files if p.is_file()
        for n, line in enumerate(p.read_text(encoding="utf-8").splitlines(), start=1) if pattern.search(line)
    ]
    assert not hits, "impeccable still references the upstream engine or its project files:\n" + "\n".join(hits)


def test_impeccable_ships_license_and_notice():
    license_text = (_impeccable_dir() / "LICENSE").read_text(encoding="utf-8")
    notice_text = (_impeccable_dir() / "NOTICE.md").read_text(encoding="utf-8")
    assert "Apache License" in license_text
    assert "pbakaus/impeccable" in notice_text


def test_impeccable_memory_log_examples_fit_the_600_char_limit():
    # memory-log rejects text over 600 characters, so a long direction contract belongs in a file, not a note.
    example = re.compile(r'vague memory-log \S+ "([^"]*)"')
    too_long, whole_contract = [], []
    for path in _impeccable_files():
        text = path.read_text(encoding="utf-8")
        name = path.relative_to(REPO_ROOT)
        too_long += [f"{name}: {len(m)} chars" for m in example.findall(text) if len(m) > 600]
        if "resends the whole contract" in text or "carries the whole direction" in text:
            whole_contract.append(str(name))
    assert not too_long, "memory-log examples over the 600-character limit:\n" + "\n".join(too_long)
    assert not whole_contract, "these files still re-log the whole direction contract:\n" + "\n".join(whole_contract)


def test_impeccable_reviewers_are_read_only_and_attributed():
    agents_dir = SKILLS_DIR.parent / "agents"
    for name in IMPECCABLE_AGENTS:
        fallback = _impeccable_dir() / "reference" / "degraded" / f"{name.removeprefix('impeccable-')}.md"
        for path in (agents_dir / f"{name}.md", fallback):
            text = path.read_text(encoding="utf-8")
            assert "Adapted from pbakaus/impeccable@2b86d9c (Apache-2.0)" in text, path
            assert "vague memory-search design-direction --scratch" in text, path
            assert "vague memory-search design- --kind learning --skill impeccable" in text, path
        frontmatter = read_md(path=agents_dir / f"{name}.md")
        assert frontmatter["name"] == name
        tools = {t.strip() for t in str(frontmatter["tools"]).split(",")}
        assert tools == {"Read", "Glob", "Grep", "Bash"}, tools


def test_dev_review_never_edits_files():
    # A review reports findings. Applying them belongs to the built-in `/code-review --fix` or the user.
    frontmatter = read_md(path=SKILLS_DIR / "dev-review" / "SKILL.md")
    assert {"Write", "Edit", "NotebookEdit"}.isdisjoint(frontmatter["allowed-tools"])
    assert "Agent" in frontmatter["allowed-tools"]
