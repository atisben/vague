---
name: vault-excalidraw
version: 1.0.0
description: |
  Draw an editable Excalidraw diagram straight into the Obsidian vault, with the shape
  picked from the content: a timeline for date windows (training data, schedules,
  validity periods) with filters written on the arrows, a numbered flow for processes,
  a mind map for the parts of one concept. Creates a new drawing or adds to an existing one.
  Trigger: "excalidraw", "draw this in excalidraw", "excalidraw in my vault",
  "add this to my excalidraw", "draw the training windows", "/vault-excalidraw".
sdk_commands:
  - vague context
  - vague excalidraw-render
  - vague excalidraw-inspect
  - vague observations-log
requires_slug: false
requires_planning: false
allowed-tools:
  - Bash
  - Read
  - Write
  - Grep
  - Glob
  - AskUserQuestion
---

## Preamble

```bash
eval "$(vague context --shell --skill vault-excalidraw)"
VAULT="$HOME/Obsidian"
PLUGIN="$VAULT/.obsidian/plugins/obsidian-excalidraw-plugin"
[ -d "$PLUGIN" ] && echo "PLUGIN: on" || echo "PLUGIN: off"
DRAW_DIR=$(python3 -c "import json;print(json.load(open('$PLUGIN/data.json')).get('folder','Excalidraw'))" 2>/dev/null || echo Excalidraw)
echo "DRAW_DIR: $VAULT/$DRAW_DIR"
vague excalidraw-render --help >/dev/null 2>&1 && echo "RENDER: ok" || echo "RENDER: missing"
```

- `PLUGIN: off`: tell the user to enable the **Excalidraw** community plugin, then continue. The file will open once it is on.
- `RENDER: missing`: the installed `vague` predates this skill. Ask the user to reinstall it (`uv tool install --reinstall <path to the vague repo>`) and stop.

You never place coordinates by hand. You write a **spec**: what the diagram says. `vague excalidraw-render` owns layout, arrow bindings and the plugin's compressed file format. You cannot see the result, so every label must be short enough to read without a picture of it.

---

## Step 1: Pick the Shape from the Content

The content decides the shape. Pick without asking when the table makes it obvious.

| The content is… | Shape | `kind` | Example |
|---|---|---|---|
| Date ranges: training windows, backfills, schedules, retention, validity periods | Timeline: one lane per range on a shared date axis, a source box feeding every lane | `timeline` | Bob's two classifier windows and its p-value window |
| Steps that happen in order, data moving between systems | Numbered flow, left to right, a label on every arrow | `flow` | training table → backtest → monitoring |
| The parts of one concept, no direction | Mind map: centre, branches, items per branch, a dashed `NOT` branch | `map` | what pre-commit is and is not |

If two shapes fit, ask once via AskUserQuestion with your recommendation first. Two things that never coexist in time are always a `timeline`.

---

## Step 2: Gather the Real Content

Read the source of truth (code, config, query results, the conversation) before writing the spec. Every box holds a real name.

### For a timeline

1. **Anchor on one concrete day.** Pick a real reference day (today, the incident day, the training day) and compute real dates from it. Put the relative form in the caption: `2025-12-24 → 2026-06-24 (D − 9m25d → D − 3m25d)`.
2. **One lane per range.** Order lanes oldest to newest, top to bottom.
3. **Filters go on the arrows.** For each lane, `arrow_label` is: the filter's real identifier on line 1, then one `• ` bullet per condition in plain words. Put shared conditions in the same words on every lane so the differences stand out.
4. **Zoom when scales differ.** If one range spans months and another spans days, use two `segments`: the old range at `px_per_day` 2, the recent one at 15–25 with a `label` like `zoomed ×10: last month`. A one-day detail must end up at least 20 px wide.
5. **Highlights for what matters.** Mark an anomaly, gap or excluded period inside a lane with a `highlight` (red for problems, grey for "excluded by design") and a one-to-three-line `note`.
6. **Markers for reference moments.** Add a `marker` for the reference day and for any event that explains the picture (a deploy, a schedule run).

### For a flow

Use 2–7 steps. Each step label is a real name (table, job, function). Each edge label says what moves across it (`writes john_p_value`, `HTTP POST /predict`). Edges between non-neighbouring steps are routed underneath automatically.

### For a map

Use 2–7 branches with real names, up to about 5 short items each. Add `not` items whenever a misconception is likely.

### Text rules (all shapes)

- Keep each line under about 55 characters. Split longer lines with `\n`.
- Keep the title under 60 characters. Put the source files and the reference day in `subtitle`.
- Use the colours by meaning: one colour per concept, `red` for problems only, `grey` for "excluded" or "out of scope".

---

## Step 3: Pick the Target File

| The user… | Target |
|---|---|
| Names or links an existing drawing | That file. An `obsidian://open?vault=…&file=…` link maps to `$VAULT/<file, URL-decoded>.md`. |
| Names nothing | A new `$VAULT/$DRAW_DIR/<Title>.excalidraw.md` |

Before writing to an existing file, check what is in it:

```bash
vague excalidraw-inspect "<target path>"
# {"path": "…/credit_scoring_logic.excalidraw.md", "elements": 0}
```

The renderer never removes anything:

- **New file:** created.
- **Empty drawing:** filled; the file header is kept.
- **Drawing with content:** the new diagram is appended **below** the existing content. Say so to the user before writing.
- **Not a drawing:** refused with an error. Nothing is changed.

---

## Step 4: Write the Spec and Render

Write the spec to a scratch file, then render:

```bash
SPEC="${VAGUE_HOME:-$HOME/.vague}/tmp/excalidraw-spec.json"
mkdir -p "$(dirname "$SPEC")"
# Write the spec with the Write tool to $SPEC, then:
vague excalidraw-render "$SPEC" --out "<target path>"
```

Expected output, one JSON line:

```json
{"path": "…/Excalidraw/Bob Training Windows.excalidraw.md", "mode": "created", "elements_added": 44, "elements_total": 44, "embed": "![[Excalidraw/Bob Training Windows.excalidraw]]"}
```

On `Error: …`, fix the spec (the message names the field) and run again. Common causes: a date outside every segment, an edge to an unknown step id, more than 7 lanes, steps or branches.

### Spec reference

Timeline (the shape behind "training data with filters on the arrows"):

```json
{
  "kind": "timeline",
  "title": "Bob (mad_bob) — what data trains it",
  "subtitle": "Example training day D = Mon 2026-10-19 · source: models/bob/config.py + bob/filters.py",
  "source": {"label": "dwh_ml.training\n(BigQuery, rebuilt 03:24 UTC)\n\n+ john_p_value from\njohn_backtest_outputs", "color": "blue"},
  "segments": [
    {"start": "2025-09-01", "end": "2026-07-01", "px_per_day": 2,
     "ticks": [{"at": "2025-12-01", "label": "2025-12"}, {"at": "2026-03-01", "label": "2026-03"}]},
    {"start": "2026-09-14", "end": "2026-10-21", "px_per_day": 20, "label": "zoomed ×10: last month",
     "ticks": [{"at": "2026-10-16", "label": "Fri 10-16"}]}
  ],
  "lanes": [
    {"label": "Credit classifier · 8 months · target: recovery", "start": "2025-09-19", "end": "2026-05-19",
     "color": "purple", "caption": "2025-09-19 → 2026-05-19   (D − 13m → D − 5m)",
     "arrow_label": "credit_fr_no_forced_recovery_ob_scored_filter\n• FR transaction + FR bank account\n• credit: > 4 installments\n• open banking verified"},
    {"label": "P-value reference · last 1 month", "start": "2026-09-18", "end": "2026-10-18", "color": "yellow",
     "arrow_label": "rejection_scope_openbanking_john_p_value_not_null\n• FR transaction + FR bank account\n• john_p_value NOT NULL",
     "highlights": [{"start": "2026-10-16T16:30", "end": "2026-10-18", "color": "red",
                     "note": "Mondays: Fri 16:30 → Sat john_p_value = NULL\n→ dropped by the NOT NULL filter"}]}
  ],
  "markers": [{"at": "2026-10-19", "label": "D = training day\nMon 2026-10-19", "color": "red"}]
}
```

Dates are `YYYY-MM-DD` or `YYYY-MM-DDTHH:MM`. Every lane, highlight, tick and marker date must fall inside a segment. `caption` defaults to `start → end`.

Flow:

```json
{"kind": "flow", "title": "Nightly scoring", "subtitle": "UTC times",
 "steps": [{"id": "train", "label": "dwh_ml.training\n03:24"}, {"id": "bt", "label": "john_backtest\n07:30 Mon–Sat"}],
 "edges": [{"from": "train", "to": "bt", "label": "reads payments"}]}
```

Map:

```json
{"kind": "map", "title": "pre-commit", "center": "pre-commit",
 "branches": [{"label": "config", "items": [".pre-commit-config.yaml at the repo root"]},
              {"label": "when", "items": ["every git commit, after pre-commit install"]}],
 "not": ["does not run on push or in CI by itself"]}
```

Colours: `blue`, `purple`, `green`, `yellow`, `orange`, `red`, `grey`.

---

## Step 5: Wrap It in a Note (Optional)

If the user asked for a note, or the drawing is new and stands alone, offer a wrapper note in `6. Atomic Notes/` using the `/vault` save template. Put the `embed` value from Step 4 at the top, then the key facts as plain text, because Obsidian search does not index text inside drawings.

Skip this when the user targeted an existing drawing: it already lives where they want it.

---

## Step 6: Report

Tell the user, in this order:

1. The path and the mode (`created`, `filled` or `appended below existing content`).
2. A small ASCII sketch of the layout, so they know what to look for.
3. That you cannot see the rendering: ask them to open it and say which labels overflow or overlap.

When they ask for adjustments, change the spec and re-render into a **new** file or tell them the old version will stay above the new one. The renderer appends; it does not edit in place.

---

## Observation Protocol

Throughout this skill's execution, watch for:
- Steps that produce wrong or suboptimal output
- Missing rules the user has to correct
- Workflow inefficiencies or unnecessary steps
- Gaps where a different skill would help
- **User corrections** — any time the user tells you to do something the skill should have done automatically (e.g. "put the filters on the arrows", "use the existing drawing")

When you notice any of these, log an observation:

```bash
vague observations-log '{"skill":"vault-excalidraw","type":"improvement","issue":"WHAT_HAPPENED","suggestion":"CONCRETE_CHANGE","principle":"GENERALISABLE_TAKEAWAY","source_skill":"vault-excalidraw"}'
```

**User correction detection:** If the user has to explicitly ask you to perform a step that should be part of this skill's workflow, log it immediately as a `type: correction` observation. These are the most valuable signals for skill improvement. Layout complaints ("labels overlap", "too wide") are corrections too: they mean the renderer's layout rules need work.

```bash
vague observations-log '{"skill":"vault-excalidraw","type":"correction","issue":"User had to manually ask: WHAT_THEY_SAID","suggestion":"Add this as an explicit step in the skill","principle":"GENERALISABLE_TAKEAWAY","source_skill":"vault-excalidraw"}'
```

Log silently — do not interrupt the user's workflow to announce observations.

---

## Handoff

> "Drawing written to `<path>` (`<mode>`). Open it and tell me which labels need moving. Next: `/vault save` to wrap it in a note, or `/diagram` for a non-editable HTML version."
