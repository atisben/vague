"""Tests for `vague design-check`: the source detector as a CLI and as a PostToolUse hook."""

from __future__ import annotations

import json
import shutil
from datetime import UTC, datetime
from pathlib import Path

import pytest
from typer.testing import CliRunner

from vague.sdk.cli import sdk_app
from vague.sdk.core.memory import Memory, append_memory

runner = CliRunner()

FIXTURES = Path(__file__).parent.parent / "fixtures" / "design"


@pytest.fixture
def home(vague_home_dir, monkeypatch):
    monkeypatch.setenv("VAGUE_HOME", str(vague_home_dir))
    return vague_home_dir


@pytest.fixture
def project(tmp_path):
    """A non-git project folder: its scope is its folder name."""
    root = tmp_path / "acme-shop"
    root.mkdir()
    return root


def _hook(payload: dict | str) -> object:
    raw = payload if isinstance(payload, str) else json.dumps(payload)
    return runner.invoke(sdk_app, ["design-check", "--hook"], input=raw)


def _payload(file_path: str, cwd: Path, tool_name: str = "Write") -> dict:
    return {
        "hook_event_name": "PostToolUse", "tool_name": tool_name, "session_id": "s1", "cwd": str(cwd),
        "tool_input": {"file_path": file_path},
    }


def test_hook_mode_exits_2_with_findings_on_stderr(home, project):
    page = project / "card.css"
    shutil.copy(FIXTURES / "side-tab.bad.css", page)
    result = _hook(_payload(file_path=str(page), cwd=project))
    assert result.exit_code == 2
    assert result.stdout == ""
    lines = result.stderr.splitlines()
    assert lines[0] == "vague design-check: 1 finding(s) in card.css"
    assert lines[1].startswith("card.css:4: side-tab: ")
    assert "impeccable-disable-next-line" in lines[-1]


@pytest.mark.parametrize("raw", ["clean", "", "   \n", "{not json", "[1, 2]", '{"cwd": "/x"}',
                                 '{"tool_input": {"file_path": 7}}', "missing-file"])
def test_hook_mode_exits_0_on_clean_file_empty_stdin_or_bad_json(home, project, raw):
    if raw == "clean":
        page = project / "card.css"
        shutil.copy(FIXTURES / "side-tab.good.css", page)
        raw = json.dumps(_payload(file_path=str(page), cwd=project))
    elif raw == "missing-file":
        raw = json.dumps(_payload(file_path=str(project / "gone.css"), cwd=project))
    result = _hook(raw)
    assert result.exit_code == 0
    assert result.stdout == ""
    assert result.stderr == ""


def test_hook_mode_ignores_non_ui_file(home, project):
    notes = project / "notes.md"
    notes.write_text("border-left: 4px solid #6366f1;\n", encoding="utf-8")
    result = _hook(_payload(file_path=str(notes), cwd=project))
    assert (result.exit_code, result.stdout, result.stderr) == (0, "", "")


def test_hook_mode_resolves_relative_path_against_cwd(home, project):
    (project / "src").mkdir()
    shutil.copy(FIXTURES / "side-tab.bad.css", project / "src" / "card.css")
    result = _hook(_payload(file_path="src/card.css", cwd=project, tool_name="Edit"))
    assert result.exit_code == 2
    assert result.stderr.splitlines()[0] == "vague design-check: 1 finding(s) in src/card.css"


def test_hook_mode_skips_brand_font_from_memory(home, project):
    page = project / "type.css"
    shutil.copy(FIXTURES / "overused-font.bad.css", page)
    assert _hook(_payload(file_path=str(page), cwd=project)).exit_code == 2

    append_memory(memory=Memory(
        ts=datetime.now(UTC), scope="acme-shop", key="design-type", kind="learning", skill="impeccable",
        text="Brand fonts: Inter (body 400/500) and Fraunces (display 600).",
    ))
    result = _hook(_payload(file_path=str(page), cwd=project))
    assert result.exit_code == 0, result.stderr
    assert result.stderr == ""


def test_hook_mode_exits_0_when_the_detector_raises(home, project, monkeypatch):
    from vague.sdk.core import design_rules

    def explode(**_kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(design_rules, "check", explode)
    page = project / "card.css"
    shutil.copy(FIXTURES / "side-tab.bad.css", page)
    result = _hook(_payload(file_path=str(page), cwd=project))
    assert (result.exit_code, result.stdout, result.stderr) == (0, "", "")


def test_paths_mode_exits_1_on_findings(home, project, monkeypatch):
    monkeypatch.chdir(project)
    shutil.copy(FIXTURES / "side-tab.bad.css", project / "card.css")
    result = runner.invoke(sdk_app, ["design-check", "card.css"])
    assert result.exit_code == 1
    lines = result.stdout.splitlines()
    assert lines[0].startswith("card.css:4: side-tab: ")
    assert lines[-1] == "FAILED: 1 finding(s)"


def test_paths_mode_exits_0_on_clean_dir(home, project, monkeypatch):
    monkeypatch.chdir(project)
    shutil.copy(FIXTURES / "side-tab.good.css", project / "card.css")
    result = runner.invoke(sdk_app, ["design-check", "."])
    assert result.exit_code == 0
    assert result.stdout.splitlines()[-1] == "OK: no findings"


def test_paths_mode_recurses_into_directories_and_skips_vendor_dirs(home, project, monkeypatch):
    monkeypatch.chdir(project)
    for sub in ("src/components", "node_modules/pkg", ".cache", "dist", "build"):
        (project / sub).mkdir(parents=True)
        shutil.copy(FIXTURES / "side-tab.bad.css", project / sub / "card.css")
    (project / "src" / "notes.md").write_text("border-left: 4px solid #6366f1;\n", encoding="utf-8")
    result = runner.invoke(sdk_app, ["design-check", "."])
    assert result.exit_code == 1
    finding_lines = [line for line in result.stdout.splitlines() if ": side-tab: " in line]
    assert [line.split(":")[0] for line in finding_lines] == ["src/components/card.css"]


def test_paths_mode_without_paths_is_a_usage_error(home):
    result = runner.invoke(sdk_app, ["design-check"])
    assert result.exit_code == 2
    assert "path" in result.stderr.lower()


def test_paths_mode_missing_path_is_a_usage_error(home, project, monkeypatch):
    monkeypatch.chdir(project)
    result = runner.invoke(sdk_app, ["design-check", "nope.css"])
    assert result.exit_code == 2
    assert "nope.css" in result.stderr
