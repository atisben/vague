"""Tests for multi-runtime installer."""

import os
import shutil
from pathlib import Path

import pytest
from typer.testing import CliRunner

from vague.installer import (
    MARKER_START,
    MARKER_END,
    LEGACY_MARKER_START,
    LEGACY_MARKER_END,
    _detect_runtimes,
    _update_instruction_file,
    _remove_instruction_block,
    RUNTIME_DIRS,
)
from vague.sdk.cli import sdk_app

runner = CliRunner()


@pytest.fixture
def fake_runtimes(tmp_path, monkeypatch):
    """Set up fake runtime directories and patch RUNTIME_DIRS to use them."""
    claude_dir = tmp_path / ".claude"
    copilot_dir = tmp_path / ".copilot"
    claude_dir.mkdir()
    copilot_dir.mkdir()

    patched = {
        "claude": (str(claude_dir), str(claude_dir / "skills"), str(claude_dir / "CLAUDE.md")),
        "copilot": (str(copilot_dir), str(copilot_dir / "skills"), str(copilot_dir / "instructions.md")),
        "missing": (str(tmp_path / ".missing"), str(tmp_path / ".missing" / "skills"), None),
    }
    monkeypatch.setattr("vague.installer.RUNTIME_DIRS", patched)
    return tmp_path, patched


class TestDetectRuntimes:
    def test_detects_multiple(self, fake_runtimes):
        runtimes = _detect_runtimes()
        assert "claude" in runtimes
        assert "copilot" in runtimes

    def test_skips_missing(self, fake_runtimes):
        runtimes = _detect_runtimes()
        assert "missing" not in runtimes

    def test_returns_empty_when_none(self, tmp_path, monkeypatch):
        monkeypatch.setattr("vague.installer.RUNTIME_DIRS", {
            "gone": (str(tmp_path / "nope"), str(tmp_path / "nope" / "skills"), None),
        })
        assert _detect_runtimes() == []

    def test_skips_none_base_dir(self, tmp_path, monkeypatch):
        monkeypatch.setattr("vague.installer.RUNTIME_DIRS", {
            "generic": (None, str(tmp_path / "skills"), None),
        })
        assert _detect_runtimes() == []


class TestUpdateInstructionFile:
    def test_appends_when_no_markers(self, fake_runtimes, monkeypatch):
        tmp_path, patched = fake_runtimes
        instruction_file = Path(patched["claude"][2])
        instruction_file.write_text("# My Config\n\nSome content.\n")

        # Provide a simple template
        monkeypatch.setattr("vague.installer._get_instructions_block", lambda: "## Vague Skills\nRouting table here.")

        _update_instruction_file("claude", Path(patched["claude"][1]))

        content = instruction_file.read_text()
        assert MARKER_START in content
        assert MARKER_END in content
        assert "## Vague Skills" in content
        assert "# My Config" in content

    def test_replaces_existing_markers(self, fake_runtimes, monkeypatch):
        tmp_path, patched = fake_runtimes
        instruction_file = Path(patched["claude"][2])
        instruction_file.write_text(
            f"# Config\n\n{MARKER_START}\nold content\n{MARKER_END}\n\n# Footer\n"
        )

        monkeypatch.setattr("vague.installer._get_instructions_block", lambda: "new content")

        _update_instruction_file("claude", Path(patched["claude"][1]))

        content = instruction_file.read_text()
        assert "old content" not in content
        assert "new content" in content
        assert "# Config" in content
        assert "# Footer" in content

    def test_replaces_legacy_bastack_markers(self, fake_runtimes, monkeypatch):
        tmp_path, patched = fake_runtimes
        instruction_file = Path(patched["claude"][2])
        instruction_file.write_text(
            f"# Config\n\n{LEGACY_MARKER_START}\nlegacy stuff\n{LEGACY_MARKER_END}\n"
        )

        monkeypatch.setattr("vague.installer._get_instructions_block", lambda: "migrated content")

        _update_instruction_file("claude", Path(patched["claude"][1]))

        content = instruction_file.read_text()
        assert "legacy stuff" not in content
        assert "migrated content" in content
        assert MARKER_START in content
        assert LEGACY_MARKER_START not in content

    def test_skips_when_file_missing(self, fake_runtimes, monkeypatch):
        """Non-fatal when instruction file doesn't exist."""
        monkeypatch.setattr("vague.installer._get_instructions_block", lambda: "content")
        # Don't create the instruction file — should not raise
        _update_instruction_file("claude", Path("/tmp/fake"))

    def test_skips_when_no_instruction_file_configured(self, fake_runtimes, monkeypatch):
        """Runtimes with instruction_file=None are skipped."""
        monkeypatch.setattr("vague.installer._get_instructions_block", lambda: "content")
        _update_instruction_file("missing", Path("/tmp/fake"))


class TestRemoveInstructionBlock:
    def test_removes_vague_block(self, fake_runtimes, monkeypatch):
        tmp_path, patched = fake_runtimes
        instruction_file = Path(patched["claude"][2])
        instruction_file.write_text(
            f"# Config\n\n{MARKER_START}\nvague stuff\n{MARKER_END}\n\n# Footer\n"
        )

        _remove_instruction_block("claude")

        content = instruction_file.read_text()
        assert MARKER_START not in content
        assert "vague stuff" not in content
        assert "# Config" in content
        assert "# Footer" in content

    def test_removes_legacy_block(self, fake_runtimes, monkeypatch):
        tmp_path, patched = fake_runtimes
        instruction_file = Path(patched["claude"][2])
        instruction_file.write_text(
            f"# Config\n\n{LEGACY_MARKER_START}\nlegacy\n{LEGACY_MARKER_END}\n"
        )

        _remove_instruction_block("claude")

        content = instruction_file.read_text()
        assert LEGACY_MARKER_START not in content
        assert "legacy" not in content


class TestCmdInstall:
    def test_install_to_specific_runtime(self, fake_runtimes, vague_home):
        tmp_path, patched = fake_runtimes
        result = runner.invoke(sdk_app, ["install", "--runtime", "claude"], input="y\n")
        assert result.exit_code == 0
        skills_dir = Path(patched["claude"][1])
        assert skills_dir.exists()
        assert any(skills_dir.iterdir())

    def test_install_unknown_runtime(self, fake_runtimes, vague_home):
        result = runner.invoke(sdk_app, ["install", "--runtime", "foobar"])
        assert result.exit_code != 0
        assert "unknown runtime" in result.output

    def test_install_no_runtimes_detected(self, tmp_path, monkeypatch, vague_home):
        monkeypatch.setattr("vague.installer.RUNTIME_DIRS", {
            "gone": (str(tmp_path / "nope"), str(tmp_path / "nope" / "skills"), None),
        })
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
