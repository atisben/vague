"""Render semantic diagram specs into Obsidian Excalidraw drawings.

The skill writes *what* to show (lanes and dates, steps and edges, branches); this module
owns *where* it goes: coordinates, arrow bindings, and the plugin's file format.
"""

from __future__ import annotations

import json
import random
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, field_validator, model_validator

from vague.sdk.core.lzstring import compress_to_base64, decompress_from_base64

FONT_SIZE = 16
LINE_HEIGHT = 1.25
# Virgil (fontFamily 1) averages a bit over half an em per character; overestimating keeps text inside boxes.
CHAR_WIDTH = 0.58

# (background, stroke, text) from the Excalidraw palette.
PALETTE: dict[str, tuple[str, str, str]] = {
    "blue": ("#e7f5ff", "#1971c2", "#1864ab"),
    "purple": ("#d0bfff", "#7048e8", "#5f3dc4"),
    "green": ("#b2f2bb", "#2f9e44", "#2b8a3e"),
    "yellow": ("#ffec99", "#f08c00", "#e67700"),
    "orange": ("#ffd8a8", "#e8590c", "#d9480f"),
    "red": ("#ff8787", "#e03131", "#c92a2a"),
    "grey": ("#dee2e6", "#868e96", "#495057"),
}
Color = Literal["blue", "purple", "green", "yellow", "orange", "red", "grey"]
INK = "#1e1e1e"
MUTED = "#495057"


# --- spec


class _Spec(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


def _parse_when(value: str) -> datetime:
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    raise ValueError(f"'{value}' is not YYYY-MM-DD or YYYY-MM-DDTHH:MM")


class _Dated(_Spec):
    @field_validator("start", "end", "at", mode="after", check_fields=False)
    @classmethod
    def _check_date(cls, value: str) -> str:
        _parse_when(value)
        return value


class Tick(_Dated):
    at: str
    label: str | None = None


class Segment(_Dated):
    start: str
    end: str
    px_per_day: float = 2
    label: str | None = None
    ticks: list[Tick] = []


class Highlight(_Dated):
    start: str
    end: str
    color: Color = "red"
    note: str | None = None


class Lane(_Dated):
    label: str
    start: str
    end: str
    color: Color = "green"
    caption: str | None = None
    arrow_label: str | None = None
    highlights: list[Highlight] = []


class Marker(_Dated):
    at: str
    label: str
    color: Color = "red"


class Source(_Spec):
    label: str
    color: Color = "blue"


class TimelineSpec(_Spec):
    kind: Literal["timeline"]
    title: str
    subtitle: str | None = None
    source: Source
    segments: list[Segment] = Field(min_length=1)
    lanes: list[Lane] = Field(min_length=1, max_length=7)
    markers: list[Marker] = []


class Step(_Spec):
    id: str
    label: str
    color: Color = "blue"


class Edge(_Spec):
    from_: str = Field(alias="from")
    to: str
    label: str


class FlowSpec(_Spec):
    kind: Literal["flow"]
    title: str
    subtitle: str | None = None
    steps: list[Step] = Field(min_length=2, max_length=7)
    edges: list[Edge] = Field(min_length=1)

    @model_validator(mode="after")
    def _edges_point_to_steps(self) -> FlowSpec:
        known = {s.id for s in self.steps}
        unknown = sorted(({e.from_ for e in self.edges} | {e.to for e in self.edges}) - known)
        if unknown:
            raise ValueError(f"edges point to unknown step ids: {unknown}")
        return self


class Branch(_Spec):
    label: str
    items: list[str] = []
    color: Color = "green"


class MapSpec(_Spec):
    kind: Literal["map"]
    title: str
    subtitle: str | None = None
    center: str
    branches: list[Branch] = Field(min_length=2, max_length=7)
    not_: list[str] = Field(default=[], alias="not")


DiagramSpec = Annotated[TimelineSpec | FlowSpec | MapSpec, Field(discriminator="kind")]
_SPEC_ADAPTER: TypeAdapter[TimelineSpec | FlowSpec | MapSpec] = TypeAdapter(DiagramSpec)


def parse_spec(data: dict[str, Any]) -> TimelineSpec | FlowSpec | MapSpec:
    return _SPEC_ADAPTER.validate_python(data)


# --- element builder


def text_size(text: str, size: int = FONT_SIZE) -> tuple[float, float]:
    lines = text.split("\n")
    return max(len(line) for line in lines) * size * CHAR_WIDTH, len(lines) * size * LINE_HEIGHT


class _Canvas:
    def __init__(self, seed: int) -> None:
        self.elements: list[dict[str, Any]] = []
        self._rng = random.Random(seed)
        self._count = 0

    def _base(self, kind: str, x: float, y: float, w: float, h: float, **style: Any) -> dict[str, Any]:
        self._count += 1
        el = {
            "id": f"{kind[:2]}{self._count:03d}{self._rng.randrange(16**6):06x}",
            "type": kind,
            "x": x,
            "y": y,
            "width": w,
            "height": h,
            "angle": 0,
            "strokeColor": style.get("stroke", INK),
            "backgroundColor": style.get("bg", "transparent"),
            "fillStyle": style.get("fill", "solid"),
            "strokeWidth": style.get("stroke_width", 2),
            "strokeStyle": style.get("stroke_style", "solid"),
            "roughness": 1,
            "opacity": 100,
            "groupIds": [],
            "frameId": None,
            "roundness": style.get("roundness"),
            "seed": self._rng.randrange(1, 2**31),
            "version": 1,
            "versionNonce": self._rng.randrange(1, 2**31),
            "isDeleted": False,
            "boundElements": [],
            "updated": 1,
            "link": None,
            "locked": False,
        }
        if "role" in style:
            el["customData"] = {"role": style["role"]}
        self.elements.append(el)
        return el

    def text(
        self,
        x: float,
        y: float,
        text: str,
        size: int = FONT_SIZE,
        color: str = INK,
        container: dict[str, Any] | None = None,
        align: str = "left",
    ) -> dict[str, Any]:
        w, h = text_size(text, size)
        el = self._base("text", x, y, w, h, stroke=color)
        el.update(
            {
                "text": text,
                "originalText": text,
                "fontSize": size,
                "fontFamily": 1,
                "textAlign": align,
                "verticalAlign": "middle" if container else "top",
                "containerId": container["id"] if container else None,
                "autoResize": True,
                "lineHeight": LINE_HEIGHT,
            }
        )
        if container:
            container["boundElements"].append({"type": "text", "id": el["id"]})
        return el

    def box(
        self, x: float, y: float, w: float, h: float, label: str | None = None, color: Color = "blue", **style: Any
    ) -> dict[str, Any]:
        bg, stroke, _ = PALETTE[color]
        style = {"bg": bg, "stroke": stroke, "roundness": {"type": 3}, **style}
        el = self._base("rectangle", x, y, w, h, **style)
        if label:
            tw, th = text_size(label)
            self.text(x + (w - tw) / 2, y + (h - th) / 2, label, container=el, align="center")
        return el

    def line(self, x1: float, y1: float, x2: float, y2: float, **style: Any) -> dict[str, Any]:
        el = self._base("line", x1, y1, x2 - x1, y2 - y1, **style)
        el.update(
            {
                "points": [[0, 0], [x2 - x1, y2 - y1]],
                "lastCommittedPoint": None,
                "startBinding": None,
                "endBinding": None,
                "startArrowhead": None,
                "endArrowhead": None,
            }
        )
        return el

    def arrow(
        self,
        src: dict[str, Any],
        dst: dict[str, Any],
        points: list[tuple[float, float]],
        label: str | None = None,
        color: Color | None = None,
        head: bool = True,
    ) -> dict[str, Any]:
        x0, y0 = points[0]
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        stroke, text_color = (PALETTE[color][1], PALETTE[color][2]) if color else (INK, INK)
        el = self._base("arrow", x0, y0, max(xs) - min(xs), max(ys) - min(ys), stroke=stroke, roundness={"type": 2})
        el.update(
            {
                "points": [[px - x0, py - y0] for px, py in points],
                "lastCommittedPoint": None,
                "startBinding": {"elementId": src["id"], "focus": 0, "gap": 4},
                "endBinding": {"elementId": dst["id"], "focus": 0, "gap": 4},
                "startArrowhead": None,
                "endArrowhead": "arrow" if head else None,
                "elbowed": False,
            }
        )
        src["boundElements"].append({"type": "arrow", "id": el["id"]})
        dst["boundElements"].append({"type": "arrow", "id": el["id"]})
        if label:
            # Excalidraw centres an arrow label on the middle point of the path.
            mid = points[len(points) // 2] if len(points) % 2 else _midpoint(points[0], points[-1])
            tw, th = text_size(label)
            self.text(mid[0] - tw / 2, mid[1] - th / 2, label, color=text_color, container=el)
        return el


def _midpoint(a: tuple[float, float], b: tuple[float, float]) -> tuple[float, float]:
    return (a[0] + b[0]) / 2, (a[1] + b[1]) / 2


def _header(canvas: _Canvas, title: str, subtitle: str | None, top: float) -> None:
    canvas.text(0, top - 120, title, size=32)
    if subtitle:
        canvas.text(0, top - 70, subtitle, color=MUTED)


# --- timeline

SOURCE_W = 330
ARROW_PAD = 40
SEGMENT_GAP = 90


class _Axis:
    def __init__(self, segments: list[Segment], origin: float) -> None:
        self.spans: list[tuple[datetime, datetime, float, float]] = []
        x = origin
        for seg in segments:
            start, end = _parse_when(seg.start), _parse_when(seg.end)
            self.spans.append((start, end, x, seg.px_per_day))
            x += _days(start, end) * seg.px_per_day + SEGMENT_GAP
        self.right = x - SEGMENT_GAP

    def x(self, when: str) -> float:
        moment = _parse_when(when)
        for start, end, x0, px in self.spans:
            if start <= moment <= end:
                return x0 + _days(start, moment) * px
        raise ValueError(f"date {when} is outside every axis segment")


def _days(a: datetime, b: datetime) -> float:
    return (b - a).total_seconds() / 86400


def _render_timeline(spec: TimelineSpec, canvas: _Canvas) -> None:
    lane_h = 60
    probe = _Axis(spec.segments, 0)
    starts = [probe.x(lane.start) for lane in spec.lanes]
    label_sizes = [text_size(lane.arrow_label) if lane.arrow_label else (0.0, 0.0) for lane in spec.lanes]
    # Shift the axis right until every arrow label fits between the source box and its lane.
    origin = max(SOURCE_W + w + 2 * ARROW_PAD - s for (w, _), s in zip(label_sizes, starts, strict=True))
    origin = max(origin, SOURCE_W + 2 * ARROW_PAD)
    axis = _Axis(spec.segments, origin)

    lane_ys: list[float] = []
    y = 0.0
    for lane, (_, label_h) in zip(spec.lanes, label_sizes, strict=True):
        y = max(y, label_h / 2 - lane_h / 2)
        lane_ys.append(y)
        notes_h = max((text_size(h.note)[1] + 30 for h in lane.highlights if h.note), default=0)
        below = lane_h + 40 + notes_h
        y += max(below, label_h / 2 + lane_h / 2) + 70

    axis_y = y + 40
    _header(canvas, spec.title, spec.subtitle, 0)
    source = canvas.box(0, -20, SOURCE_W, axis_y - 80, spec.source.label, spec.source.color, role="source")

    for lane, lane_y in zip(spec.lanes, lane_ys, strict=True):
        x0, x1 = axis.x(lane.start), axis.x(lane.end)
        bar = canvas.box(x0, lane_y, x1 - x0, lane_h, lane.label, lane.color, role="lane")
        caption = lane.caption or f"{lane.start} → {lane.end}"
        canvas.text(x0, lane_y + lane_h + 8, caption, color=MUTED)
        mid_y = lane_y + lane_h / 2
        canvas.arrow(source, bar, [(SOURCE_W + 4, mid_y), (x0 - 4, mid_y)], lane.arrow_label, lane.color)
        for hl in lane.highlights:
            hx0, hx1 = axis.x(hl.start), axis.x(hl.end)
            canvas.box(hx0, lane_y - 4, hx1 - hx0, lane_h + 8, None, hl.color, fill="cross-hatch", role="highlight")
            if hl.note:
                note_w, _ = text_size(hl.note)
                canvas.text(min(hx0, axis.right - note_w), lane_y + lane_h + 38, hl.note, color=PALETTE[hl.color][2])

    for i, seg in enumerate(spec.segments):
        _, _, sx, px = axis.spans[i]
        end_x = axis.x(seg.end)
        canvas.line(sx, axis_y, end_x, axis_y)
        if i:
            canvas.text(sx - SEGMENT_GAP / 2 - 8, axis_y - 16, "≈", size=28)
        if seg.label:
            canvas.text(sx, axis_y + 50, seg.label, color=MUTED)
        for tick in seg.ticks:
            tx = axis.x(tick.at)
            canvas.line(tx, axis_y - 8, tx, axis_y + 8)
            tick_label = tick.label or tick.at
            canvas.text(tx - text_size(tick_label)[0] / 2, axis_y + 14, tick_label, color=MUTED)

    for marker in spec.markers:
        mx = axis.x(marker.at)
        _, stroke, ink = PALETTE[marker.color]
        canvas.line(mx, -20, mx, axis_y + 10, stroke=stroke, stroke_style="dashed")
        canvas.text(mx + 8, -20, marker.label, color=ink)


# --- flow

STEP_H_PAD = 30
STEP_W_PAD = 40


def _render_flow(spec: FlowSpec, canvas: _Canvas) -> None:
    order = {step.id: i for i, step in enumerate(spec.steps)}
    labels = [f"{i + 1}. {step.label}" for i, step in enumerate(spec.steps)]
    sizes = [text_size(label) for label in labels]
    step_w = max(w for w, _ in sizes) + STEP_W_PAD
    step_h = max(h for _, h in sizes) + STEP_H_PAD

    adjacent = [e for e in spec.edges if abs(order[e.to] - order[e.from_]) == 1]
    gap = max([text_size(e.label)[0] + 2 * ARROW_PAD for e in adjacent] + [160])
    label_h = max([text_size(e.label)[1] for e in adjacent] + [0])
    top = label_h / 2 + 20

    _header(canvas, spec.title, spec.subtitle, 0)
    boxes = [
        canvas.box(i * (step_w + gap), top, step_w, step_h, label, step.color, role="step")
        for i, (step, label) in enumerate(zip(spec.steps, labels, strict=True))
    ]

    detour_y = top + step_h + 60
    for edge in spec.edges:
        a, b = order[edge.from_], order[edge.to]
        src, dst = boxes[a], boxes[b]
        if abs(a - b) == 1:
            forward = b > a
            y = top + step_h / 2
            sx = src["x"] + step_w + 4 if forward else src["x"] - 4
            dx = dst["x"] - 4 if forward else dst["x"] + step_w + 4
            canvas.arrow(src, dst, [(sx, y), (dx, y)], edge.label)
        else:
            # Skip-level edges route underneath the row so they never cross a box.
            sx, dx = src["x"] + step_w / 2, dst["x"] + step_w / 2
            bottom = top + step_h + 4
            canvas.arrow(src, dst, [(sx, bottom), ((sx + dx) / 2, detour_y), (dx, bottom)], edge.label)
            detour_y += text_size(edge.label)[1] + 30


# --- map

BRANCH_GAP_X = 260
ITEM_GAP = 30


def _render_map(spec: MapSpec, canvas: _Canvas) -> None:
    center_w, center_h = text_size(spec.center, 24)
    center_w, center_h = center_w + 60, center_h + 40

    branches: list[tuple[str, list[str], Color, str]] = [(b.label, b.items, b.color, "branch") for b in spec.branches]
    if spec.not_:
        branches.append(("NOT", spec.not_, "red", "not"))

    def block(label: str, items: list[str]) -> tuple[float, float, float, float]:
        bw, bh = text_size(label)
        iw, ih = text_size("\n".join(f"• {item}" for item in items)) if items else (0.0, 0.0)
        return bw + 40, bh + 24, iw, ih

    sides: list[list[int]] = [[], []]
    for i in range(len(branches)):
        sides[i % 2].append(i)

    _header(canvas, spec.title, spec.subtitle, -200)
    heights = [
        sum(max(block(*branches[i][:2])[1], block(*branches[i][:2])[3]) + 40 for i in side) - 40 for side in sides
    ]
    center = canvas.box(-center_w / 2, -center_h / 2, center_w, center_h, None, "yellow", role="center", stroke_width=3)
    canvas.text(
        -text_size(spec.center, 24)[0] / 2,
        -text_size(spec.center, 24)[1] / 2,
        spec.center,
        24,
        container=center,
        align="center",
    )

    for side_index, side in enumerate(sides):
        direction = 1 if side_index == 0 else -1
        y = -heights[side_index] / 2
        for i in side:
            label, items, color, role = branches[i]
            bw, bh, iw, ih = block(label, items)
            row_h = max(bh, ih)
            bx = center_w / 2 + BRANCH_GAP_X if direction == 1 else -center_w / 2 - BRANCH_GAP_X - bw
            by = y + (row_h - bh) / 2
            style = {"stroke_style": "dashed"} if role == "not" else {}
            branch = canvas.box(bx, by, bw, bh, label, color, role=role, **style)
            start = (center_w / 2 * direction + 4 * direction, 0.0)
            end = (bx - 4 if direction == 1 else bx + bw + 4, by + bh / 2)
            canvas.arrow(center, branch, [start, end], head=False)
            if items:
                text = "\n".join(f"• {item}" for item in items)
                ix = bx + bw + ITEM_GAP if direction == 1 else bx - ITEM_GAP - iw
                canvas.text(ix, y + (row_h - ih) / 2, text, color=PALETTE[color][2])
            y += row_h + 40


def render(spec: TimelineSpec | FlowSpec | MapSpec, seed: int = 7) -> dict[str, Any]:
    canvas = _Canvas(seed)
    if isinstance(spec, TimelineSpec):
        _render_timeline(spec, canvas)
    elif isinstance(spec, FlowSpec):
        _render_flow(spec, canvas)
    else:
        _render_map(spec, canvas)
    return {
        "type": "excalidraw",
        "version": 2,
        "source": "https://github.com/zsviczian/obsidian-excalidraw-plugin",
        "elements": canvas.elements,
        "appState": {"gridSize": None, "viewBackgroundColor": "#ffffff"},
        "files": {},
    }


# --- files

NEW_FILE = """---

excalidraw-plugin: parsed
tags: [excalidraw]

---
==⚠  Switch to EXCALIDRAW VIEW in the MORE OPTIONS menu of this document. ⚠==


# Excalidraw Data

%%
## Drawing
```compressed-json
{payload}
```
%%
"""
_DRAWING_BLOCK = re.compile(r"```(compressed-json|json)\n(.*?)\n```", re.DOTALL)
APPEND_GAP = 300


class DrawingFileError(ValueError):
    pass


@dataclass
class WriteResult:
    mode: Literal["created", "filled", "appended"]
    elements_added: int
    elements_total: int


def _decode(match: re.Match[str]) -> dict[str, Any]:
    kind, payload = match.group(1), match.group(2)
    raw = decompress_from_base64(payload) if kind == "compressed-json" else payload
    return json.loads(raw)


def read_drawing(path: Path) -> dict[str, Any]:
    match = _DRAWING_BLOCK.search(path.read_text(encoding="utf-8"))
    if not match:
        raise DrawingFileError(f"{path} has no Excalidraw drawing block")
    return _decode(match)


def _rename_ids(elements: list[dict[str, Any]], taken: set[str]) -> None:
    mapping: dict[str, str] = {}
    for el in elements:
        new_id = el["id"]
        n = 1
        while new_id in taken:
            new_id = f"{el['id']}_{n}"
            n += 1
        mapping[el["id"]] = new_id
        taken.add(new_id)
    for el in elements:
        el["id"] = mapping[el["id"]]
        el["boundElements"] = [{**b, "id": mapping.get(b["id"], b["id"])} for b in el["boundElements"]]
        if el.get("containerId"):
            el["containerId"] = mapping.get(el["containerId"], el["containerId"])
        for end in ("startBinding", "endBinding"):
            if el.get(end):
                el[end] = {**el[end], "elementId": mapping.get(el[end]["elementId"], el[end]["elementId"])}


def write_drawing(path: Path, doc: dict[str, Any]) -> WriteResult:
    """Create the drawing, fill an empty one, or append below existing content. Never removes elements."""
    new = [dict(el) for el in doc["elements"]]
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = compress_to_base64(json.dumps({**doc, "elements": new}, ensure_ascii=False))
        path.write_text(NEW_FILE.format(payload=payload), encoding="utf-8")
        return WriteResult("created", len(new), len(new))

    text = path.read_text(encoding="utf-8")
    match = _DRAWING_BLOCK.search(text)
    if not match:
        raise DrawingFileError(f"{path} has no Excalidraw drawing block; refusing to modify it")
    existing = _decode(match)
    old = [el for el in existing.get("elements", []) if not el.get("isDeleted")]

    mode: Literal["filled", "appended"] = "filled"
    if old:
        mode = "appended"
        old_bottom = max(el["y"] + el["height"] for el in old)
        old_left = min(el["x"] for el in old)
        new_top = min(el["y"] for el in new)
        new_left = min(el["x"] for el in new)
        for el in new:
            el["x"] += old_left - new_left
            el["y"] += old_bottom + APPEND_GAP - new_top
        _rename_ids(new, {el["id"] for el in existing.get("elements", [])})

    merged = {**existing, "elements": existing.get("elements", []) + new}
    merged.setdefault("files", {})
    payload = compress_to_base64(json.dumps(merged, ensure_ascii=False))
    path.write_text(text[: match.start()] + f"```compressed-json\n{payload}\n```" + text[match.end() :], "utf-8")
    return WriteResult(mode, len(new), len(merged["elements"]))
