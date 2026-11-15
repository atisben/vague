"""Tests for multi-runtime installer."""

from pathlib import Path

import pytest
from typer.testing import CliRunner

from vague.installer import (
    MARKER_END,
    MARKER_START,
    _detect_runtimes,
    _remove_instruction_block,
    _update_instruction_file,
)
from vague.sdk.cli import sdk_app

runner = CliRunner()


@pytest.fixture
def fake_runtimes(tmp_path, monkeypatch):
    """Set up fake runtime directories and patch RUNTIME_DIRS to use them."""
    claude_dir = tmp_path / ".claude"
    cursor_dir = tmp_path / ".cursor"
    claude_dir.mkdir()
    cursor_dir.mkdir()

    patched = {
        "claude": (str(claude_dir), str(claude_dir / "skills"), str(claude_dir / "CLAUDE.md")),
        "cursor": (str(cursor_dir), str(cursor_dir / "skills"), str(cursor_dir / "rules" / "vague.mdc")),
        "missing": (str(tmp_path / ".missing"), str(tmp_path / ".missing" / "skills"), None),
    }
    monkeypatch.setattr("vague.installer.RUNTIME_DIRS", patched)
    return tmp_path, patched


class TestDetectRuntimes:
    def test_detects_multiple(self, fake_runtimes):
        runtimes = _detect_runtimes()
        assert "claude" in runtimes
        assert "cursor" in runtimes

    def test_skips_missing(self, fake_runtimes):
        runtimes = _detect_runtimes()
        assert "missing" not in runtimes

    def test_returns_empty_when_none(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "vague.installer.RUNTIME_DIRS",
            {
                "gone": (str(tmp_path / "nope"), str(tmp_path / "nope" / "skills"), None),
            },
        )
        assert _detect_runtimes() == []

    def test_skips_none_base_dir(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "vague.installer.RUNTIME_DIRS",
            {
                "generic": (None, str(tmp_path / "skills"), None),
            },
        )
        assert _detect_runtimes() == []


class TestUpdateInstructionFile:
    def test_appends_when_no_markers(self, fake_runtimes, monkeypatch):
        tmp_path, patched = fake_runtimes
        instruction_file = Path(patched["claude"][2])
        instruction_file.write_text("# My Config\n\nSome content.\n")

        # Provide a simple template
        monkeypatch.setattr(
            "vague.installer._get_instructions_block",
            lambda runtime=None: "## Vague Skills\nRouting table here.",
        )

        _update_instruction_file("claude", Path(patched["claude"][1]))

        content = instruction_file.read_text()
        assert MARKER_START in content
        assert MARKER_END in content
        assert "## Vague Skills" in content
        assert "# My Config" in content

    def test_replaces_existing_markers(self, fake_runtimes, monkeypatch):
        tmp_path, patched = fake_runtimes
        instruction_file = Path(patched["claude"][2])
        instruction_file.write_text(f"# Config\n\n{MARKER_START}\nold content\n{MARKER_END}\n\n# Footer\n")

        monkeypatch.setattr("vague.installer._get_instructions_block", lambda runtime=None: "new content")

        _update_instruction_file("claude", Path(patched["claude"][1]))

        content = instruction_file.read_text()
        assert "old content" not in content
        assert "new content" in content
        assert "# Config" in content
        assert "# Footer" in content

    def test_skips_when_file_missing(self, fake_runtimes, monkeypatch):
        """Non-fatal when instruction file doesn't exist."""
        monkeypatch.setattr("vague.installer._get_instructions_block", lambda runtime=None: "content")
        # Don't create the instruction file — should not raise
        _update_instruction_file("claude", Path("/tmp/fake"))

    def test_skips_when_no_instruction_file_configured(self, fake_runtimes, monkeypatch):
        """Runtimes with instruction_file=None are skipped."""
        monkeypatch.setattr("vague.installer._get_instructions_block", lambda runtime=None: "content")
        _update_instruction_file("missing", Path("/tmp/fake"))


class TestMarkersMustOwnTheirLine:
    """A marker quoted inside prose is documentation, not a block boundary.

    Treating a mid-sentence mention as the start of the managed region
    silently destroys everything the user wrote after it.
    """

    def test_prose_mention_before_the_block_is_not_the_boundary(self, fake_runtimes, monkeypatch):
        tmp_path, patched = fake_runtimes
        instruction_file = Path(patched["claude"][2])
        instruction_file.write_text(
            f"# Notes\n\nEverything after the `{MARKER_START}` line is generated.\n\n"
            f"## Keep Me\n\nHand-written content.\n\n"
            f"{MARKER_START}\nOLD_GENERATED\n{MARKER_END}\n"
        )

        monkeypatch.setattr(
            "vague.installer._get_instructions_block",
            lambda runtime=None: "NEW_GENERATED",
        )

        _update_instruction_file("claude", Path(patched["claude"][1]))

        content = instruction_file.read_text()
        assert "## Keep Me" in content
        assert "Hand-written content." in content
        assert "Everything after the" in content
        assert "NEW_GENERATED" in content
        assert "OLD_GENERATED" not in content

    def test_prose_mention_of_end_marker_is_ignored(self, fake_runtimes, monkeypatch):
        tmp_path, patched = fake_runtimes
        instruction_file = Path(patched["claude"][2])
        instruction_file.write_text(
            f"# Notes\n\nThe block ends at `{MARKER_END}` — do not edit it.\n\n"
            f"{MARKER_START}\nOLD_GENERATED\n{MARKER_END}\n\n# Footer\n"
        )

        monkeypatch.setattr(
            "vague.installer._get_instructions_block",
            lambda runtime=None: "NEW_GENERATED",
        )

        _update_instruction_file("claude", Path(patched["claude"][1]))

        content = instruction_file.read_text()
        assert "The block ends at" in content
        assert "# Footer" in content
        assert "NEW_GENERATED" in content
        assert "OLD_GENERATED" not in content

    def test_removal_ignores_prose_mentions(self, fake_runtimes):
        tmp_path, patched = fake_runtimes
        instruction_file = Path(patched["claude"][2])
        instruction_file.write_text(
            f"# Notes\n\nSee `{MARKER_START}` for details.\n\n"
            f"{MARKER_START}\ngenerated\n{MARKER_END}\n\n# Footer\n"
        )

        _remove_instruction_block("claude")

        content = instruction_file.read_text()
        assert "generated" not in content
        assert "See `" in content
        assert "# Footer" in content


class TestRemoveInstructionBlock:
    def test_removes_vague_block(self, fake_runtimes, monkeypatch):
        tmp_path, patched = fake_runtimes
        instruction_file = Path(patched["claude"][2])
        instruction_file.write_text(f"# Config\n\n{MARKER_START}\nvague stuff\n{MARKER_END}\n\n# Footer\n")

        _remove_instruction_block("claude")

        content = instruction_file.read_text()
        assert MARKER_START not in content
        assert "vague stuff" not in content
        assert "# Config" in content
        assert "# Footer" in content

class TestCmdInstall:
    def test_install_to_specific_runtime(self, fake_runtimes, vague_home):
        tmp_path, patched = fake_runtimes
        result = runner.invoke(sdk_app, ["install", "--runtime", "claude"], input="y\n")
        assert result.exit_code == 0
        skills_dir = Path(patched["claude"][1])
        assert skills_dir.exists()
        assert any(skills_dir.iterdir())

    def test_install_creates_symlinks(self, fake_runtimes, vague_home):
        tmp_path, patched = fake_runtimes
        result = runner.invoke(sdk_app, ["install", "--runtime", "claude"], input="y\n")
        assert result.exit_code == 0
        skills_dir = Path(patched["claude"][1])
        linked = list(skills_dir.iterdir())
        assert linked
        for entry in linked:
            assert entry.is_symlink()
            assert entry.resolve().is_dir()

    def test_uninstall_removes_symlinks(self, fake_runtimes, vague_home):
        tmp_path, patched = fake_runtimes
        runner.invoke(sdk_app, ["install", "--runtime", "claude"], input="y\n")
        result = runner.invoke(sdk_app, ["uninstall", "--runtime", "claude"], input="y\n")
        assert result.exit_code == 0
        skills_dir = Path(patched["claude"][1])
        assert not any(skills_dir.iterdir())

    def test_install_removes_links_to_renamed_skills(self, fake_runtimes, vague_home):
        tmp_path, patched = fake_runtimes
        skills_dir = Path(patched["claude"][1])
        skills_dir.mkdir()
        assets_skills = Path(__file__).parents[2] / "vague" / "assets" / "skills"
        stale = skills_dir / "ops-renamed-away"
        stale.symlink_to(assets_skills / "ops-renamed-away", target_is_directory=True)

        result = runner.invoke(sdk_app, ["install", "--runtime", "claude"], input="y\n")

        assert result.exit_code == 0
        assert not stale.is_symlink()

    def test_install_keeps_skills_not_owned_by_vague(self, fake_runtimes, vague_home):
        tmp_path, patched = fake_runtimes
        skills_dir = Path(patched["claude"][1])
        skills_dir.mkdir()
        own_skill = skills_dir / "my-skill"
        own_skill.mkdir()
        broken_foreign_link = skills_dir / "foreign"
        broken_foreign_link.symlink_to(tmp_path / "elsewhere", target_is_directory=True)

        result = runner.invoke(sdk_app, ["install", "--runtime", "claude"], input="y\n")

        assert result.exit_code == 0
        assert own_skill.is_dir()
        assert broken_foreign_link.is_symlink()

    def test_install_unknown_runtime(self, fake_runtimes, vague_home):
        result = runner.invoke(sdk_app, ["install", "--runtime", "foobar"])
        assert result.exit_code != 0
        assert "unknown runtime" in result.output

    def test_install_no_runtimes_detected(self, tmp_path, monkeypatch, vague_home):
        monkeypatch.setattr(
            "vague.installer.RUNTIME_DIRS",
            {
                "gone": (str(tmp_path / "nope"), str(tmp_path / "nope" / "skills"), None),
            },
        )
        result = runner.invoke(sdk_app, ["install"])
        assert result.exit_code != 0
        assert "no runtimes detected" in result.output.lower()


class TestCmdUninstall:
    def test_uninstall_from_runtime(self, fake_runtimes, vague_home):
        tmp_path, patched = fake_runtimes
        # First install
        runner.invoke(sdk_app, ["install", "--runtime", "claude"], input="y\n")
        # Then uninstall
        result = runner.invoke(sdk_app, ["uninstall", "--runtime", "claude"], input="y\n")
        assert result.exit_code == 0
        assert "removed" in result.output.lower()

    def test_uninstall_nothing_installed(self, fake_runtimes, vague_home):
        result = runner.invoke(sdk_app, ["uninstall", "--runtime", "claude"])
        assert result.exit_code == 0
        assert "no vague skills" in result.output.lower()


@pytest.fixture
def fake_assets(tmp_path, monkeypatch):
    """A bundled-assets tree with one skill for every runtime, one Claude-only skill and one agent."""
    assets = tmp_path / "assets"
    for name, runtimes in (("everywhere", ""), ("claude-only", "runtimes:\n  - claude\n")):
        skill_md = assets / "skills" / name / "SKILL.md"
        skill_md.parent.mkdir(parents=True)
        skill_md.write_text(
            f"---\nname: {name}\ndescription: |\n  Demo. Trigger: \"{name} please\".\n{runtimes}---\nbody\n",
            encoding="utf-8",
        )
    agents = assets / "agents"
    (agents / ".gitkeep").parent.mkdir(parents=True)
    (agents / ".gitkeep").write_text("", encoding="utf-8")
    (agents / "demo-reviewer.md").write_text("---\nname: demo-reviewer\n---\n", encoding="utf-8")
    monkeypatch.setattr("vague.installer._get_assets_dir", lambda: assets)
    return assets


class TestClaudeOnlyAssets:
    def test_claude_only_skill_is_not_linked_into_a_non_claude_runtime(self, fake_runtimes, fake_assets, vague_home):
        _, patched = fake_runtimes
        result = runner.invoke(sdk_app, ["install", "--runtime", "cursor"], input="y\n")
        assert result.exit_code == 0, result.output
        linked = sorted(p.name for p in Path(patched["cursor"][1]).iterdir())
        assert linked == ["everywhere"]

    def test_claude_only_skill_is_linked_into_every_claude_profile(self, tmp_path, fake_assets, vague_home,
                                                                   monkeypatch):
        work, personal = tmp_path / ".claude-work", tmp_path / ".claude-personal"
        work.mkdir()
        personal.mkdir()
        monkeypatch.setenv("VAGUE_CLAUDE_DIRS", f"{work}:{personal}")
        result = runner.invoke(sdk_app, ["install", "--runtime", "claude"], input="y\n")
        assert result.exit_code == 0, result.output
        for profile in (work, personal):
            assert sorted(p.name for p in (profile / "skills").iterdir()) == ["claude-only", "everywhere"]

    def test_install_drops_a_stale_claude_only_link_from_a_non_claude_runtime(self, fake_runtimes, fake_assets,
                                                                              vague_home):
        _, patched = fake_runtimes
        stale = Path(patched["cursor"][1]) / "claude-only"
        stale.parent.mkdir(parents=True)
        stale.symlink_to(fake_assets / "skills" / "claude-only", target_is_directory=True)
        runner.invoke(sdk_app, ["install", "--runtime", "cursor"], input="y\n")
        assert not stale.is_symlink()

    def test_agents_are_linked_for_claude_runtimes_only(self, fake_runtimes, fake_assets, vague_home):
        tmp_path, patched = fake_runtimes
        for rt in ("claude", "cursor"):
            result = runner.invoke(sdk_app, ["install", "--runtime", rt], input="y\n")
            assert result.exit_code == 0, result.output

        claude_agents = Path(patched["claude"][0]) / "agents"
        assert sorted(p.name for p in claude_agents.iterdir()) == ["demo-reviewer.md"]
        assert (claude_agents / "demo-reviewer.md").resolve() == (fake_assets / "agents" / "demo-reviewer.md").resolve()
        assert not (Path(patched["cursor"][0]) / "agents").exists()

    def test_uninstall_removes_vague_agents_and_keeps_the_users_own(self, fake_runtimes, fake_assets, vague_home):
        _, patched = fake_runtimes
        runner.invoke(sdk_app, ["install", "--runtime", "claude"], input="y\n")
        agents_dir = Path(patched["claude"][0]) / "agents"
        (agents_dir / "mine.md").write_text("---\nname: mine\n---\n", encoding="utf-8")

        result = runner.invoke(sdk_app, ["uninstall", "--runtime", "claude"], input="y\n")

        assert result.exit_code == 0, result.output
        assert sorted(p.name for p in agents_dir.iterdir()) == ["mine.md"]

    def test_routing_block_lists_claude_only_skills_for_claude_runtimes_only(self, fake_runtimes, fake_assets,
                                                                             vague_home):
        _, patched = fake_runtimes
        for rt in ("claude", "cursor"):
            instruction_file = Path(patched[rt][2])
            instruction_file.parent.mkdir(parents=True, exist_ok=True)
            instruction_file.write_text("# mine\n", encoding="utf-8")
            runner.invoke(sdk_app, ["install", "--runtime", rt], input="y\n")

        claude_block = Path(patched["claude"][2]).read_text(encoding="utf-8")
        cursor_block = Path(patched["cursor"][2]).read_text(encoding="utf-8")
        assert "`/claude-only`" in claude_block and "2 skills" in claude_block
        assert "`/claude-only`" not in cursor_block and "1 skills" in cursor_block
        assert "`/everywhere`" in cursor_block
