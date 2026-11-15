"""Tests for the vault scanner behind `vague vault-scan` and the /vault-clean skill."""

from __future__ import annotations

import os
from datetime import date, datetime
from pathlib import Path

import pytest

from vague.sdk.core.vault_scan import scan, similar

TODAY = date(2026, 11, 15)

GOOD_NOTE = """---
aliases: []
tags:
  - homelab
kind: knowledge
status: active
---
# 2026-04-01 - {title}

{body}

# Next Actions
- [ ]

# References
 -
"""


class Vault:
    """A temporary vault: call it to write one note, read `.root` for the vault path."""

    def __init__(self, root: Path) -> None:
        self.root = root
        (root / "6. Atomic Notes").mkdir(parents=True)

    def __call__(self, rel: str, text: str | None = None, *, body: str = "Some text.",
                 modified: date | None = None) -> Path:
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text if text is not None else GOOD_NOTE.format(title=path.stem, body=body), encoding="utf-8")
        if modified:
            stamp = datetime(modified.year, modified.month, modified.day).timestamp()
            os.utime(path, (stamp, stamp))
        return path


@pytest.fixture
def vault(tmp_path) -> Vault:
    return Vault(root=tmp_path / "Obsidian")


def _note(report, name: str):
    return next(n for n in report.notes if n.path.endswith(f"{name}.md"))


def test_scan_well_formed_note_has_no_issues(vault):
    vault("6. Atomic Notes/Proxmox Setup.md")
    report = scan(vault=vault.root, today=TODAY)
    assert _note(report, "Proxmox Setup").issues == []


def test_scan_flags_missing_frontmatter(vault):
    vault("6. Atomic Notes/Loose.md", "# Loose\n\nno metadata\n")
    assert "no-frontmatter" in _note(scan(vault=vault.root, today=TODAY), "Loose").issues


def test_scan_flags_template_prompt_saved_as_tag(vault):
    text = GOOD_NOTE.format(title="Notes entretien Adrian", body="x").replace(
        "  - homelab", "  - Problem and solution statement")
    vault("6. Atomic Notes/Notes entretien Adrian.md", text)
    issues = _note(scan(vault=vault.root, today=TODAY), "Notes entretien Adrian").issues
    assert "bad-tag: Problem and solution statement" in issues


def test_scan_flags_empty_tags(vault):
    vault("6. Atomic Notes/Bare.md", GOOD_NOTE.format(title="Bare", body="x").replace("  - homelab\n", ""))
    assert "no-tags" in _note(scan(vault=vault.root, today=TODAY), "Bare").issues


def test_scan_flags_missing_template_sections(vault):
    vault("6. Atomic Notes/Short.md", "---\ntags:\n  - personal\n---\n# 2026-01-01 - Short\n\nbody\n")
    assert "missing-sections" in _note(scan(vault=vault.root, today=TODAY), "Short").issues


def test_scan_counts_inbound_wikilinks_in_every_form(vault):
    vault("6. Atomic Notes/Target.md")
    vault("6. Atomic Notes/A.md", body="see [[Target]]")
    vault("6. Atomic Notes/B.md", body="see [[Target|the target]] and ![[Target#Setup]]")
    report = scan(vault=vault.root, today=TODAY)
    assert _note(report, "Target").inbound == 2
    assert _note(report, "A").inbound == 0


def test_scan_ignores_links_from_archived_notes(vault):
    vault("6. Atomic Notes/Target.md")
    vault("9. Archive/Old.md", body="see [[Target]]")
    assert _note(scan(vault=vault.root, today=TODAY), "Target").inbound == 0


def test_scan_skips_templates_obsidian_and_excalidraw_folders(vault):
    vault("5. Templates/Template.md")
    vault(".obsidian/plugin.md")
    vault("8. Excalidraw/Drawing.md")
    vault("6. Atomic Notes/Real.md")
    assert [n.path for n in scan(vault=vault.root, today=TODAY).notes] == ["6. Atomic Notes/Real.md"]


def test_scan_reads_kind_and_status_from_frontmatter(vault):
    vault("6. Atomic Notes/Proxmox Setup.md")
    note = _note(scan(vault=vault.root, today=TODAY), "Proxmox Setup")
    assert (note.kind, note.kind_source, note.status) == ("knowledge", "frontmatter", "active")


@pytest.mark.parametrize(("title", "tags", "expected"), [
    ("Perf Review — Jane Doe — H1-2026", [], "record"),
    ("Notes entretien Adrian", [], "record"),
    ("Interview Datadog", ["job_interview"], "record"),
    ("Eng Plan - Skill Checks Hook", [], "plan"),
    ("Vague Simplification Plan", ["engineering", "decision"], "plan"),
    ("EOY 2026 - Théo - Conversation Plan", ["decision"], "record"),
    ("Use Postgres over Mongo", ["decision"], "record"),
    ("Design Critique - vague usage UI", [], "plan"),
    ("Bayesian Optimisation", ["ml_fundamental"], "knowledge"),
])
def test_scan_guesses_kind_when_frontmatter_has_none(vault, title, tags, expected):
    tag_lines = "".join(f"  - {t}\n" for t in tags) or "  - misc\n"
    vault(f"6. Atomic Notes/{title}.md", f"---\ntags:\n{tag_lines}---\n# 2026-01-01 - {title}\n\nbody\n")
    note = _note(scan(vault=vault.root, today=TODAY), title)
    assert (note.kind, note.kind_source) == (expected, "guess")


def test_scan_age_counts_from_the_h1_date_not_the_file_time(vault):
    vault("6. Atomic Notes/Synced Today.md", modified=TODAY)
    assert _note(scan(vault=vault.root, today=TODAY), "Synced Today").age_days == (TODAY - date(2026, 4, 1)).days


def test_scan_age_falls_back_to_file_time_without_h1_date(vault):
    vault("6. Atomic Notes/Old.md", "---\ntags:\n  - x\n---\n# Old\n", modified=date(2026, 11, 5))
    assert _note(scan(vault=vault.root, today=TODAY), "Old").age_days == 10


def test_scan_marks_notes_the_ledger_knows_as_agent_written(vault):
    path = vault("6. Atomic Notes/Written By Skill.md")
    vault("6. Atomic Notes/Hand Written.md")
    report = scan(vault=vault.root, today=TODAY, agent_paths={str(path)})
    assert _note(report, "Written By Skill").agent_written is True
    assert _note(report, "Hand Written").agent_written is False


def test_scan_clusters_notes_with_near_identical_titles(vault):
    vault("6. Atomic Notes/Perf Review — Jane Doe — H1-2026.md", body="alpha")
    vault("6. Atomic Notes/Perf Review — Jane Doe — H1-2026 (Lattice).md", body="omega")
    vault("6. Atomic Notes/Proxmox Setup.md", body="unrelated")
    clusters = scan(vault=vault.root, today=TODAY).clusters
    assert len(clusters) == 1
    assert sorted(Path(p).stem for p in clusters[0]) == [
        "Perf Review — Jane Doe — H1-2026", "Perf Review — Jane Doe — H1-2026 (Lattice)"]


def test_scan_clusters_notes_with_overlapping_bodies_despite_different_titles(vault):
    body = ("Datadog interview loop: system design round, coding round, values round. "
            "Prepare the monitoring pipeline story, the alerting story and the incident story.")
    vault("6. Atomic Notes/Interview Datadog.md", body=body)
    vault("6. Atomic Notes/Data dog Interview Prep.md", body=body + " Also review SLOs.")
    vault("6. Atomic Notes/Sourdough Bread.md", body="Flour, water, salt, levain. Bake at 250 degrees.")
    clusters = scan(vault=vault.root, today=TODAY).clusters
    assert [sorted(Path(p).stem for p in c) for c in clusters] == [["Data dog Interview Prep", "Interview Datadog"]]


def test_scan_does_not_cluster_different_people_with_same_note_shape(vault):
    vault("6. Atomic Notes/Perf Review — Jane Doe — H1-2026.md", body="Jane shipped the scoring model.")
    vault("6. Atomic Notes/Perf Review — Max Roe — H1-2026.md", body="Max rebuilt the feature store.")
    assert scan(vault=vault.root, today=TODAY).clusters == []


def test_scan_lists_archived_notes_past_the_grace_period_as_expired(vault):
    text = "---\ntags:\n  - homelab\nstatus: archived\narchived: {d}\n---\n# Old\n"
    vault("9. Archive/Expired.md", text.format(d="2026-07-01"))
    vault("9. Archive/Recent.md", text.format(d="2026-11-01"))
    report = scan(vault=vault.root, today=TODAY, grace_days=90)
    assert report.expired == ["9. Archive/Expired.md"]
    assert all(not n.path.startswith("9. Archive/") for n in report.notes)


def test_similar_finds_existing_note_by_title_words(vault):
    vault("6. Atomic Notes/Home Server Hardware.md")
    vault("6. Atomic Notes/Sourdough Bread.md")
    assert similar(vault=vault.root, title="home server") == ["6. Atomic Notes/Home Server Hardware.md"]


def test_similar_matches_accents_and_case_loosely(vault):
    vault("6. Atomic Notes/Stage Planche à voile.md")
    assert similar(vault=vault.root, title="stage planche a VOILE") == ["6. Atomic Notes/Stage Planche à voile.md"]
