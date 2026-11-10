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


def test_readme_skill_count_matches():
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    count = len(_skill_names())
    assert f"{count} markdown-based LLM skills" in readme, (
        f"README intro should state the real skill count ({count})"
    )


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
