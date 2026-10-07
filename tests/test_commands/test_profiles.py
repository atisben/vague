"""Tests for multi-profile Claude sync: runtime expansion and the public managed block."""

import pytest
from typer.testing import CliRunner

from vague.installer import (
    MARKER_END,
    MARKER_START,
    RUNTIME_DIRS,
    _build_skill_section,
    _effective_runtime_dirs,
    _get_assets_dir,
    _get_guidelines_file,
    _get_instructions_block,
    _resolve_requested_runtimes,
)
from vague.sdk.cli import sdk_app

runner = CliRunner()


@pytest.fixture
def two_profiles(tmp_path, vague_home_dir, monkeypatch):
    """Two Claude profile dirs declared via VAGUE_CLAUDE_DIRS."""
    work = tmp_path / ".claude-work"
    personal = tmp_path / ".claude-personal"
    work.mkdir()
    personal.mkdir()
    monkeypatch.setenv("VAGUE_HOME", str(vague_home_dir))
    monkeypatch.setenv("VAGUE_CLAUDE_DIRS", f"{work}:{personal}")
    return work, personal, vague_home_dir


class TestEffectiveRuntimeDirs:
    def test_expands_claude_into_one_entry_per_profile(self, two_profiles):
        work, personal, _ = two_profiles
        dirs = _effective_runtime_dirs()

        assert "claude:work" in dirs
        assert "claude:personal" in dirs
        assert dirs["claude:work"] == (str(work), str(work / "skills"), str(work / "CLAUDE.md"))
        assert dirs["claude:personal"] == (
            str(personal),
            str(personal / "skills"),
            str(personal / "CLAUDE.md"),
        )

    def test_plain_claude_key_is_replaced(self, two_profiles):
        assert "claude" not in _effective_runtime_dirs()

    def test_other_runtimes_are_untouched(self, two_profiles):
        dirs = _effective_runtime_dirs()
        assert dirs["copilot"] == (
            "~/.copilot/",
            "~/.copilot/skills/",
            "~/.copilot/instructions.md",
        )

    def test_falls_back_to_default_when_unconfigured(self, vague_home_dir, monkeypatch):
        monkeypatch.setenv("VAGUE_HOME", str(vague_home_dir))
        dirs = _effective_runtime_dirs()
        assert dirs["claude"] == ("~/.claude/", "~/.claude/skills/", "~/.claude/CLAUDE.md")
        assert not any(key.startswith("claude:") for key in dirs)


class TestResolveRequestedRuntimes:
    def test_claude_selects_every_profile(self, two_profiles):
        assert sorted(_resolve_requested_runtimes("claude")) == ["claude:personal", "claude:work"]

    def test_exact_profile_selects_one(self, two_profiles):
        assert _resolve_requested_runtimes("claude:work") == ["claude:work"]

    def test_unknown_runtime_returns_empty(self, two_profiles):
        assert _resolve_requested_runtimes("foobar") == []

    def test_non_claude_runtime_still_resolves(self, two_profiles):
        assert _resolve_requested_runtimes("copilot") == ["copilot"]


GUIDELINES_TEXT = "# Shared Guidelines\n\nAlways explain with a diagram.\n"


@pytest.fixture
def guidelines_file(tmp_path, monkeypatch):
    """A stand-in for vague/assets/claude/guidelines.md with known content."""
    path = tmp_path / "guidelines.md"
    path.write_text(GUIDELINES_TEXT)
    monkeypatch.setattr("vague.installer._get_guidelines_file", lambda: path)
    return path


class TestInstructionsBlockAssembly:
    def test_block_starts_with_guidelines_then_skill_table(self, guidelines_file):
        block = _get_instructions_block()

        assert block.startswith(GUIDELINES_TEXT.strip() + "\n\n# vague\n")
        assert block.index("Always explain with a diagram.") < block.index("## Skill Routing")
        assert "/dev-ship" in block
        assert block.endswith("\n")

    def test_bundled_guidelines_file_is_included_verbatim_when_present(self):
        bundled = _get_guidelines_file()
        if not bundled.is_file():
            pytest.skip("bundled guidelines.md not present yet")

        block = _get_instructions_block()

        assert bundled.read_text().strip() in block
        assert block.index(bundled.read_text().strip()) < block.index("# vague")

    def test_missing_guidelines_yields_skill_section_alone(self, tmp_path, monkeypatch):
        monkeypatch.setattr("vague.installer._get_guidelines_file", lambda: tmp_path / "absent.md")

        block = _get_instructions_block()

        assert block == _build_skill_section()
        assert block.startswith("# vague")

    def test_skill_section_does_not_need_instructions_template(self):
        assert not (_get_assets_dir() / "templates" / "instructions-block.md").exists()
        assert "## Skill Routing" in _build_skill_section()

    def test_leftover_claude_d_base_is_never_included(self, two_profiles, guidelines_file):
        _, _, home = two_profiles
        claude_d = home / "claude.d"
        claude_d.mkdir()
        (claude_d / "base.md").write_text("# PRIVATE_BASE_CONTENT\n")
        (claude_d / "work.md").write_text("# PRIVATE_WORK_CONTENT\n")

        block = _get_instructions_block()

        assert "PRIVATE_BASE_CONTENT" not in block
        assert "PRIVATE_WORK_CONTENT" not in block


class TestClaudeInitRemoved:
    def test_claude_init_command_no_longer_exists(self):
        result = runner.invoke(sdk_app, ["claude-init"])
        assert result.exit_code != 0
        assert "No such command" in result.output


class TestSyncPreservesUserContent:
    def test_content_outside_the_fence_survives(self, two_profiles):
        """The fence is the contract: everything outside it is the user's."""
        work, personal, home = two_profiles
        target = work / "CLAUDE.md"
        target.write_text(
            f"# Hand written header\n\n{MARKER_START}\nOUTDATED_BLOCK_CONTENT\n{MARKER_END}\n\n# Hand written footer\n"
        )

        result = runner.invoke(sdk_app, ["install", "--runtime", "claude:work"], input="y\n")

        assert result.exit_code == 0
        content = target.read_text()
        assert "# Hand written header" in content
        assert "# Hand written footer" in content
        assert "OUTDATED_BLOCK_CONTENT" not in content
        assert "## Skill Routing" in content

    def test_each_profile_gets_its_own_skills_dir(self, two_profiles):
        work, personal, home = two_profiles

        result = runner.invoke(sdk_app, ["install", "--runtime", "claude"], input="y\n")

        assert result.exit_code == 0
        for profile_dir in (work, personal):
            skills = profile_dir / "skills"
            assert skills.is_dir()
            linked = list(skills.iterdir())
            assert linked
            assert all(entry.is_symlink() for entry in linked)

    def test_every_runtime_gets_the_same_full_block(self, two_profiles, guidelines_file, tmp_path, monkeypatch):
        work, personal, _ = two_profiles
        copilot = tmp_path / ".copilot"
        copilot.mkdir()
        (copilot / "instructions.md").write_text("")
        (work / "CLAUDE.md").write_text("")
        (personal / "CLAUDE.md").write_text("")
        monkeypatch.setitem(
            RUNTIME_DIRS,
            "copilot",
            (str(copilot), str(copilot / "skills"), str(copilot / "instructions.md")),
        )

        for runtime in ("claude", "copilot"):
            result = runner.invoke(sdk_app, ["install", "--runtime", runtime], input="y\n")
            assert result.exit_code == 0

        contents = [
            (work / "CLAUDE.md").read_text(),
            (personal / "CLAUDE.md").read_text(),
            (copilot / "instructions.md").read_text(),
        ]
        for content in contents:
            assert "Always explain with a diagram." in content
            assert "## Skill Routing" in content
        assert contents[0] == contents[1] == contents[2]

    def test_text_outside_the_markers_is_byte_identical(self, two_profiles, guidelines_file):
        work, _, _ = two_profiles
        header = "# Private header\n\nKeep  this   spacing\t exactly.\n\n"
        footer = "\n\n## Private footer\n- [ ] trailing item  \n"
        target = work / "CLAUDE.md"
        target.write_text(f"{header}{MARKER_START}\nOUTDATED\n{MARKER_END}{footer}")

        result = runner.invoke(sdk_app, ["install", "--runtime", "claude:work"], input="y\n")

        assert result.exit_code == 0
        content = target.read_text()
        assert content.startswith(header + MARKER_START)
        assert content.endswith(MARKER_END + footer)
        assert "OUTDATED" not in content

    def test_leftover_claude_d_is_not_rendered_and_triggers_warning(self, two_profiles, guidelines_file):
        work, _, home = two_profiles
        claude_d = home / "claude.d"
        claude_d.mkdir()
        (claude_d / "base.md").write_text("# PRIVATE_BASE_CONTENT\n")
        (work / "CLAUDE.md").write_text("")

        result = runner.invoke(sdk_app, ["install", "--runtime", "claude:work"], input="y\n")

        assert result.exit_code == 0
        assert "PRIVATE_BASE_CONTENT" not in (work / "CLAUDE.md").read_text()
        assert f"{claude_d} is no longer read" in result.output
        assert (claude_d / "base.md").read_text() == "# PRIVATE_BASE_CONTENT\n"

    def test_no_legacy_warning_without_claude_d(self, two_profiles, guidelines_file):
        result = runner.invoke(sdk_app, ["install", "--runtime", "claude:work"], input="y\n")

        assert result.exit_code == 0
        assert "no longer read" not in result.output
