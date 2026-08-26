"""Tests for multi-profile Claude sync: runtime expansion and block assembly."""

import pytest
from typer.testing import CliRunner

from vague.installer import (
    MARKER_END,
    MARKER_START,
    _effective_runtime_dirs,
    _get_instructions_block,
    _resolve_requested_runtimes,
    cmd_claude_init,
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


class TestInstructionsBlockAssembly:
    def test_includes_skill_table_without_claude_d(self, two_profiles):
        block = _get_instructions_block(profile="work")
        assert "## Skill Routing" in block
        assert "/dev-ship" in block

    def test_prepends_shared_base(self, two_profiles):
        _, _, home = two_profiles
        claude_d = home / "claude.d"
        claude_d.mkdir()
        (claude_d / "base.md").write_text("# Shared Rules\n\nAlways use uv.\n")

        block = _get_instructions_block(profile="work")

        assert "# Shared Rules" in block
        assert "Always use uv." in block
        assert block.index("# Shared Rules") < block.index("## Skill Routing")

    def test_appends_matching_profile_overlay(self, two_profiles):
        _, _, home = two_profiles
        claude_d = home / "claude.d"
        claude_d.mkdir()
        (claude_d / "base.md").write_text("# Shared\n")
        (claude_d / "work.md").write_text("# Work Only\n\nInternal service notes.\n")
        (claude_d / "personal.md").write_text("# Personal Only\n\nObsidian vault.\n")

        block = _get_instructions_block(profile="work")

        assert "# Work Only" in block
        assert "Internal service notes." in block

    def test_excludes_other_profiles_overlay(self, two_profiles):
        """The whole point of profiles: work content must not reach personal."""
        _, _, home = two_profiles
        claude_d = home / "claude.d"
        claude_d.mkdir()
        (claude_d / "work.md").write_text("# Work Only\n\nInternal service notes.\n")
        (claude_d / "personal.md").write_text("# Personal Only\n\nObsidian vault.\n")

        personal_block = _get_instructions_block(profile="personal")

        assert "# Personal Only" in personal_block
        assert "Internal service notes." not in personal_block
        assert "# Work Only" not in personal_block

    def test_base_precedes_overlay(self, two_profiles):
        _, _, home = two_profiles
        claude_d = home / "claude.d"
        claude_d.mkdir()
        (claude_d / "base.md").write_text("# Shared\n")
        (claude_d / "work.md").write_text("# Work Only\n")

        block = _get_instructions_block(profile="work")

        assert block.index("# Shared") < block.index("# Work Only")

    def test_no_profile_yields_skill_table_only(self, two_profiles):
        """Runtimes without a Claude profile (copilot) get no personal content."""
        _, _, home = two_profiles
        claude_d = home / "claude.d"
        claude_d.mkdir()
        (claude_d / "base.md").write_text("# Shared\n")

        block = _get_instructions_block(profile=None)

        assert "# Shared" not in block
        assert "## Skill Routing" in block


class TestClaudeInit:
    def test_seeds_base_from_existing_file(self, two_profiles):
        work, personal, home = two_profiles
        (personal / "CLAUDE.md").write_text(
            f"# My Rules\n\nAlways use uv.\n\n{MARKER_START}\nold skills\n{MARKER_END}\n"
        )

        cmd_claude_init(source=personal / "CLAUDE.md")

        base = (home / "claude.d" / "base.md").read_text()
        assert "# My Rules" in base
        assert "Always use uv." in base

    def test_seeded_base_excludes_the_vague_block(self, two_profiles):
        work, personal, home = two_profiles
        (personal / "CLAUDE.md").write_text(f"# My Rules\n\n{MARKER_START}\nold skill table\n{MARKER_END}\n")

        cmd_claude_init(source=personal / "CLAUDE.md")

        base = (home / "claude.d" / "base.md").read_text()
        assert "old skill table" not in base
        assert MARKER_START not in base

    def test_creates_empty_overlay_per_profile(self, two_profiles):
        work, personal, home = two_profiles
        (personal / "CLAUDE.md").write_text("# My Rules\n")

        cmd_claude_init(source=personal / "CLAUDE.md")

        assert (home / "claude.d" / "work.md").exists()
        assert (home / "claude.d" / "personal.md").exists()

    def test_does_not_clobber_existing_base(self, two_profiles):
        work, personal, home = two_profiles
        claude_d = home / "claude.d"
        claude_d.mkdir()
        (claude_d / "base.md").write_text("# Already Here\n")
        (personal / "CLAUDE.md").write_text("# Would Overwrite\n")

        cmd_claude_init(source=personal / "CLAUDE.md")

        assert (claude_d / "base.md").read_text() == "# Already Here\n"

    def test_force_overwrites_existing_base(self, two_profiles):
        work, personal, home = two_profiles
        claude_d = home / "claude.d"
        claude_d.mkdir()
        (claude_d / "base.md").write_text("# Already Here\n")
        (personal / "CLAUDE.md").write_text("# Replaces It\n")

        cmd_claude_init(source=personal / "CLAUDE.md", force=True)

        assert "# Replaces It" in (claude_d / "base.md").read_text()


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

    def test_profiles_receive_their_own_overlay(self, two_profiles):
        work, personal, home = two_profiles
        claude_d = home / "claude.d"
        claude_d.mkdir()
        (claude_d / "work.md").write_text("# Work internal\n")
        (claude_d / "personal.md").write_text("# Obsidian vault\n")
        (work / "CLAUDE.md").write_text("")
        (personal / "CLAUDE.md").write_text("")

        result = runner.invoke(sdk_app, ["install", "--runtime", "claude"], input="y\n")

        assert result.exit_code == 0
        work_content = (work / "CLAUDE.md").read_text()
        personal_content = (personal / "CLAUDE.md").read_text()
        assert "# Work internal" in work_content
        assert "# Work internal" not in personal_content
        assert "# Obsidian vault" in personal_content
        assert "# Obsidian vault" not in work_content
