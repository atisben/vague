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
