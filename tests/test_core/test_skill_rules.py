"""Tests for the shared skill rules behind `vague skill-check`."""

import pytest

from vague.sdk.core.skill_rules import (
    check_repo,
    check_skill,
    default_repo_root,
    skill_dir_for,
    skill_dirs,
    vague_commands_in,
)


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


def test_impeccable_frontmatter_declares_the_design_check_hook():
    import re

    from vague.sdk.core.frontmatter import read_md

    skill_md = default_repo_root() / "vague" / "assets" / "skills" / "impeccable" / "SKILL.md"
    frontmatter = read_md(path=skill_md)
    [entry] = frontmatter["hooks"]["PostToolUse"]
    assert re.fullmatch(entry["matcher"], "Edit")
    assert re.fullmatch(entry["matcher"], "Write")
    assert entry["hooks"] == [{"type": "command", "command": "vague design-check --hook"}]
    assert "vague design-check" in frontmatter["sdk_commands"]


def test_check_skill_rejects_a_malformed_hooks_block(skill_dir):
    bad = skill_dir(name="bad-hooks", fields={"hooks": {"PostToolUse": [{"matcher": "Edit", "hooks": "nope"}]}},
                    body=_preamble("bad-hooks"))
    assert any("invalid manifest" in f for f in check_skill(skill_dir=bad))


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


def test_check_repo_reports_unknown_command_in_docs(tmp_path, skill_dir):
    repo = _fake_repo(
        tmp_path, skill_dir, names=["alpha"],
        readme="1 markdown-based LLM skills: /alpha\n\n```bash\nvague skill-audit ./x\n```\n",
        claude_md="1 skills: `/alpha`",
    )
    assert any(
        "README.md" in f and "unknown-command" in f and "skill-audit" in f for f in check_repo(repo_root=repo)
    )


def test_vague_commands_in_skips_sample_output_and_wildcards():
    text = "```text\nvague memory · scope o-r · 4 memories\n```\nEvery `vague memory-*` command.\n`vague status`\n"
    assert vague_commands_in(text=text) == {"status"}


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

    doc_log = '\n```bash\nvague memory-log eng-plan-x "Plan." --doc --files "/p.md" --skill plan-eng\n```\n'
    with_doc = skill_dir(name="plan-eng", fields=fields, body=_preamble("plan-eng") + doc_log)
    assert check_skill(skill_dir=with_doc) == []
    assert not any("deliverable-doc-memory" in f for f in check_skill(skill_dir=skill_dir(name="triage")))


def test_check_skill_reports_link_to_missing_reference_file(skill_dir):
    directory = skill_dir(body=_preamble("demo-skill") + "\nRead [polish](reference/polish.md) first.\n")
    reference = directory / "reference"
    reference.mkdir()
    (reference / "polish.md").write_text(
        "See [gone](live.md), [fallback](degraded/finish-reviewer.md) and [ok](polish.md#steps).\n"
        "Ignore [site](https://example.com/x.md), [anchor](#top) and `[code](nope.md)`.\n",
        encoding="utf-8",
    )
    (reference / "degraded").mkdir()
    (reference / "degraded" / "finish-reviewer.md").write_text("[up](../polish.md)\n", encoding="utf-8")

    findings = check_skill(skill_dir=directory)

    assert [f for f in findings if "missing-reference" in f] == [
        f"{reference / 'polish.md'}: missing-reference: line 1: `live.md` does not exist in the skill"
    ], findings


def test_check_skill_reports_link_that_escapes_the_skill_dir(skill_dir):
    directory = skill_dir(body=_preamble("demo-skill") + "\nSee [other](../other/SKILL.md).\n")
    skill_dir(name="other")
    assert any("missing-reference" in f and "../other/SKILL.md" in f for f in check_skill(skill_dir=directory))


def _repo_with_agents(tmp_path, skill_dir, body, agents=()):
    repo = _fake_repo(tmp_path, skill_dir, names=["shiny", "shiny-extra"],
                      readme="2 markdown-based LLM skills: /shiny /shiny-extra",
                      claude_md="2 skills: `/shiny` `/shiny-extra`")
    skill_dir(name="shiny", root=repo / "vague" / "assets" / "skills", body=_preamble("shiny") + body)
    agents_dir = repo / "vague" / "assets" / "agents"
    agents_dir.mkdir(parents=True)
    for agent in agents:
        (agents_dir / f"{agent}.md").write_text(f"---\nname: {agent}\n---\n", encoding="utf-8")
    return repo


def test_check_repo_reports_skill_naming_a_missing_agent(tmp_path, skill_dir):
    body = (
        "\nSpawn the `shiny-finish-reviewer` agent, then the `shiny-documenter` agent.\n"
        "The agent hands off to `/shiny-extra` and `shiny-extra`.\n"
        "Style the `shiny-panel` box.\n"
    )
    repo = _repo_with_agents(tmp_path, skill_dir, body=body, agents=["shiny-finish-reviewer"])

    findings = [f for f in check_repo(repo_root=repo) if "missing-agent" in f]

    assert len(findings) == 1, findings
    assert "`shiny-documenter`" in findings[0] and "SKILL.md" in findings[0]


def test_check_repo_checks_agent_names_in_reference_files(tmp_path, skill_dir):
    repo = _repo_with_agents(tmp_path, skill_dir, body="\nNo agents here.\n")
    reference = repo / "vague" / "assets" / "skills" / "shiny" / "reference"
    reference.mkdir()
    (reference / "x.md").write_text("Hand off to the `shiny-asset-producer` subagent.\n", encoding="utf-8")
    assert any("missing-agent" in f and "shiny-asset-producer" in f for f in check_repo(repo_root=repo))


def test_check_skill_accepts_a_runtimes_list_and_rejects_unknown_runtimes(skill_dir):
    assert check_skill(skill_dir=skill_dir(name="ok", fields={"runtimes": ["claude"]})) == []
    findings = check_skill(skill_dir=skill_dir(name="bad", fields={"runtimes": ["vscode"]}))
    assert any("invalid manifest" in f and "runtimes" in f for f in findings), findings


def test_check_repo_lets_a_notice_name_dropped_upstream_agents(tmp_path, skill_dir):
    repo = _repo_with_agents(tmp_path, skill_dir, body="\nNo agents here.\n")
    notice = repo / "vague" / "assets" / "skills" / "shiny" / "NOTICE.md"
    notice.write_text("Dropped agents: `shiny-documenter`.\n", encoding="utf-8")
    assert not [f for f in check_repo(repo_root=repo) if "missing-agent" in f]
