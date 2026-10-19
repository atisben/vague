"""Tests for the excalidraw-render command."""

import json

from typer.testing import CliRunner

from vague.sdk.cli import sdk_app
from vague.sdk.core.excalidraw import read_drawing

runner = CliRunner()

SPEC = {
    "kind": "flow",
    "title": "Two steps",
    "steps": [{"id": "a", "label": "extract"}, {"id": "b", "label": "load"}],
    "edges": [{"from": "a", "to": "b", "label": "parquet"}],
}


def test_render_writes_the_drawing_and_reports_json(tmp_path):
    spec_path = tmp_path / "spec.json"
    spec_path.write_text(json.dumps(SPEC))
    out = tmp_path / "Excalidraw" / "Two steps.excalidraw.md"
    result = runner.invoke(sdk_app, ["excalidraw-render", str(spec_path), "--out", str(out)])
    assert result.exit_code == 0, result.output
    report = json.loads(result.output)
    assert report["mode"] == "created"
    assert report["embed"] == "![[Excalidraw/Two steps.excalidraw]]"
    assert len(read_drawing(out)["elements"]) == report["elements_added"]


def test_render_reports_spec_errors_without_writing(tmp_path):
    spec_path = tmp_path / "spec.json"
    spec_path.write_text(json.dumps({**SPEC, "edges": [{"from": "a", "to": "zzz", "label": "x"}]}))
    out = tmp_path / "out.excalidraw.md"
    result = runner.invoke(sdk_app, ["excalidraw-render", str(spec_path), "--out", str(out)])
    assert result.exit_code == 1
    assert "zzz" in result.output
    assert not out.exists()


def test_render_rejects_a_path_without_excalidraw_suffix(tmp_path):
    spec_path = tmp_path / "spec.json"
    spec_path.write_text(json.dumps(SPEC))
    result = runner.invoke(sdk_app, ["excalidraw-render", str(spec_path), "--out", str(tmp_path / "x.md")])
    assert result.exit_code == 1
    assert ".excalidraw.md" in result.output


def test_inspect_counts_live_elements_of_a_drawing(tmp_path):
    spec_path = tmp_path / "spec.json"
    spec_path.write_text(json.dumps(SPEC))
    out = tmp_path / "d.excalidraw.md"
    runner.invoke(sdk_app, ["excalidraw-render", str(spec_path), "--out", str(out)])
    result = runner.invoke(sdk_app, ["excalidraw-inspect", str(out)])
    assert result.exit_code == 0, result.output
    assert json.loads(result.output) == {"path": str(out), "elements": len(read_drawing(out)["elements"])}


def test_inspect_rejects_a_file_that_is_not_a_drawing(tmp_path):
    note = tmp_path / "note.md"
    note.write_text("# note\n")
    result = runner.invoke(sdk_app, ["excalidraw-inspect", str(note)])
    assert result.exit_code == 1
    assert "no Excalidraw drawing block" in result.output
