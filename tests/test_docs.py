"""Drift guards: docs must list every bundled skill, and skills may only call commands that exist.

The skill and doc rules live in vague.sdk.core.skill_rules so `vague skill-check` and the
pre-commit hook enforce the same thing. The tests below cover what those rules do not.
"""

import re
from pathlib import Path

from vague.sdk.commands.skill import _get_assets_skills_dir
from vague.sdk.core.skill_rules import check_repo, check_skill, skill_dirs

REPO_ROOT = Path(__file__).parent.parent


def test_repo_passes_every_skill_rule():
    assert check_repo(repo_root=REPO_ROOT) == []


def test_every_bundled_skill_passes_check_skill():
    findings = [f for d in skill_dirs(repo_root=REPO_ROOT) for f in check_skill(skill_dir=d)]
    assert findings == []


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


def test_guidelines_have_memory_section():
    guidelines = (_get_assets_skills_dir().parent / "claude" / "guidelines.md").read_text(encoding="utf-8")
    assert "\n## Memory\n" in guidelines
    for flag in ("--global", "--about", "--scratch", "--files", "--skill"):
        assert flag in guidelines, f"guidelines Memory section should explain {flag}"


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


def test_dev_develop_briefs_hand_memory_to_subagents():
    text = (_get_assets_skills_dir() / "dev-develop" / "SKILL.md").read_text(encoding="utf-8")
    assert "--scratch" in text, "subagents never run the preamble, so their brief must explain the scratchpad"


# Skills whose deliverable is a file the user must be able to find later, so the usage graph can show it.
FILE_WRITING_SKILLS = ("vault", "vault-excalidraw", "slides")


def test_file_writing_skills_record_the_files_they_write():
    for name in FILE_WRITING_SKILLS:
        text = (_get_assets_skills_dir() / name / "SKILL.md").read_text(encoding="utf-8")
        assert re.search(r"memory-log .*--files", text), f"{name} must log the files it writes with --files"


def test_guidelines_tell_skills_to_record_files_written_outside_the_repo():
    guidelines = (_get_assets_skills_dir().parent / "claude" / "guidelines.md").read_text(encoding="utf-8")
    assert "Obsidian" in guidelines.split("\n## Memory\n", 1)[1]
