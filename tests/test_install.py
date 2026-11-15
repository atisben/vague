"""Tests for vague/install.py."""

import json
import os
from pathlib import Path

import pytest
import typer
from typer.testing import CliRunner

from vague.cli import app
from vague.install import (
    MARKER_END,
    MARKER_START,
    Runtime,
    _build_skill_section,
    _get_guidelines_file,
    _get_instructions_block,
    _install_to_runtime,
    hook_command,
    install_hooks,
    remove_hooks,
    replace_block,
    resolve_runtimes,
    runtimes,
    write_instruction_block,
)
from vague.skill_rules import skill_trigger

runner = CliRunner()
BLOCK = f"{MARKER_START}\nOLD\n{MARKER_END}"


@pytest.fixture
def profile(tmp_path, monkeypatch):
    """One Claude profile, ~/.claude-test, declared in VAGUE_CLAUDE_DIRS: runtime key `claude:test`."""
    directory = tmp_path / ".claude-test"
    directory.mkdir()
    monkeypatch.setenv("VAGUE_CLAUDE_DIRS", str(directory))
    return directory


@pytest.fixture
def two_profiles(tmp_path, monkeypatch):
    """Two Claude profile dirs declared via VAGUE_CLAUDE_DIRS."""
    work = tmp_path / ".claude-work"
    personal = tmp_path / ".claude-personal"
    work.mkdir()
    personal.mkdir()
    monkeypatch.setenv("VAGUE_CLAUDE_DIRS", f"{work}:{personal}")
    return work, personal


@pytest.fixture
def fake_assets(tmp_path, monkeypatch):
    """A bundled-assets tree with two skills and one agent."""
    assets = tmp_path / "assets"
    for name in ("alpha", "beta"):
        skill_md = assets / "skills" / name / "SKILL.md"
        skill_md.parent.mkdir(parents=True)
        skill_md.write_text(
            f"---\nname: {name}\ndescription: |\n  Demo. Trigger: \"{name} please\".\n---\nbody\n", encoding="utf-8"
        )
    agents = assets / "agents"
    agents.mkdir()
    (agents / ".gitkeep").write_text("", encoding="utf-8")
    (agents / "demo-reviewer.md").write_text("---\nname: demo-reviewer\n---\n", encoding="utf-8")
    monkeypatch.setattr("vague.install._get_assets_dir", lambda: assets)
    return assets


class TestRuntimes:
    def test_one_runtime_per_claude_profile(self, two_profiles):
        work, personal = two_profiles
        assert runtimes() == [
            Runtime(key="claude:work", root=work, skills_dir=work / "skills", instruction_file=work / "CLAUDE.md",
                    agents_dir=work / "agents", settings_file=work / "settings.json"),
            Runtime(key="claude:personal", root=personal, skills_dir=personal / "skills",
                    instruction_file=personal / "CLAUDE.md", agents_dir=personal / "agents",
                    settings_file=personal / "settings.json"),
        ]

    def test_unconfigured_falls_back_to_home_dot_claude(self):
        (runtime,) = runtimes()
        assert (runtime.key, runtime.root) == ("claude", Path("~/.claude").expanduser())


class TestResolveRuntimes:
    def test_claude_selects_every_profile(self, two_profiles):
        assert sorted(r.key for r in resolve_runtimes(requested="claude")) == ["claude:personal", "claude:work"]

    def test_exact_profile_selects_one(self, two_profiles):
        assert [r.key for r in resolve_runtimes(requested="claude:work")] == ["claude:work"]

    def test_unknown_runtime_exits_with_the_choices(self, two_profiles, capsys):
        with pytest.raises(typer.Exit):
            resolve_runtimes(requested="cursor")
        assert "claude:work" in capsys.readouterr().err

    def test_no_request_detects_only_existing_profiles(self, tmp_path, monkeypatch):
        present = tmp_path / ".claude-here"
        present.mkdir()
        monkeypatch.setenv("VAGUE_CLAUDE_DIRS", f"{present}:{tmp_path / '.claude-gone'}")
        assert [r.key for r in resolve_runtimes(requested=None)] == ["claude:here"]

    def test_no_request_and_no_profile_on_disk_exits(self, tmp_path, monkeypatch):
        monkeypatch.setenv("VAGUE_CLAUDE_DIRS", str(tmp_path / ".claude-gone"))
        with pytest.raises(typer.Exit):
            resolve_runtimes(requested=None)


class TestReplaceBlock:
    def test_replaces_the_block_and_keeps_the_rest(self):
        text = f"# Config\n\n{BLOCK}\n\n# Footer\n"
        assert replace_block(text=text, block="NEW") == f"# Config\n\n{MARKER_START}\nNEW\n{MARKER_END}\n\n# Footer\n"

    def test_appends_after_a_blank_line_when_there_is_no_block(self):
        assert replace_block(text="# Mine\n", block="NEW") == f"# Mine\n\n{MARKER_START}\nNEW\n{MARKER_END}\n"

    def test_empty_block_removes_the_block_and_its_blank_lines(self):
        text = f"# Config\n\n{BLOCK}\n\n# Footer\n"
        assert replace_block(text=text, block="") == "# Config\n\n# Footer\n"

    def test_empty_block_without_a_block_changes_nothing(self):
        assert replace_block(text="# Mine\n", block="") == "# Mine\n"

    @pytest.mark.parametrize("prose", [
        f"Everything after the `{MARKER_START}` line is generated.",
        f"The block ends at `{MARKER_END}`, do not edit it.",
    ])
    def test_a_marker_quoted_in_prose_is_not_a_boundary(self, prose):
        text = f"# Notes\n\n{prose}\n\n## Keep Me\n\n{BLOCK}\n\n# Footer\n"
        updated = replace_block(text=text, block="NEW")
        assert updated == text.replace("OLD", "NEW")
        assert replace_block(text=text, block="") == f"# Notes\n\n{prose}\n\n## Keep Me\n\n# Footer\n"

    def test_text_outside_the_markers_is_byte_identical(self):
        header = "# Private header\n\nKeep  this   spacing\t exactly.\n\n"
        footer = "\n\n## Private footer\n- [ ] trailing item  \n"
        updated = replace_block(text=f"{header}{BLOCK}{footer}", block="NEW")
        assert updated == f"{header}{MARKER_START}\nNEW\n{MARKER_END}{footer}"


class TestWriteInstructionBlock:
    def test_skips_a_missing_file(self, profile):
        (runtime,) = runtimes()
        write_instruction_block(runtime=runtime, block="NEW")
        assert not runtime.instruction_file.exists()

    def test_skips_a_runtime_without_an_instruction_file(self, profile):
        (runtime,) = runtimes()
        write_instruction_block(runtime=Runtime(**{**runtime.__dict__, "instruction_file": None}), block="NEW")

    @pytest.mark.skipif(os.geteuid() == 0, reason="root ignores file permissions")
    def test_an_unwritable_file_warns_and_does_not_raise(self, profile, capsys):
        (runtime,) = runtimes()
        runtime.instruction_file.write_text("# Mine\n")
        runtime.instruction_file.chmod(0o444)
        write_instruction_block(runtime=runtime, block="NEW")
        assert runtime.instruction_file.read_text() == "# Mine\n"
        assert "cannot update" in capsys.readouterr().err


class TestSkillTrigger:
    def test_reads_a_trigger_that_spans_lines(self, tmp_path):
        skill_md = tmp_path / "s" / "SKILL.md"
        skill_md.parent.mkdir()
        skill_md.write_text('---\nname: s\ndescription: |\n  Does things. Trigger: "a",\n    "b", "/s".\n---\n')
        assert skill_trigger(skill_dir=skill_md.parent) == '"a", "b", "/s"'

    def test_no_trigger_returns_none(self, tmp_path):
        skill_md = tmp_path / "s" / "SKILL.md"
        skill_md.parent.mkdir()
        skill_md.write_text("---\nname: s\ndescription: Does things.\n---\n")
        assert skill_trigger(skill_dir=skill_md.parent) is None


class TestInstallToRuntime:
    def test_links_skills_agents_block_and_hooks(self, profile, fake_assets):
        (runtime,) = runtimes()
        runtime.instruction_file.write_text("# mine\n")
        assert _install_to_runtime(runtime=runtime) == 2
        assert sorted(p.name for p in runtime.skills_dir.iterdir()) == ["alpha", "beta"]
        assert all(p.is_symlink() for p in runtime.skills_dir.iterdir())
        assert [p.name for p in runtime.agents_dir.iterdir()] == ["demo-reviewer.md"]
        assert "`/alpha`" in runtime.instruction_file.read_text()
        assert "log-event" in runtime.settings_file.read_text()

    def test_a_runtime_without_agents_or_hooks_gets_neither(self, profile, fake_assets):
        (claude,) = runtimes()
        bare = Runtime(**{**claude.__dict__, "agents_dir": None, "settings_file": None})
        _install_to_runtime(runtime=bare)
        assert sorted(p.name for p in bare.skills_dir.iterdir()) == ["alpha", "beta"]
        assert not claude.agents_dir.exists()
        assert not claude.settings_file.exists()


class TestCmdInstall:
    def test_install_links_every_skill(self, profile):
        result = runner.invoke(app, ["install", "--runtime", "claude"], input="y\n")
        assert result.exit_code == 0, result.output
        linked = list((profile / "skills").iterdir())
        assert linked and all(entry.is_symlink() and entry.resolve().is_dir() for entry in linked)

    def test_install_removes_links_to_renamed_skills(self, profile):
        skills_dir = profile / "skills"
        skills_dir.mkdir()
        stale = skills_dir / "ops-renamed-away"
        stale.symlink_to(Path(__file__).parents[1] / "vague" / "assets" / "skills" / "ops-renamed-away",
                         target_is_directory=True)
        runner.invoke(app, ["install", "--runtime", "claude"], input="y\n")
        assert not stale.is_symlink()

    def test_install_keeps_skills_not_owned_by_vague(self, profile, tmp_path):
        skills_dir = profile / "skills"
        (skills_dir / "my-skill").mkdir(parents=True)
        foreign = skills_dir / "foreign"
        foreign.symlink_to(tmp_path / "elsewhere", target_is_directory=True)
        result = runner.invoke(app, ["install", "--runtime", "claude"], input="y\n")
        assert result.exit_code == 0
        assert (skills_dir / "my-skill").is_dir() and foreign.is_symlink()

    def test_install_unknown_runtime(self, profile):
        result = runner.invoke(app, ["install", "--runtime", "cursor"])
        assert result.exit_code != 0
        assert "unknown runtime" in result.output

    def test_each_profile_gets_the_same_full_block(self, two_profiles, guidelines_file):
        work, personal = two_profiles
        (work / "CLAUDE.md").write_text("")
        (personal / "CLAUDE.md").write_text("")
        result = runner.invoke(app, ["install", "--runtime", "claude"], input="y\n")
        assert result.exit_code == 0, result.output
        content = (work / "CLAUDE.md").read_text()
        assert content == (personal / "CLAUDE.md").read_text()
        assert "Always explain with a diagram." in content and "`/impeccable`" in content

    def test_install_keeps_content_outside_the_fence(self, profile):
        target = profile / "CLAUDE.md"
        target.write_text(f"# Header\n\n{BLOCK}\n\n# Footer\n")
        runner.invoke(app, ["install", "--runtime", "claude:test"], input="y\n")
        content = target.read_text()
        assert content.startswith("# Header\n\n") and content.endswith("\n\n# Footer\n")
        assert "OLD" not in content and "## Skill Routing" in content


class TestCmdUninstall:
    def test_uninstall_removes_links_block_agents_and_hooks_and_keeps_the_users_own(self, profile, fake_assets):
        (profile / "CLAUDE.md").write_text("# mine\n")
        runner.invoke(app, ["install", "--runtime", "claude"], input="y\n")
        (profile / "agents" / "mine.md").write_text("---\nname: mine\n---\n")

        result = runner.invoke(app, ["uninstall", "--runtime", "claude"], input="y\n")

        assert result.exit_code == 0, result.output
        assert "removed" in result.output.lower()
        assert not any((profile / "skills").iterdir())
        assert [p.name for p in (profile / "agents").iterdir()] == ["mine.md"]
        assert (profile / "CLAUDE.md").read_text() == "# mine\n"
        assert "log-event" not in (profile / "settings.json").read_text()

    def test_uninstall_nothing_installed(self, profile):
        result = runner.invoke(app, ["uninstall", "--runtime", "claude"])
        assert result.exit_code == 0
        assert "no vague skills" in result.output.lower()


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

    def test_bundled_guidelines_file_is_included_verbatim(self):
        bundled = _get_guidelines_file().read_text().strip()
        block = _get_instructions_block()
        assert block.index(bundled) < block.index("# vague")

    def test_missing_guidelines_yields_skill_section_alone(self, tmp_path, monkeypatch):
        monkeypatch.setattr("vague.install._get_guidelines_file", lambda: tmp_path / "absent.md")

        block = _get_instructions_block()

        assert block == _build_skill_section()
        assert block.startswith("# vague")


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
