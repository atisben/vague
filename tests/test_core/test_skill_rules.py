"""Tests for the shared skill rules behind `vague skill-check`."""

import pytest

from vague.sdk.core.skill_rules import check_repo, check_skill, default_repo_root, skill_dir_for, skill_dirs


def _preamble(name: str) -> str:
    return f'```bash\neval "$(vague context --shell --skill {name})"\n```\n'


def test_check_skill_passes_on_a_valid_skill(skill_dir):
    assert check_skill(skill_dir=skill_dir()) == []


def test_check_skill_reports_missing_frontmatter_field(skill_dir):
    findings = check_skill(skill_dir=skill_dir(omit=("description",)))
    assert any("description" in f for f in findings), findings


def test_check_skill_reports_missing_skill_md(tmp_path):
    findings = check_skill(skill_dir=tmp_path)
    assert findings and "SKILL.md" in findings[0]


@pytest.mark.parametrize("line", [
    "vague learnings-log '{}'", "vague learnings-search docker", "vague observations-log '{}'",
    "vague timeline-log '{}'", "CONTEXT=$(vague init)", "vague skill-validate ./x",
    "vague skill-audit ./x", "vague memory-search --all", "bs-config get proactive",
    'source "$(dirname "$0")/../_preamble.sh"',
])
def test_check_skill_reports_removed_command(skill_dir, line):
    findings = check_skill(skill_dir=skill_dir(body=_preamble("demo-skill") + f"\n```bash\n{line}\n```\n"))
    assert any("removed" in f for f in findings), findings


def test_check_skill_requires_own_name_in_preamble(skill_dir):
    no_flag = skill_dir(name="no-flag", body='```bash\neval "$(vague context --shell)"\n```\n')
    other_name = skill_dir(name="vault", body=_preamble("vault-excalidraw"))
    assert any("--skill no-flag" in f for f in check_skill(skill_dir=no_flag))
    assert any("--skill vault" in f for f in check_skill(skill_dir=other_name))


def test_check_skill_reports_unknown_vague_command(skill_dir):
    in_body = skill_dir(name="body", body=_preamble("body") + "\n`vague frobnicate --now`\n")
    in_frontmatter = skill_dir(name="fm", fields={"sdk_commands": ["vague context", "vague frobnicate"]})
    assert any("frobnicate" in f for f in check_skill(skill_dir=in_body))
    assert any("frobnicate" in f for f in check_skill(skill_dir=in_frontmatter))


def test_check_skill_ignores_vague_in_prose(skill_dir):
    directory = skill_dir(body=_preamble("demo-skill") + "\nEdit the vague repo, not this file.\n")
    assert check_skill(skill_dir=directory) == []


def test_check_skill_reports_undeclared_memory_command(skill_dir):
    directory = skill_dir(body=_preamble("demo-skill") + '\n```bash\nvague memory-log k "fact"\n```\n')
    findings = check_skill(skill_dir=directory)
    assert any("memory-log" in f and "sdk_commands" in f for f in findings), findings

    declared = skill_dir(
        name="declared",
        fields={"sdk_commands": ["vague context", "vague memory-log"]},
        body=_preamble("declared") + '\n```bash\nvague memory-log k "fact"\n```\n',
    )
    assert check_skill(skill_dir=declared) == []


def test_check_skill_passes_on_every_bundled_skill():
    findings = [f for d in skill_dirs(repo_root=default_repo_root()) for f in check_skill(skill_dir=d)]
    assert findings == []


def test_check_repo_passes_on_this_repo():
    assert check_repo(repo_root=default_repo_root()) == []


def _fake_repo(tmp_path, skill_dir, names, readme, claude_md):
    skills_root = tmp_path / "vague" / "assets" / "skills"
    for name in names:
        skill_dir(name=name, root=skills_root)
    (tmp_path / "README.md").write_text(readme, encoding="utf-8")
    (tmp_path / "CLAUDE.md").write_text(claude_md, encoding="utf-8")
    return tmp_path


def test_check_repo_passes_on_a_consistent_repo(tmp_path, skill_dir):
    repo = _fake_repo(
        tmp_path, skill_dir, names=["alpha", "beta"],
        readme="2 markdown-based LLM skills: /alpha, /beta", claude_md="2 skills: `/alpha` `/beta`",
    )
    assert check_repo(repo_root=repo) == []


def test_check_repo_reports_skill_missing_from_readme_and_claude_md(tmp_path, skill_dir):
    repo = _fake_repo(
        tmp_path, skill_dir, names=["alpha", "beta"],
        readme="2 markdown-based LLM skills: /alpha", claude_md="2 skills: `/alpha`",
    )
    findings = check_repo(repo_root=repo)
    assert any("README.md" in f and "beta" in f for f in findings), findings
    assert any("CLAUDE.md" in f and "beta" in f for f in findings), findings


def test_check_repo_reports_wrong_skill_count(tmp_path, skill_dir):
    repo = _fake_repo(
        tmp_path, skill_dir, names=["alpha", "beta"],
        readme="3 markdown-based LLM skills: /alpha /beta", claude_md="3 skills: `/alpha` `/beta`",
    )
    findings = check_repo(repo_root=repo)
    assert any("README.md" in f and "2" in f for f in findings), findings
    assert any("CLAUDE.md" in f and "2" in f for f in findings), findings


def test_check_repo_includes_skill_findings(tmp_path, skill_dir):
    repo = _fake_repo(
        tmp_path, skill_dir, names=["alpha"],
        readme="1 markdown-based LLM skills: /alpha", claude_md="1 skills: `/alpha`",
    )
    skill_dir(name="alpha", root=repo / "vague" / "assets" / "skills", omit=("version",))
    assert any("version" in f for f in check_repo(repo_root=repo))


def test_check_repo_reports_removed_command_in_docs(tmp_path, skill_dir):
    repo = _fake_repo(
        tmp_path, skill_dir, names=["alpha"],
        readme="1 markdown-based LLM skills: /alpha\n\n    vague skill-audit ./x\n", claude_md="1 skills: `/alpha`",
    )
    assert any("README.md" in f and "skill-audit" in f for f in check_repo(repo_root=repo))


def test_skill_dir_for_resolves_dir_and_nested_file(skill_dir, tmp_path):
    directory = skill_dir()
    nested = directory / "pack" / "templates" / "x.md"
    nested.parent.mkdir(parents=True)
    nested.write_text("x", encoding="utf-8")
    assert skill_dir_for(path=directory) == directory.resolve()
    assert skill_dir_for(path=directory / "SKILL.md") == directory.resolve()
    assert skill_dir_for(path=nested) == directory.resolve()
    assert skill_dir_for(path=tmp_path) is None


def _fake_docs_repo(tmp_path, skill_dir, guidelines="", skill_body=""):
    repo = _fake_repo(tmp_path, skill_dir, names=["alpha"],
                      readme="1 markdown-based LLM skills: /alpha", claude_md="1 skills: `/alpha`")
    if skill_body:
        skill_dir(name="alpha", root=repo / "vague" / "assets" / "skills", body=_preamble("alpha") + skill_body)
    path = repo / "vague" / "assets" / "claude" / "guidelines.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(guidelines, encoding="utf-8")
    return repo


@pytest.mark.parametrize("line", [
    'PLAN=$(ls -t "$VAGUE_HOME/projects/$SLUG/designs/"*.md)',
    "~/.vague/projects/{slug}/retros/",
    'ls "${VAGUE_HOME:-$HOME/.vague}"/projects/*/diagrams/*.html',
    "writes to ~/.vague/projects/.../designs",
])
def test_check_repo_reports_reference_to_projects_state_dir(tmp_path, skill_dir, line):
    in_skill = _fake_docs_repo(tmp_path / "a", skill_dir, skill_body=f"\n```bash\n{line}\n```\n")
    in_guidelines = _fake_docs_repo(tmp_path / "b", skill_dir, guidelines=f"Plans live in `{line}`.\n")
    assert any("SKILL.md: reference-to-projects-state-dir" in f for f in check_repo(repo_root=in_skill))
    assert any("guidelines.md: reference-to-projects-state-dir" in f for f in check_repo(repo_root=in_guidelines))


def test_check_repo_ignores_project_paths_outside_vague_state(tmp_path, skill_dir):
    repo = _fake_docs_repo(tmp_path, skill_dir, guidelines="Designs live in `~/projects/personal/designs/`.\n")
    assert check_repo(repo_root=repo) == []


@pytest.mark.parametrize("line", [
    'vague memory-log <kebab-key> "Saved <name>." --files "<absolute path>" --skill <current skill>',
    'vague memory-log excalidraw-x "Drew X as a Mermaid note." --files "<path>" --skill vault-excalidraw',
])
def test_check_repo_reports_saved_learning_convention_in_guidelines(tmp_path, skill_dir, line):
    repo = _fake_docs_repo(tmp_path, skill_dir, guidelines=f"| deliverable | `{line}` |\n")
    findings = check_repo(repo_root=repo)
    assert any("guidelines.md: saved-learning-convention" in f for f in findings), findings

    fixed = _fake_docs_repo(tmp_path / "fixed", skill_dir, guidelines=f"| deliverable | `{line} --doc` |\n")
    assert check_repo(repo_root=fixed) == []


def test_file_writing_skills_log_their_deliverable_with_doc(skill_dir):
    fields = {"sdk_commands": ["vague context", "vague memory-log"]}
    learning = '\n```bash\nvague memory-log deck-x "Deck." --files "/d.html"\n```\n'
    without = skill_dir(name="slides", fields=fields, body=_preamble("slides") + learning)
    assert any("deliverable-doc-memory" in f for f in check_skill(skill_dir=without))

    with_doc = skill_dir(name="retro", fields=fields, body=_preamble("retro")
                         + '\n```bash\nvague memory-log retro-x "Retro." --doc --files "/r.md" --skill retro\n```\n')
    assert check_skill(skill_dir=with_doc) == []
    assert not any("deliverable-doc-memory" in f for f in check_skill(skill_dir=skill_dir(name="triage")))
