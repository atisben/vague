"""Tests for the `vague vault-scan` command."""

from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest
from typer.testing import CliRunner

from vague.sdk.cli import sdk_app
from vague.sdk.core.memory import Memory, append_memory

runner = CliRunner()

NOTE = "---\ntags:\n  - homelab\n---\n# 2026-01-01 - {t}\n\nbody\n\n# Next Actions\n- [ ]\n\n# References\n -\n"


@pytest.fixture
def vault(tmp_path):
    root = tmp_path / "Obsidian"
    notes = root / "6. Atomic Notes"
    notes.mkdir(parents=True)
    (notes / "Home Server.md").write_text(NOTE.format(t="Home Server"), encoding="utf-8")
    (notes / "Loose.md").write_text("# Loose\n", encoding="utf-8")
    return root


def test_vault_scan_text_lists_hygiene_issues(vault):
    result = runner.invoke(sdk_app, ["vault-scan", "--vault", str(vault)])
    assert result.exit_code == 0, result.output
    assert "NOTES: 2" in result.output
    assert "6. Atomic Notes/Loose.md: no-frontmatter, missing-sections" in result.output


def test_vault_scan_json_has_notes_clusters_and_expired(vault):
    result = runner.invoke(sdk_app, ["vault-scan", "--vault", str(vault), "--json"])
    data = json.loads(result.output)
    assert sorted(data) == ["clusters", "expired", "notes"]
    assert {n["path"] for n in data["notes"]} == {"6. Atomic Notes/Home Server.md", "6. Atomic Notes/Loose.md"}


def test_vault_scan_marks_notes_logged_as_doc_memories(vault, monkeypatch, tmp_path):
    monkeypatch.setenv("VAGUE_HOME", str(tmp_path / ".vague"))
    append_memory(Memory(ts=datetime(2026, 11, 1, tzinfo=UTC), scope="o-r", key="vault-home-server", kind="doc",
                         text="Home server note", files=[str(vault / "6. Atomic Notes" / "Home Server.md")]))
    data = json.loads(runner.invoke(sdk_app, ["vault-scan", "--vault", str(vault), "--json"]).output)
    written = {n["path"]: n["agent_written"] for n in data["notes"]}
    assert written == {"6. Atomic Notes/Home Server.md": True, "6. Atomic Notes/Loose.md": False}


def test_vault_scan_similar_prints_matching_paths(vault):
    result = runner.invoke(sdk_app, ["vault-scan", "--vault", str(vault), "--similar", "home server"])
    assert result.output.strip() == "SIMILAR: 6. Atomic Notes/Home Server.md"


def test_vault_scan_similar_says_none_when_nothing_matches(vault):
    result = runner.invoke(sdk_app, ["vault-scan", "--vault", str(vault), "--similar", "sourdough"])
    assert result.output.strip() == "SIMILAR: none"


def test_vault_scan_missing_vault_is_a_usage_error(tmp_path):
    result = runner.invoke(sdk_app, ["vault-scan", "--vault", str(tmp_path / "nope")])
    assert result.exit_code == 2
