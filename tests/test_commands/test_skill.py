"""Tests for skill commands."""

import json
import os
import shutil
import pytest
from pathlib import Path
from typer.testing import CliRunner

from vague.sdk.cli import sdk_app
from vague.sdk.core.frontmatter import write_md

runner = CliRunner()

VALID_SKILL_FRONTMATTER = {
    "name": "test-skill",
    "version": "1.0.0",
    "description": "A test skill",
    "sdk_commands": ["vague init"],
    "requires_slug": True,
    "requires_planning": False,
}


def test_skill_validate_passes_on_valid(tmp_path, vague_home):
    skill_dir = tmp_path / "my-skill"
    skill_dir.mkdir()
    write_md(skill_dir / "SKILL.md", VALID_SKILL_FRONTMATTER, body="# Test")
    result = runner.invoke(sdk_app, ["skill-validate", str(skill_dir)])
    assert result.exit_code == 0
    assert "OK" in result.output


def test_skill_validate_fails_missing_required_field(tmp_path, vague_home):
    skill_dir = tmp_path / "bad-skill"
    skill_dir.mkdir()
    # Missing 'description'
    write_md(skill_dir / "SKILL.md", {"name": "bad-skill", "version": "1.0.0"}, body="")
    result = runner.invoke(sdk_app, ["skill-validate", str(skill_dir)])
    assert result.exit_code != 0


def test_skill_audit_detects_bs_patterns(tmp_path, vague_home):
    skill_dir = tmp_path / "legacy-skill"
    skill_dir.mkdir()
    write_md(skill_dir / "SKILL.md", VALID_SKILL_FRONTMATTER, body="""
## Preamble
```bash
bs-config get proactive
bs-learnings-log '{"skill":"test"}'
source "$(dirname "$0")/../_preamble.sh"
```
""")
    result = runner.invoke(sdk_app, ["skill-audit", str(skill_dir)])
    assert "legacy" in result.output.lower() or "WARNINGS" in result.output


def test_skill_audit_clean_on_migrated(tmp_path, vague_home):
    skill_dir = tmp_path / "clean-skill"
    skill_dir.mkdir()
    write_md(skill_dir / "SKILL.md", VALID_SKILL_FRONTMATTER, body="""
## Preamble
```bash
CONTEXT=$(vague init)
SLUG=$(echo "$CONTEXT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['slug'])")
```
""")
    result = runner.invoke(sdk_app, ["skill-audit", str(skill_dir)])
    assert result.exit_code == 0
    assert "OK" in result.output


def test_skill_list_returns_json(vague_home):
    result = runner.invoke(sdk_app, ["skill-list"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert isinstance(data, list)
