"""Layout and file handling for Excalidraw diagrams written into an Obsidian vault."""

import json

import pytest
from pydantic import ValidationError

from vague.sdk.core.excalidraw import (
    DrawingFileError,
    parse_spec,
    read_drawing,
    render,
    write_drawing,
)
from vague.sdk.core.lzstring import compress_to_base64

TIMELINE_SPEC = {
    "kind": "timeline",
    "title": "Bob — what data trains it",
    "subtitle": "Example training day D = 2026-10-19",
    "source": {"label": "dwh_ml.training"},
    "segments": [
        {"start": "2025-09-01", "end": "2026-07-01", "px_per_day": 2, "ticks": [{"at": "2025-12-01"}]},
        {"start": "2026-09-14", "end": "2026-10-21", "px_per_day": 20, "label": "zoomed: last month"},
    ],
    "lanes": [
        {
            "label": "Credit classifier",
            "start": "2025-09-19",
            "end": "2026-05-19",
            "color": "purple",
            "arrow_label": "credit_filter\n• credit: > 4 installments\n• open banking verified",
        },
        {
            "label": "P-value reference",
            "start": "2026-09-18",
            "end": "2026-10-18",
            "color": "yellow",
            "arrow_label": "p_value_filter\n• john_p_value NOT NULL",
            "highlights": [{"start": "2026-10-16T16:30", "end": "2026-10-18", "note": "NULL on Mondays"}],
        },
    ],
    "markers": [{"at": "2026-10-19", "label": "D = training day"}],
}

FLOW_SPEC = {
    "kind": "flow",
    "title": "Nightly scoring",
    "steps": [
        {"id": "train", "label": "dwh_ml.training"},
        {"id": "bt", "label": "john_backtest"},
        {"id": "mon", "label": "monitoring"},
    ],
    "edges": [
        {"from": "train", "to": "bt", "label": "reads"},
        {"from": "bt", "to": "mon", "label": "john_p_value"},
        {"from": "train", "to": "mon", "label": "null drift"},
    ],
}

MAP_SPEC = {
    "kind": "map",
    "title": "pre-commit",
    "center": "pre-commit",
    "branches": [
        {"label": "config", "items": [".pre-commit-config.yaml"]},
        {"label": "when", "items": ["on every git commit"]},
        {"label": "fails", "items": ["commit aborted"]},
    ],
    "not": ["does not run on push"],
}


def _by_id(doc):
    return {e["id"]: e for e in doc["elements"]}


def _box(el):
    return el["x"], el["y"], el["x"] + el["width"], el["y"] + el["height"]


def _overlap(a, b):
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    return ax1 < bx2 and bx1 < ax2 and ay1 < by2 and by1 < ay2


def _assert_bindings_consistent(doc):
    ids = _by_id(doc)
    for el in doc["elements"]:
        for bound in el["boundElements"]:
            assert bound["id"] in ids, f"{el['id']} points to missing {bound['id']}"
        if el["type"] == "arrow":
            for end in ("startBinding", "endBinding"):
                if el[end]:
                    target = ids[el[end]["elementId"]]
                    assert {"type": "arrow", "id": el["id"]} in target["boundElements"]
        if el["type"] == "text" and el["containerId"]:
            assert {"type": "text", "id": el["id"]} in ids[el["containerId"]]["boundElements"]


def _arrow_labels(doc):
    ids = _by_id(doc)
    return {
        ids[el["containerId"]]["endBinding"]["elementId"]: el
        for el in doc["elements"]
        if el["type"] == "text" and el["containerId"] and ids[el["containerId"]]["type"] == "arrow"
    }


# --- timeline


def test_timeline_bar_width_is_proportional_to_dates():
    doc = render(parse_spec(TIMELINE_SPEC))
    lanes = [e for e in doc["elements"] if e.get("customData", {}).get("role") == "lane"]
    credit, pvalue = lanes
    assert credit["width"] == pytest.approx(242 * 2)
    assert pvalue["width"] == pytest.approx(30 * 20)


def test_timeline_zoomed_segment_sits_right_of_the_first():
    doc = render(parse_spec(TIMELINE_SPEC))
    credit, pvalue = [e for e in doc["elements"] if e.get("customData", {}).get("role") == "lane"]
    assert pvalue["x"] > credit["x"] + credit["width"]


def test_timeline_links_source_to_every_lane_with_the_filter_label():
    doc = render(parse_spec(TIMELINE_SPEC))
    labels = _arrow_labels(doc)
    lane_ids = [e["id"] for e in doc["elements"] if e.get("customData", {}).get("role") == "lane"]
    assert set(labels) == set(lane_ids)
    texts = sorted(t["text"] for t in labels.values())
    assert texts[0].startswith("credit_filter")
    _assert_bindings_consistent(doc)


def test_timeline_arrow_labels_fit_between_source_and_lane():
    doc = render(parse_spec(TIMELINE_SPEC))
    ids = _by_id(doc)
    source = next(e for e in doc["elements"] if e.get("customData", {}).get("role") == "source")
    for lane_id, label in _arrow_labels(doc).items():
        assert not _overlap(_box(label), _box(source))
        assert not _overlap(_box(label), _box(ids[lane_id]))


def test_timeline_lane_labels_do_not_collide():
    doc = render(parse_spec(TIMELINE_SPEC))
    boxes = [_box(t) for t in _arrow_labels(doc).values()]
    assert not _overlap(*boxes)


def test_timeline_highlight_starts_at_its_datetime():
    doc = render(parse_spec(TIMELINE_SPEC))
    pvalue = [e for e in doc["elements"] if e.get("customData", {}).get("role") == "lane"][1]
    highlight = next(e for e in doc["elements"] if e.get("customData", {}).get("role") == "highlight")
    days_after_lane_start = 28 + 16.5 / 24  # 2026-09-18 → 2026-10-16T16:30
    assert highlight["x"] - pvalue["x"] == pytest.approx(days_after_lane_start * 20)


def test_timeline_rejects_a_date_outside_every_segment():
    spec = json.loads(json.dumps(TIMELINE_SPEC))
    spec["lanes"][0]["start"] = "2024-01-01"
    with pytest.raises(ValueError, match="2024-01-01"):
        render(parse_spec(spec))


# --- flow


def test_flow_numbers_steps_left_to_right():
    doc = render(parse_spec(FLOW_SPEC))
    steps = [e for e in doc["elements"] if e.get("customData", {}).get("role") == "step"]
    ids = _by_id(doc)
    labels = [ids[s["boundElements"][0]["id"]]["text"] for s in sorted(steps, key=lambda s: s["x"])]
    assert labels == ["1. dwh_ml.training", "2. john_backtest", "3. monitoring"]


def test_flow_labels_every_edge():
    doc = render(parse_spec(FLOW_SPEC))
    arrows = [e for e in doc["elements"] if e["type"] == "arrow"]
    assert len(arrows) == 3
    assert all(any(b["type"] == "text" for b in a["boundElements"]) for a in arrows)
    _assert_bindings_consistent(doc)


def test_flow_rejects_more_than_seven_steps():
    spec = json.loads(json.dumps(FLOW_SPEC))
    spec["steps"] = [{"id": f"s{i}", "label": f"step {i}"} for i in range(8)]
    with pytest.raises(ValidationError):
        parse_spec(spec)


def test_flow_rejects_edge_to_unknown_step():
    spec = json.loads(json.dumps(FLOW_SPEC))
    spec["edges"].append({"from": "train", "to": "ghost", "label": "x"})
    with pytest.raises(ValidationError, match="ghost"):
        parse_spec(spec)


# --- map


def test_map_draws_center_branches_and_a_dashed_not_branch():
    doc = render(parse_spec(MAP_SPEC))
    roles = [e.get("customData", {}).get("role") for e in doc["elements"]]
    assert roles.count("center") == 1
    assert roles.count("branch") == 3
    not_box = next(e for e in doc["elements"] if e.get("customData", {}).get("role") == "not")
    assert not_box["strokeStyle"] == "dashed"
    _assert_bindings_consistent(doc)


def test_map_branch_boxes_do_not_overlap():
    doc = render(parse_spec(MAP_SPEC))
    boxes = [_box(e) for e in doc["elements"] if e.get("customData", {}).get("role") in ("branch", "not", "center")]
    for i, a in enumerate(boxes):
        for b in boxes[i + 1 :]:
            assert not _overlap(a, b)


# --- files

EMPTY_COMPRESSED = """---

excalidraw-plugin: parsed
tags: [excalidraw]

---
==⚠  Switch to EXCALIDRAW VIEW in the MORE OPTIONS menu of this document. ⚠==


## Drawing
```compressed-json
{payload}
```
%%
"""


def _existing(tmp_path, elements):
    doc = {"type": "excalidraw", "version": 2, "elements": elements, "appState": {}, "files": {}}
    path = tmp_path / "existing.excalidraw.md"
    path.write_text(EMPTY_COMPRESSED.format(payload=compress_to_base64(json.dumps(doc))), encoding="utf-8")
    return path


def test_write_creates_a_new_compressed_drawing(tmp_path):
    path = tmp_path / "Excalidraw" / "new.excalidraw.md"
    doc = render(parse_spec(FLOW_SPEC))
    result = write_drawing(path, doc)
    assert result.mode == "created"
    text = path.read_text(encoding="utf-8")
    assert "excalidraw-plugin: parsed" in text
    assert "```compressed-json" in text
    assert len(read_drawing(path)["elements"]) == len(doc["elements"])


def test_write_fills_an_empty_drawing_and_keeps_its_header(tmp_path):
    path = _existing(tmp_path, [])
    result = write_drawing(path, render(parse_spec(FLOW_SPEC)))
    assert result.mode == "filled"
    assert path.read_text(encoding="utf-8").startswith("---\n\nexcalidraw-plugin: parsed")
    assert read_drawing(path)["elements"]


def test_write_appends_below_existing_content_without_removing_it(tmp_path):
    old = render(parse_spec(MAP_SPEC))["elements"]
    path = _existing(tmp_path, old)
    result = write_drawing(path, render(parse_spec(FLOW_SPEC)))
    assert result.mode == "appended"
    elements = read_drawing(path)["elements"]
    old_ids = {e["id"] for e in old}
    assert old_ids <= {e["id"] for e in elements}
    old_bottom = max(e["y"] + e["height"] for e in old)
    new_top = min(e["y"] for e in elements if e["id"] not in old_ids)
    assert new_top > old_bottom


def test_write_keeps_ids_unique_when_appending_the_same_diagram_twice(tmp_path):
    path = _existing(tmp_path, render(parse_spec(FLOW_SPEC))["elements"])
    write_drawing(path, render(parse_spec(FLOW_SPEC)))
    ids = [e["id"] for e in read_drawing(path)["elements"]]
    assert len(ids) == len(set(ids))
    _assert_bindings_consistent(read_drawing(path))


def test_read_accepts_plain_json_drawings(tmp_path):
    path = tmp_path / "plain.excalidraw.md"
    path.write_text('# Excalidraw Data\n%%\n## Drawing\n```json\n{"elements": [{"id": "a"}]}\n```\n%%\n')
    assert read_drawing(path)["elements"] == [{"id": "a"}]


def test_write_refuses_a_file_without_drawing_data(tmp_path):
    path = tmp_path / "note.md"
    path.write_text("# Just a note\n")
    with pytest.raises(DrawingFileError):
        write_drawing(path, render(parse_spec(FLOW_SPEC)))
    assert path.read_text() == "# Just a note\n"
