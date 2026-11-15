"""Tests for skill commands."""

import json

import pytest
from typer.testing import CliRunner

from vague.sdk.cli import sdk_app

runner = CliRunner()

def test_skill_check_passes_on_valid_skill(skill_dir):
    result = runner.invoke(sdk_app, ["skill-check", str(skill_dir())])
    assert result.exit_code == 0
    assert "OK" in result.output


def test_skill_check_exits_1_on_findings(skill_dir):
    result = runner.invoke(sdk_app, ["skill-check", str(skill_dir(omit=("description",)))])
    assert result.exit_code == 1
    assert "description" in result.output


def test_skill_check_accepts_a_file_inside_the_skill(skill_dir):
    directory = skill_dir(omit=("version",))
    result = runner.invoke(sdk_app, ["skill-check", str(directory / "SKILL.md")])
    assert result.exit_code == 1
    assert "version" in result.output


def test_skill_check_reports_a_path_outside_any_skill(tmp_path):
    result = runner.invoke(sdk_app, ["skill-check", str(tmp_path)])
    assert result.exit_code == 1
    assert "SKILL.md" in result.output


@pytest.mark.parametrize("command", [
    "vague learnings-log '{}'", "vague learnings-search docker", "vague observations-log '{}'",
    "vague timeline-log '{}'", "CONTEXT=$(vague init)", "bs-learnings-log '{}'",
])
def test_skill_check_flags_removed_commands(skill_dir, command):
    preamble = '```bash\neval "$(vague context --shell --skill demo-skill)"\n```\n'
    result = runner.invoke(sdk_app, ["skill-check", str(skill_dir(body=f"{preamble}```bash\n{command}\n```\n"))])
    assert result.exit_code == 1
    assert "removed" in result.output


def test_skill_check_flags_preamble_without_skill_flag(skill_dir):
    result = runner.invoke(
        sdk_app, ["skill-check", str(skill_dir(body='```bash\neval "$(vague context --shell)"\n```\n'))]
    )
    assert result.exit_code == 1
    assert "--skill demo-skill" in result.output


def test_skill_check_without_paths_checks_all_skills_and_docs(tmp_path, skill_dir, monkeypatch):
    skill_dir(name="alpha", root=tmp_path / "vague" / "assets" / "skills")
    (tmp_path / "README.md").write_text("1 markdown-based LLM skills", encoding="utf-8")
    (tmp_path / "CLAUDE.md").write_text("1 skills: `/alpha`", encoding="utf-8")
    monkeypatch.setattr("vague.sdk.commands.skill.default_repo_root", lambda: tmp_path)

    result = runner.invoke(sdk_app, ["skill-check"])

    assert result.exit_code == 1
    assert "README.md" in result.output and "alpha" in result.output


def test_skill_check_without_paths_passes_on_this_repo():
    result = runner.invoke(sdk_app, ["skill-check"])
    assert result.exit_code == 0, result.output
    assert "OK" in result.output


def test_bundled_skills_have_no_requires_planning():
    from vague.sdk.commands.skill import _get_assets_skills_dir

    template = _get_assets_skills_dir().parent / "templates" / "SKILL.template.md"
    for skill_md in [*_get_assets_skills_dir().glob("*/SKILL.md"), template]:
        assert "requires_planning" not in skill_md.read_text(encoding="utf-8"), skill_md


def test_skill_list_returns_json(vague_home):
    result = runner.invoke(sdk_app, ["skill-list"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert isinstance(data, list)
