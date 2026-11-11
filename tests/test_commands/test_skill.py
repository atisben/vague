"""Tests for skill commands."""

import json

import pytest
from typer.testing import CliRunner

from vague.sdk.cli import sdk_app
from vague.sdk.core.frontmatter import write_md

runner = CliRunner()

VALID_SKILL_FRONTMATTER = {
    "name": "test-skill",
    "version": "1.0.0",
    "description": "A test skill",
    "sdk_commands": ["vague context"],
    "requires_slug": True,
    "allowed-tools": ["Bash"],
}


def test_skill_validate_passes_on_valid(tmp_path, vague_home):
    skill_dir = tmp_path / "my-skill"
    skill_dir.mkdir()
    write_md(skill_dir / "SKILL.md", VALID_SKILL_FRONTMATTER, body="# Test")
    result = runner.invoke(sdk_app, ["skill-validate", str(skill_dir)])
    assert result.exit_code == 0
    assert "OK" in result.output


def test_skill_validate_fails_missing_required_field(tmp_path, vague_home):
    skill_dir = tmp_path / "bad-skill"
    skill_dir.mkdir()
    # Missing 'description'
    write_md(skill_dir / "SKILL.md", {"name": "bad-skill", "version": "1.0.0"}, body="")
    result = runner.invoke(sdk_app, ["skill-validate", str(skill_dir)])
    assert result.exit_code != 0


def test_skill_audit_detects_bs_patterns(tmp_path, vague_home):
    skill_dir = tmp_path / "legacy-skill"
    skill_dir.mkdir()
    write_md(skill_dir / "SKILL.md", VALID_SKILL_FRONTMATTER, body="""
## Preamble
```bash
bs-config get proactive
bs-learnings-log '{"skill":"test"}'
source "$(dirname "$0")/../_preamble.sh"
```
""")
    result = runner.invoke(sdk_app, ["skill-audit", str(skill_dir)])
    assert "legacy" in result.output.lower() or "WARNINGS" in result.output


def test_skill_audit_clean_on_current_skill(tmp_path, vague_home):
    skill_dir = tmp_path / "clean-skill"
    skill_dir.mkdir()
    write_md(skill_dir / "SKILL.md", VALID_SKILL_FRONTMATTER, body="""
## Preamble
```bash
eval "$(vague context --shell --skill clean-skill)"
vague memory-log some-key "a fact"
```
""")
    result = runner.invoke(sdk_app, ["skill-audit", str(skill_dir)])
    assert result.exit_code == 0
    assert "OK" in result.output


@pytest.mark.parametrize("command", [
    "vague learnings-log '{}'", "vague learnings-search docker", "vague observations-log '{}'",
    "vague timeline-log '{}'", "CONTEXT=$(vague init)",
])
def test_skill_audit_flags_removed_vague_commands(tmp_path, vague_home, command):
    skill_dir = tmp_path / "old-vague-skill"
    skill_dir.mkdir()
    write_md(skill_dir / "SKILL.md", VALID_SKILL_FRONTMATTER, body=f"```bash\n{command}\n```\n")
    result = runner.invoke(sdk_app, ["skill-audit", str(skill_dir)])
    assert "WARNINGS: 1" in result.output


def test_bundled_skills_have_no_requires_planning():
    from vague.sdk.commands.skill import _get_assets_skills_dir

    template = _get_assets_skills_dir().parent / "templates" / "SKILL.template.md"
    for skill_md in [*_get_assets_skills_dir().glob("*/SKILL.md"), template]:
        assert "requires_planning" not in skill_md.read_text(encoding="utf-8"), skill_md


def test_skill_audit_flags_preamble_without_skill_flag(tmp_path, vague_home):
    skill_dir = tmp_path / "no-telemetry-skill"
    skill_dir.mkdir()
    write_md(skill_dir / "SKILL.md", VALID_SKILL_FRONTMATTER, body="""
## Preamble
```bash
eval "$(vague context --shell)"
```
""")
    result = runner.invoke(sdk_app, ["skill-audit", str(skill_dir)])
    assert "WARNINGS" in result.output


def test_skill_audit_accepts_preamble_with_skill_flag(tmp_path, vague_home):
    skill_dir = tmp_path / "telemetry-skill"
    skill_dir.mkdir()
    write_md(skill_dir / "SKILL.md", VALID_SKILL_FRONTMATTER, body="""
## Preamble
```bash
eval "$(vague context --shell --skill telemetry-skill)"
```
""")
    result = runner.invoke(sdk_app, ["skill-audit", str(skill_dir)])
    assert result.exit_code == 0
    assert "OK" in result.output


def test_bundled_skills_preambles_capture_usage():
    """Every bundled skill that runs the context preamble must pass --skill."""
    from vague.sdk.commands.skill import _get_assets_skills_dir

    for skill_dir in sorted(_get_assets_skills_dir().iterdir()):
        if not skill_dir.is_dir() or not (skill_dir / "SKILL.md").exists():
            continue
        content = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
        assert "vague context --shell)" not in content, (
            f"{skill_dir.name}: preamble missing --skill {skill_dir.name}"
        )


def test_skill_list_returns_json(vague_home):
    result = runner.invoke(sdk_app, ["skill-list"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert isinstance(data, list)
