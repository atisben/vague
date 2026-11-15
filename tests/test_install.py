"""Tests for vague/install.py."""

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from vague.cli import app
from vague.install import (
    MARKER_END,
    MARKER_START,
    RUNTIME_DIRS,
    _build_skill_section,
    _detect_runtimes,
    _effective_runtime_dirs,
    _get_guidelines_file,
    _get_instructions_block,
    _remove_instruction_block,
    _resolve_requested_runtimes,
    _update_instruction_file,
    hook_command,
    install_hooks,
    remove_hooks,
)

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
    monkeypatch.setattr("vague.install.RUNTIME_DIRS", patched)
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
            "vague.install.RUNTIME_DIRS",
            {
                "gone": (str(tmp_path / "nope"), str(tmp_path / "nope" / "skills"), None),
            },
        )
        assert _detect_runtimes() == []

    def test_skips_none_base_dir(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "vague.install.RUNTIME_DIRS",
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
            "vague.install._get_instructions_block",
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

        monkeypatch.setattr("vague.install._get_instructions_block", lambda runtime=None: "new content")

        _update_instruction_file("claude", Path(patched["claude"][1]))

        content = instruction_file.read_text()
        assert "old content" not in content
        assert "new content" in content
        assert "# Config" in content
        assert "# Footer" in content

    def test_skips_when_file_missing(self, fake_runtimes, monkeypatch):
        """Non-fatal when instruction file doesn't exist."""
        monkeypatch.setattr("vague.install._get_instructions_block", lambda runtime=None: "content")
        # Don't create the instruction file — should not raise
        _update_instruction_file("claude", Path("/tmp/fake"))

    def test_skips_when_no_instruction_file_configured(self, fake_runtimes, monkeypatch):
        """Runtimes with instruction_file=None are skipped."""
        monkeypatch.setattr("vague.install._get_instructions_block", lambda runtime=None: "content")
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
            "vague.install._get_instructions_block",
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
            "vague.install._get_instructions_block",
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
        result = runner.invoke(app, ["install", "--runtime", "claude"], input="y\n")
        assert result.exit_code == 0
        skills_dir = Path(patched["claude"][1])
        assert skills_dir.exists()
        assert any(skills_dir.iterdir())

    def test_install_creates_symlinks(self, fake_runtimes, vague_home):
        tmp_path, patched = fake_runtimes
        result = runner.invoke(app, ["install", "--runtime", "claude"], input="y\n")
        assert result.exit_code == 0
        skills_dir = Path(patched["claude"][1])
        linked = list(skills_dir.iterdir())
        assert linked
        for entry in linked:
            assert entry.is_symlink()
            assert entry.resolve().is_dir()

    def test_uninstall_removes_symlinks(self, fake_runtimes, vague_home):
        tmp_path, patched = fake_runtimes
        runner.invoke(app, ["install", "--runtime", "claude"], input="y\n")
        result = runner.invoke(app, ["uninstall", "--runtime", "claude"], input="y\n")
        assert result.exit_code == 0
        skills_dir = Path(patched["claude"][1])
        assert not any(skills_dir.iterdir())

    def test_install_removes_links_to_renamed_skills(self, fake_runtimes, vague_home):
        tmp_path, patched = fake_runtimes
        skills_dir = Path(patched["claude"][1])
        skills_dir.mkdir()
        assets_skills = Path(__file__).parents[1] / "vague" / "assets" / "skills"
        stale = skills_dir / "ops-renamed-away"
        stale.symlink_to(assets_skills / "ops-renamed-away", target_is_directory=True)

        result = runner.invoke(app, ["install", "--runtime", "claude"], input="y\n")

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

        result = runner.invoke(app, ["install", "--runtime", "claude"], input="y\n")

        assert result.exit_code == 0
        assert own_skill.is_dir()
        assert broken_foreign_link.is_symlink()

    def test_install_unknown_runtime(self, fake_runtimes, vague_home):
        result = runner.invoke(app, ["install", "--runtime", "foobar"])
        assert result.exit_code != 0
        assert "unknown runtime" in result.output

    def test_install_no_runtimes_detected(self, tmp_path, monkeypatch, vague_home):
        monkeypatch.setattr(
            "vague.install.RUNTIME_DIRS",
            {
                "gone": (str(tmp_path / "nope"), str(tmp_path / "nope" / "skills"), None),
            },
        )
        result = runner.invoke(app, ["install"])
        assert result.exit_code != 0
        assert "no runtimes detected" in result.output.lower()


class TestCmdUninstall:
    def test_uninstall_from_runtime(self, fake_runtimes, vague_home):
        tmp_path, patched = fake_runtimes
        # First install
        runner.invoke(app, ["install", "--runtime", "claude"], input="y\n")
        # Then uninstall
        result = runner.invoke(app, ["uninstall", "--runtime", "claude"], input="y\n")
        assert result.exit_code == 0
        assert "removed" in result.output.lower()

    def test_uninstall_nothing_installed(self, fake_runtimes, vague_home):
        result = runner.invoke(app, ["uninstall", "--runtime", "claude"])
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
    monkeypatch.setattr("vague.install._get_assets_dir", lambda: assets)
    return assets


class TestClaudeOnlyAssets:
    def test_claude_only_skill_is_not_linked_into_a_non_claude_runtime(self, fake_runtimes, fake_assets, vague_home):
        _, patched = fake_runtimes
        result = runner.invoke(app, ["install", "--runtime", "cursor"], input="y\n")
        assert result.exit_code == 0, result.output
        linked = sorted(p.name for p in Path(patched["cursor"][1]).iterdir())
        assert linked == ["everywhere"]

    def test_claude_only_skill_is_linked_into_every_claude_profile(self, tmp_path, fake_assets, vague_home,
                                                                   monkeypatch):
        work, personal = tmp_path / ".claude-work", tmp_path / ".claude-personal"
        work.mkdir()
        personal.mkdir()
        monkeypatch.setenv("VAGUE_CLAUDE_DIRS", f"{work}:{personal}")
        result = runner.invoke(app, ["install", "--runtime", "claude"], input="y\n")
        assert result.exit_code == 0, result.output
        for profile in (work, personal):
            assert sorted(p.name for p in (profile / "skills").iterdir()) == ["claude-only", "everywhere"]

    def test_install_drops_a_stale_claude_only_link_from_a_non_claude_runtime(self, fake_runtimes, fake_assets,
                                                                              vague_home):
        _, patched = fake_runtimes
        stale = Path(patched["cursor"][1]) / "claude-only"
        stale.parent.mkdir(parents=True)
        stale.symlink_to(fake_assets / "skills" / "claude-only", target_is_directory=True)
        runner.invoke(app, ["install", "--runtime", "cursor"], input="y\n")
        assert not stale.is_symlink()

    def test_agents_are_linked_for_claude_runtimes_only(self, fake_runtimes, fake_assets, vague_home):
        tmp_path, patched = fake_runtimes
        for rt in ("claude", "cursor"):
            result = runner.invoke(app, ["install", "--runtime", rt], input="y\n")
            assert result.exit_code == 0, result.output

        claude_agents = Path(patched["claude"][0]) / "agents"
        assert sorted(p.name for p in claude_agents.iterdir()) == ["demo-reviewer.md"]
        assert (claude_agents / "demo-reviewer.md").resolve() == (fake_assets / "agents" / "demo-reviewer.md").resolve()
        assert not (Path(patched["cursor"][0]) / "agents").exists()

    def test_uninstall_removes_vague_agents_and_keeps_the_users_own(self, fake_runtimes, fake_assets, vague_home):
        _, patched = fake_runtimes
        runner.invoke(app, ["install", "--runtime", "claude"], input="y\n")
        agents_dir = Path(patched["claude"][0]) / "agents"
        (agents_dir / "mine.md").write_text("---\nname: mine\n---\n", encoding="utf-8")

        result = runner.invoke(app, ["uninstall", "--runtime", "claude"], input="y\n")

        assert result.exit_code == 0, result.output
        assert sorted(p.name for p in agents_dir.iterdir()) == ["mine.md"]

    def test_routing_block_lists_claude_only_skills_for_claude_runtimes_only(self, fake_runtimes, fake_assets,
                                                                             vague_home):
        _, patched = fake_runtimes
        for rt in ("claude", "cursor"):
            instruction_file = Path(patched[rt][2])
            instruction_file.parent.mkdir(parents=True, exist_ok=True)
            instruction_file.write_text("# mine\n", encoding="utf-8")
            runner.invoke(app, ["install", "--runtime", rt], input="y\n")

        claude_block = Path(patched["claude"][2]).read_text(encoding="utf-8")
        cursor_block = Path(patched["cursor"][2]).read_text(encoding="utf-8")
        assert "`/claude-only`" in claude_block and "2 skills" in claude_block
        assert "`/claude-only`" not in cursor_block and "1 skills" in cursor_block
        assert "`/everywhere`" in cursor_block


@pytest.fixture
def two_profiles(tmp_path, vague_home, monkeypatch):
    """Two Claude profile dirs declared via VAGUE_CLAUDE_DIRS."""
    work = tmp_path / ".claude-work"
    personal = tmp_path / ".claude-personal"
    work.mkdir()
    personal.mkdir()
    monkeypatch.setenv("VAGUE_CLAUDE_DIRS", f"{work}:{personal}")
    return work, personal, vague_home


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
        assert dirs["cursor"] == (
            "~/.cursor/",
            "~/.cursor/skills/",
            "~/.cursor/rules/vague.mdc",
        )

    def test_falls_back_to_default_when_unconfigured(self, vague_home, monkeypatch):
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
        assert _resolve_requested_runtimes("cursor") == ["cursor"]


GUIDELINES_TEXT = "# Shared Guidelines\n\nAlways explain with a diagram.\n"


@pytest.fixture
def guidelines_file(tmp_path, monkeypatch):
    """A stand-in for vague/assets/claude/guidelines.md with known content."""
    path = tmp_path / "guidelines.md"
    path.write_text(GUIDELINES_TEXT)
    monkeypatch.setattr("vague.install._get_guidelines_file", lambda: path)
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
        monkeypatch.setattr("vague.install._get_guidelines_file", lambda: tmp_path / "absent.md")

        block = _get_instructions_block()

        assert block == _build_skill_section()
        assert block.startswith("# vague")


class TestSyncPreservesUserContent:
    def test_content_outside_the_fence_survives(self, two_profiles):
        """The fence is the contract: everything outside it is the user's."""
        work, personal, home = two_profiles
        target = work / "CLAUDE.md"
        target.write_text(
            f"# Hand written header\n\n{MARKER_START}\nOUTDATED_BLOCK_CONTENT\n{MARKER_END}\n\n# Hand written footer\n"
        )

        result = runner.invoke(app, ["install", "--runtime", "claude:work"], input="y\n")

        assert result.exit_code == 0
        content = target.read_text()
        assert "# Hand written header" in content
        assert "# Hand written footer" in content
        assert "OUTDATED_BLOCK_CONTENT" not in content
        assert "## Skill Routing" in content

    def test_each_profile_gets_its_own_skills_dir(self, two_profiles):
        work, personal, home = two_profiles

        result = runner.invoke(app, ["install", "--runtime", "claude"], input="y\n")

        assert result.exit_code == 0
        for profile_dir in (work, personal):
            skills = profile_dir / "skills"
            assert skills.is_dir()
            linked = list(skills.iterdir())
            assert linked
            assert all(entry.is_symlink() for entry in linked)

    def test_every_runtime_gets_the_full_block(self, two_profiles, guidelines_file, tmp_path, monkeypatch):
        work, personal, _ = two_profiles
        cursor = tmp_path / ".cursor"
        (cursor / "rules").mkdir(parents=True)
        (cursor / "rules" / "vague.mdc").write_text("")
        (work / "CLAUDE.md").write_text("")
        (personal / "CLAUDE.md").write_text("")
        monkeypatch.setitem(
            RUNTIME_DIRS,
            "cursor",
            (str(cursor), str(cursor / "skills"), str(cursor / "rules" / "vague.mdc")),
        )

        for runtime in ("claude", "cursor"):
            result = runner.invoke(app, ["install", "--runtime", runtime], input="y\n")
            assert result.exit_code == 0

        contents = [
            (work / "CLAUDE.md").read_text(),
            (personal / "CLAUDE.md").read_text(),
            (cursor / "rules" / "vague.mdc").read_text(),
        ]
        for content in contents:
            assert "Always explain with a diagram." in content
            assert "## Skill Routing" in content
        # Claude profiles share one block. Cursor's lists only the skills it gets: no Claude-only ones.
        assert contents[0] == contents[1]
        assert "`/impeccable`" in contents[0]
        assert "`/impeccable`" not in contents[2]

    def test_text_outside_the_markers_is_byte_identical(self, two_profiles, guidelines_file):
        work, _, _ = two_profiles
        header = "# Private header\n\nKeep  this   spacing\t exactly.\n\n"
        footer = "\n\n## Private footer\n- [ ] trailing item  \n"
        target = work / "CLAUDE.md"
        target.write_text(f"{header}{MARKER_START}\nOUTDATED\n{MARKER_END}{footer}")

        result = runner.invoke(app, ["install", "--runtime", "claude:work"], input="y\n")

        assert result.exit_code == 0
        content = target.read_text()
        assert content.startswith(header + MARKER_START)
        assert content.endswith(MARKER_END + footer)
        assert "OUTDATED" not in content


def _read(path):
    return json.loads(path.read_text())


def _commands(settings, event):
    return [h["command"] for group in settings["hooks"][event] for h in group["hooks"]]


def test_install_creates_settings_with_both_hooks(tmp_path):
    path = tmp_path / "settings.json"

    assert install_hooks(settings_path=path, command="vague log-event") is True

    settings = _read(path)
    assert _commands(settings, "UserPromptSubmit") == ["vague log-event"]
    assert _commands(settings, "PostToolUse") == ["vague log-event"]
    assert settings["hooks"]["PostToolUse"][0]["matcher"] == "Skill|Write|Edit"


def test_install_keeps_existing_settings_and_hooks(tmp_path):
    path = tmp_path / "settings.json"
    other = {"type": "command", "command": "echo hi"}
    path.write_text(json.dumps({"theme": "dark", "hooks": {"PostToolUse": [{"matcher": "Bash", "hooks": [other]}]}}))

    install_hooks(settings_path=path, command="vague log-event")

    settings = _read(path)
    assert settings["theme"] == "dark"
    assert _commands(settings, "PostToolUse") == ["echo hi", "vague log-event"]


def test_install_twice_does_not_duplicate(tmp_path):
    path = tmp_path / "settings.json"
    install_hooks(settings_path=path, command="vague log-event")

    assert install_hooks(settings_path=path, command="vague log-event") is False

    assert _commands(_read(path), "UserPromptSubmit") == ["vague log-event"]


def test_install_recognises_a_hand_added_hook_with_another_path(tmp_path):
    path = tmp_path / "settings.json"
    entry = {"type": "command", "command": "~/.local/bin/vague log-event"}
    manual = {"hooks": {"UserPromptSubmit": [{"hooks": [entry]}]}}
    path.write_text(json.dumps(manual))

    install_hooks(settings_path=path, command="/opt/bin/vague log-event")

    assert _commands(_read(path), "UserPromptSubmit") == ["~/.local/bin/vague log-event"]


def test_install_leaves_a_corrupt_settings_file_untouched(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text("{not json")

    assert install_hooks(settings_path=path, command="vague log-event") is False

    assert path.read_text() == "{not json"


def test_remove_deletes_only_vague_hooks(tmp_path):
    path = tmp_path / "settings.json"
    other = {"type": "command", "command": "echo hi"}
    path.write_text(json.dumps({"hooks": {"PostToolUse": [{"matcher": "Bash", "hooks": [other]}]}}))
    install_hooks(settings_path=path, command="vague log-event")

    remove_hooks(settings_path=path)

    settings = _read(path)
    assert _commands(settings, "PostToolUse") == ["echo hi"]
    assert "UserPromptSubmit" not in settings["hooks"]


def test_remove_drops_the_empty_hooks_key(tmp_path):
    path = tmp_path / "settings.json"
    install_hooks(settings_path=path, command="vague log-event")

    remove_hooks(settings_path=path)

    assert "hooks" not in _read(path)


def test_hook_command_uses_the_absolute_path_when_vague_is_on_path(monkeypatch):
    monkeypatch.setattr("vague.install.shutil.which", lambda name: "/opt/bin/vague")

    assert hook_command() == "/opt/bin/vague log-event"


def test_hook_command_quotes_a_path_with_spaces(monkeypatch):
    monkeypatch.setattr("vague.install.shutil.which", lambda name: "/my bin/vague")

    assert hook_command() == "'/my bin/vague' log-event"


def test_hook_command_falls_back_to_the_bare_name(monkeypatch):
    monkeypatch.setattr("vague.install.shutil.which", lambda name: None)

    assert hook_command() == "vague log-event"


@pytest.fixture
def runtimes(tmp_path, monkeypatch):
    claude, cursor = tmp_path / ".claude", tmp_path / ".cursor"
    claude.mkdir()
    cursor.mkdir()
    monkeypatch.setattr("vague.install.RUNTIME_DIRS", {
        "claude": (str(claude), str(claude / "skills"), str(claude / "CLAUDE.md")),
        "cursor": (str(cursor), str(cursor / "skills"), str(cursor / "rules" / "vague.mdc")),
    })
    return claude, cursor


def test_install_command_wires_hooks_for_claude_only(runtimes):
    claude, cursor = runtimes

    result = runner.invoke(app, ["install"], input="y\n")

    assert result.exit_code == 0, result.output
    assert "log-event" in (claude / "settings.json").read_text()
    assert not (cursor / "settings.json").exists()


def test_uninstall_command_removes_the_hooks(runtimes):
    claude, _ = runtimes
    runner.invoke(app, ["install"], input="y\n")

    result = runner.invoke(app, ["uninstall"], input="y\n")

    assert result.exit_code == 0, result.output
    assert "log-event" not in (claude / "settings.json").read_text()


def test_install_widens_matcher_of_existing_vague_hook(tmp_path):
    path = tmp_path / "settings.json"
    other = {"type": "command", "command": "echo hi"}
    old = {"type": "command", "command": "vague log-event"}
    path.write_text(json.dumps({"hooks": {"PostToolUse": [
        {"matcher": "Bash", "hooks": [other]}, {"matcher": "Skill", "hooks": [old]},
    ]}}))

    assert install_hooks(settings_path=path, command="vague log-event") is True

    groups = _read(path)["hooks"]["PostToolUse"]
    assert groups == [
        {"matcher": "Bash", "hooks": [other]},
        {"matcher": "Skill|Write|Edit", "hooks": [{"type": "command", "command": "vague log-event"}]},
    ]


def test_install_twice_leaves_settings_unchanged(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text(json.dumps({"hooks": {"PostToolUse": [{"matcher": "Skill", "hooks": [
        {"type": "command", "command": "vague log-event"}]}]}}))
    install_hooks(settings_path=path, command="vague log-event")
    first = path.read_text()

    assert install_hooks(settings_path=path, command="vague log-event") is False

    assert path.read_text() == first
