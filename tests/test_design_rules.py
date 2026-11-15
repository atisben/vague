"""Tests for vague/design_rules.py."""

from __future__ import annotations

import json
import shutil
from datetime import UTC, datetime
from pathlib import Path

import pytest
from typer.testing import CliRunner

from vague import design_rules
from vague.cli import app
from vague.design_rules import RULES, Finding, brand_fonts_from_memory, check, parse_brand_fonts
from vague.memory import Memory, append_memory

FIXTURES = Path(__file__).parent / "fixtures" / "design"


RULE_IDS = [
    "ai-color-palette",
    "border-accent-on-rounded",
    "bounce-easing",
    "broken-image",
    "gradient-text",
    "gray-on-color",
    "overused-font",
    "side-tab",
]


FIXTURE_PAIRS = [
    ("ai-color-palette", "html"),
    ("border-accent-on-rounded", "css"),
    ("border-accent-on-rounded", "html"),
    ("bounce-easing", "css"),
    ("bounce-easing", "html"),
    ("broken-image", "html"),
    ("gradient-text", "css"),
    ("gradient-text", "html"),
    ("gray-on-color", "html"),
    ("overused-font", "css"),
    ("side-tab", "css"),
    ("side-tab", "html"),
]


def _ids(findings: list[Finding]) -> list[str]:
    return [f.rule_id for f in findings]


def test_rule_list_is_fixed():
    assert sorted({rule.id for rule in RULES}) == RULE_IDS


def test_every_rule_has_a_fixture_pair():
    assert sorted({rule_id for rule_id, _ in FIXTURE_PAIRS}) == RULE_IDS


@pytest.mark.parametrize(("rule_id", "suffix"), FIXTURE_PAIRS)
def test_rule_flags_bad_fixture(rule_id, suffix):
    findings = check(path=FIXTURES / f"{rule_id}.bad.{suffix}")
    assert rule_id in _ids(findings)
    assert all(f.message for f in findings)


@pytest.mark.parametrize(("rule_id", "suffix"), FIXTURE_PAIRS)
def test_rule_passes_good_fixture(rule_id, suffix):
    findings = check(path=FIXTURES / f"{rule_id}.good.{suffix}")
    assert rule_id not in _ids(findings)


def test_finding_carries_line_and_path():
    path = FIXTURES / "side-tab.bad.css"
    [finding] = check(path=path)
    assert (finding.rule_id, finding.line, finding.path) == ("side-tab", 4, path)


def test_broken_image_flags_each_tag_on_its_own_line():
    findings = check(path=FIXTURES / "broken-image.bad.html")
    assert [f.line for f in findings] == [2, 3, 4]


def test_disable_comment_suppresses_one_rule_only(tmp_path):
    page = tmp_path / "card.css"
    page.write_text(
        ".card {\n"
        "  border-radius: 12px;\n"
        "  /* impeccable-disable-next-line side-tab: brand callout */\n"
        "  border-left: 4px solid #6366f1;\n"
        "  transition: transform 1s cubic-bezier(0.68, -0.55, 0.265, 1.55); /* impeccable-disable-line side-tab */\n"
        "}\n",
        encoding="utf-8",
    )
    assert _ids(check(path=page)) == ["bounce-easing"]


def test_disable_directive_without_line_suffix_covers_the_whole_file(tmp_path):
    page = tmp_path / "page.html"
    page.write_text(
        "<!-- impeccable-disable broken-image -- exported doc -->\n"
        "<img alt=\"a\">\n"
        "<p class=\"text-gray-400 bg-blue-600\">x</p>\n"
        "<img alt=\"b\">\n",
        encoding="utf-8",
    )
    assert _ids(check(path=page)) == ["gray-on-color"]


def test_disable_directive_with_no_rule_suppresses_every_rule(tmp_path):
    page = tmp_path / "page.html"
    page.write_text("<img alt=\"a\"> <!-- impeccable-disable-line -->\n<img alt=\"b\">\n", encoding="utf-8")
    assert [f.line for f in check(path=page)] == [2]


def test_css_named_in_prose_code_samples_or_comments_is_not_flagged(tmp_path):
    page = tmp_path / "docs.html"
    page.write_text(
        "<style>\n  /* .old { border-radius: 8px; border-left: 4px solid #6366f1; } */\n"
        "  body { color: #111; }\n</style>\n"
        "<p><code>background-clip: text</code> gradients stop tripping the rules.</p>\n"
        "<pre><code>.hero { background: linear-gradient(#667eea, #764ba2); background-clip: text; }</code></pre>\n"
        "<p>The Tailwind form pairs bg-clip-text with bg-gradient-to-r on one element.</p>\n"
        "<!-- <img alt=\"draft\"> and animation: bounce 1s are only commented out -->\n"
        "<p>Avoid cubic-bezier(0.68, -0.55, 0.265, 1.55) and font-family: Inter in new work.</p>\n",
        encoding="utf-8",
    )
    assert check(path=page) == []


def test_style_block_and_style_attribute_are_still_read(tmp_path):
    page = tmp_path / "page.html"
    page.write_text(
        "<style>\n  .card { border-radius: 8px; border-left: 4px solid #6366f1; }\n</style>\n"
        "<div style=\"border-radius: 8px; border-top: 4px solid #10b981\">x</div>\n",
        encoding="utf-8",
    )
    assert _ids(check(path=page)) == ["side-tab", "border-accent-on-rounded"]


def test_non_ui_extension_yields_no_findings(tmp_path):
    notes = tmp_path / "notes.md"
    notes.write_text((FIXTURES / "side-tab.bad.css").read_text(encoding="utf-8"), encoding="utf-8")
    assert check(path=notes) == []


def test_markup_rules_skip_plain_scripts(tmp_path):
    script = tmp_path / "template.ts"
    script.write_text("const html = '<img alt=\"x\">';\n", encoding="utf-8")
    assert check(path=script) == []


def test_style_rules_run_on_plain_scripts(tmp_path):
    script = tmp_path / "theme.ts"
    script.write_text("export const ease = 'cubic-bezier(0.68, -0.55, 0.265, 1.55)';\n", encoding="utf-8")
    assert _ids(check(path=script)) == ["bounce-easing"]


def test_unreadable_or_binary_file_yields_no_findings(tmp_path):
    assert check(path=tmp_path / "missing.css") == []
    assert check(path=tmp_path) == []
    binary = tmp_path / "logo.css"
    binary.write_bytes(b"border-left: 4px solid red;\x00\x01")
    assert check(path=binary) == []
    latin = tmp_path / "old.css"
    latin.write_bytes(b".a { border-radius: 8px; border-left: 4px solid red; } /* caf\xe9 */")
    assert check(path=latin) == []


def test_parse_brand_fonts_reads_families_from_the_brief_line():
    text = ("Brand fonts: Fraunces (display, 600, 3-4.5rem, tracking -0.02em) and Inter (body 400/500, 1rem/1.6, "
            "65ch). JetBrains Mono 400 for SKUs. Scale ratio 1.25.")
    assert parse_brand_fonts(text=text) == frozenset({"fraunces", "inter", "jetbrains mono"})


@pytest.mark.parametrize("text", ["", "a friendly sans", "Brand fonts:", None])
def test_parse_brand_fonts_without_a_family_is_empty(text):
    assert parse_brand_fonts(text=text) == frozenset()


def test_brand_font_from_design_type_learning_is_not_flagged(tmp_path, vague_home):
    bad = FIXTURES / "overused-font.bad.css"
    assert "overused-font" in _ids(check(path=bad))
    assert "overused-font" not in _ids(check(path=bad, brand_fonts=frozenset({"inter"})))

    append_memory(memory=Memory(
        ts=datetime.now(UTC), scope="acme-shop", key="design-type", kind="learning", skill="impeccable",
        text="Brand fonts: Inter (body 400/500) and Fraunces (display 600). JetBrains Mono 400 for SKUs.",
    ))
    append_memory(memory=Memory(
        ts=datetime.now(UTC), scope="other-repo", key="design-type", kind="learning", skill="impeccable",
        text="Brand fonts: Roboto (body).",
    ))
    fonts = brand_fonts_from_memory(scope="acme-shop")
    assert fonts == frozenset({"inter", "fraunces", "jetbrains mono"})
    assert "overused-font" not in _ids(check(path=bad, brand_fonts=fonts))
    assert brand_fonts_from_memory(scope="no-such-repo") == frozenset()


def test_brand_fonts_from_memory_never_raises(vague_home, monkeypatch):
    (vague_home / "memory.jsonl").write_text("not json\n", encoding="utf-8")
    assert brand_fonts_from_memory(scope="acme-shop") == frozenset()

    def explode(**_kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(design_rules, "search", explode)
    assert brand_fonts_from_memory(scope="acme-shop") == frozenset()


runner = CliRunner()


@pytest.fixture
def project(tmp_path):
    """A non-git project folder: its scope is its folder name."""
    root = tmp_path / "acme-shop"
    root.mkdir()
    return root


def _hook(payload: dict | str) -> object:
    raw = payload if isinstance(payload, str) else json.dumps(payload)
    return runner.invoke(app, ["design-check", "--hook"], input=raw)


def _payload(file_path: str, cwd: Path, tool_name: str = "Write") -> dict:
    return {
        "hook_event_name": "PostToolUse", "tool_name": tool_name, "session_id": "s1", "cwd": str(cwd),
        "tool_input": {"file_path": file_path},
    }


def test_hook_mode_exits_2_with_findings_on_stderr(vague_home, project):
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
def test_hook_mode_exits_0_on_clean_file_empty_stdin_or_bad_json(vague_home, project, raw):
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


def test_hook_mode_ignores_non_ui_file(vague_home, project):
    notes = project / "notes.md"
    notes.write_text("border-left: 4px solid #6366f1;\n", encoding="utf-8")
    result = _hook(_payload(file_path=str(notes), cwd=project))
    assert (result.exit_code, result.stdout, result.stderr) == (0, "", "")


def test_hook_mode_resolves_relative_path_against_cwd(vague_home, project):
    (project / "src").mkdir()
    shutil.copy(FIXTURES / "side-tab.bad.css", project / "src" / "card.css")
    result = _hook(_payload(file_path="src/card.css", cwd=project, tool_name="Edit"))
    assert result.exit_code == 2
    assert result.stderr.splitlines()[0] == "vague design-check: 1 finding(s) in src/card.css"


def test_hook_mode_skips_brand_font_from_memory(vague_home, project):
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


def test_hook_mode_exits_0_when_the_detector_raises(vague_home, project, monkeypatch):
    from vague import design_rules

    def explode(**_kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(design_rules, "check", explode)
    page = project / "card.css"
    shutil.copy(FIXTURES / "side-tab.bad.css", page)
    result = _hook(_payload(file_path=str(page), cwd=project))
    assert (result.exit_code, result.stdout, result.stderr) == (0, "", "")


def test_paths_mode_exits_1_on_findings(vague_home, project, monkeypatch):
    monkeypatch.chdir(project)
    shutil.copy(FIXTURES / "side-tab.bad.css", project / "card.css")
    result = runner.invoke(app, ["design-check", "card.css"])
    assert result.exit_code == 1
    lines = result.stdout.splitlines()
    assert lines[0].startswith("card.css:4: side-tab: ")
    assert lines[-1] == "FAILED: 1 finding(s)"


def test_paths_mode_exits_0_on_clean_dir(vague_home, project, monkeypatch):
    monkeypatch.chdir(project)
    shutil.copy(FIXTURES / "side-tab.good.css", project / "card.css")
    result = runner.invoke(app, ["design-check", "."])
    assert result.exit_code == 0
    assert result.stdout.splitlines()[-1] == "OK: no findings"


def test_paths_mode_recurses_into_directories_and_skips_vendor_dirs(vague_home, project, monkeypatch):
    monkeypatch.chdir(project)
    for sub in ("src/components", "node_modules/pkg", ".cache", "dist", "build"):
        (project / sub).mkdir(parents=True)
        shutil.copy(FIXTURES / "side-tab.bad.css", project / sub / "card.css")
    (project / "src" / "notes.md").write_text("border-left: 4px solid #6366f1;\n", encoding="utf-8")
    result = runner.invoke(app, ["design-check", "."])
    assert result.exit_code == 1
    finding_lines = [line for line in result.stdout.splitlines() if ": side-tab: " in line]
    assert [line.split(":")[0] for line in finding_lines] == ["src/components/card.css"]


def test_paths_mode_without_paths_is_a_usage_error(vague_home):
    result = runner.invoke(app, ["design-check"])
    assert result.exit_code == 2
    assert "path" in result.stderr.lower()


def test_paths_mode_missing_path_is_a_usage_error(vague_home, project, monkeypatch):
    monkeypatch.chdir(project)
    result = runner.invoke(app, ["design-check", "nope.css"])
    assert result.exit_code == 2
    assert "nope.css" in result.stderr
