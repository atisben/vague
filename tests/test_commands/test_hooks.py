"""`vague install` wires the Claude Code hooks that record skill starts."""

import json

import pytest
from typer.testing import CliRunner

from vague.installer import hook_command, install_hooks, remove_hooks
from vague.sdk.cli import sdk_app

runner = CliRunner()


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
    assert settings["hooks"]["PostToolUse"][0]["matcher"] == "Skill"


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
    monkeypatch.setattr("vague.installer.shutil.which", lambda name: "/opt/bin/vague")

    assert hook_command() == "/opt/bin/vague log-event"


def test_hook_command_quotes_a_path_with_spaces(monkeypatch):
    monkeypatch.setattr("vague.installer.shutil.which", lambda name: "/my bin/vague")

    assert hook_command() == "'/my bin/vague' log-event"


def test_hook_command_falls_back_to_the_bare_name(monkeypatch):
    monkeypatch.setattr("vague.installer.shutil.which", lambda name: None)

    assert hook_command() == "vague log-event"


@pytest.fixture
def runtimes(tmp_path, monkeypatch):
    claude, cursor = tmp_path / ".claude", tmp_path / ".cursor"
    claude.mkdir()
    cursor.mkdir()
    monkeypatch.setattr("vague.installer.RUNTIME_DIRS", {
        "claude": (str(claude), str(claude / "skills"), str(claude / "CLAUDE.md")),
        "cursor": (str(cursor), str(cursor / "skills"), str(cursor / "rules" / "vague.mdc")),
    })
    return claude, cursor


def test_install_command_wires_hooks_for_claude_only(runtimes):
    claude, cursor = runtimes

    result = runner.invoke(sdk_app, ["install"], input="y\n")

    assert result.exit_code == 0, result.output
    assert "log-event" in (claude / "settings.json").read_text()
    assert not (cursor / "settings.json").exists()


def test_uninstall_command_removes_the_hooks(runtimes):
    claude, _ = runtimes
    runner.invoke(sdk_app, ["install"], input="y\n")

    result = runner.invoke(sdk_app, ["uninstall"], input="y\n")

    assert result.exit_code == 0, result.output
    assert "log-event" not in (claude / "settings.json").read_text()
