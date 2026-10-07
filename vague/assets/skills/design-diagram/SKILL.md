---
name: design-diagram
version: 2.0.0
description: |
  Build a mind map or an architecture overview as a single self-contained HTML page
  (inline SVG, light + dark theme). Reads the real codebase for architecture views,
  or the user's notes/topic for mind maps. Real names and paths in every box.
  Trigger: "mind map", "map this out", "architecture overview", "draw the architecture",
  "diagram this", "visualize the system", "how do these pieces connect".
sdk_commands:
  - vague init
  - vague observations-log
requires_slug: true
requires_planning: false
allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - AskUserQuestion
---

## Preamble

```bash
eval "$(vague context --shell --skill design-diagram)"
VAGUE_HOME="${VAGUE_HOME:-$HOME/.vague}"
DIAGRAM_DIR="$VAGUE_HOME/projects/$SLUG/diagrams"
mkdir -p "$DIAGRAM_DIR"
```

You draw diagrams that explain. A diagram earns its place only if someone who has never
seen the system understands how the pieces combine after one look. Every box holds a real
name. Every arrow says what flows across it.

---

## Step 1: Pick the Diagram Kind

If the request already makes it obvious, skip the question. Otherwise ask via AskUserQuestion:

```
What should I draw?
  A) Mind map — one central idea, branches of related concepts (topic, notes, decision, plan)
  B) Architecture overview — components, the data/calls flowing between them, where state lives
```

| Kind | Shape | Source of truth |
|---|---|---|
| Mind map | Radial tree: root in the center, 3–7 branches, ≤ 3 levels deep | The user's notes, a doc, a design doc in `$VAGUE_HOME/projects/$SLUG/designs/`, or the conversation |
| Architecture overview | Layered boxes-and-arrows: entry points → components → stores/external services | The code itself |

The one distinction: a mind map shows **what relates to what** (no direction, no flow).
An architecture overview shows **what calls or feeds what** (every arrow has a direction and a label).

---

## Step 2: Gather the Real Content

### Mind map
- Use the material the user gave. If they only named a topic, ask for their notes or the doc to map — never invent branches they didn't mention.
- Group into 3–7 first-level branches. If you have more, merge; if a branch has > 6 children, split it.
- Leaf labels are short phrases (≤ 6 words). Detail goes in a tooltip (`<title>`), not the box.

### Architecture overview
Read the code before drawing anything:
```bash
git ls-files | head -200
ls -la
[ -f Taskfile.yml ] && task --list 2>/dev/null
[ -f docs/architecture.md ] && echo "EXISTING_ARCH_DOC: docs/architecture.md"
```
Then read entry points (CLI, `main`, routes, `pyproject.toml` scripts), config, and the modules they import.
Build an inventory before drawing:

| Component | Real path | Talks to | What flows |
|---|---|---|---|
| e.g. CLI | `vague/sdk/cli.py` | installer | install command |

Rules:
- Every box uses a real module, file, service, or directory name. No `Service A`, no `foo`.
- Every arrow carries a verb label: `calls`, `writes to`, `reads`, `symlinks to`, `publishes`.
- Show where state lives (DB, files, `~/.vague/…`) as distinct store shapes.
- Say what does **not** exist if a reader would assume it (e.g. "no server", "no cache").
- Cap at ~15 boxes. If the system is bigger, draw the top level and offer a zoomed-in second diagram.

Confirm the inventory/branch list with the user in one short message before rendering.

---

## Step 3: Render

Produce one self-contained HTML file:

- Inline `<svg>` with a `viewBox` so it scales; no external scripts, fonts, or CDNs.
- Colors as CSS custom properties on `:root`, redefined under `@media (prefers-color-scheme: dark)`; give `body` an explicit background. SVG uses `currentColor` / `var(--…)`, never hardcoded fills.
- Lay out by hand with explicit coordinates — compute positions, don't guess:
  - **Mind map:** root at center; branches evenly spaced by angle (`360 / n`); children fanned within their branch's sector; curved connectors (`<path>` quadratic). One hue per first-level branch, carried to its children.
  - **Architecture:** columns or rows by layer (entry → logic → state/external); straight or orthogonal arrows with `<marker>` arrowheads; label centered on each arrow with a background rect so it stays legible.
- Text must fit its box: size boxes from label length (~7.5px per char at 13px font + 24px padding). No overlapping boxes or labels.
- Below the diagram, for architecture views only, add the inventory table from Step 2 and a single "The one thing to remember" sentence.
- Mobile: the SVG scales to width; the table scrolls inside its own container.

Save and open:
```bash
OUTPUT_FILE="$DIAGRAM_DIR/<kind>-<short-topic>-$(date +%Y%m%d-%H%M%S).html"
open "$OUTPUT_FILE"
```

---

## Step 4: Self-Check

- [ ] Every box holds a real name; no placeholders
- [ ] Every architecture arrow has a direction and a label
- [ ] No overlapping boxes, arrows crossing labels, or clipped text
- [ ] Readable in both light and dark mode
- [ ] Someone new could answer "how do these combine?" from the picture alone

Fix anything that fails, then reopen.

---

## Step 5: Iterate and Offer to Keep

Ask via AskUserQuestion: "Opened in your browser. What should change?" Apply, reopen, repeat until approved.

Once approved, offer:
- Copy into the repo (e.g. `docs/architecture.html`) if it documents this codebase.
- Save to the vault via `/ops-vault` (architecture → `7. Code/`, mind map → `6. Atomic Notes/`), linking the HTML path.

---

## Observation Protocol

Throughout this skill's execution, watch for:
- Steps that produce wrong or suboptimal output
- Missing rules the user has to correct
- Workflow inefficiencies or unnecessary steps
- Gaps where a different skill would help
- **User corrections** — any time the user tells you to do something the skill should have done automatically (e.g. "read the code first", "label the arrows", "use the real module names")

When you notice any of these, log an observation:

```bash
vague observations-log '{"skill":"design-diagram","type":"improvement","issue":"WHAT_HAPPENED","suggestion":"CONCRETE_CHANGE","principle":"GENERALISABLE_TAKEAWAY","source_skill":"design-diagram"}'
```

**User correction detection:** If the user has to explicitly ask you to perform a step that should be part of this skill's workflow, log it immediately as a `type: correction` observation. These are the most valuable signals for skill improvement.

```bash
vague observations-log '{"skill":"design-diagram","type":"correction","issue":"User had to manually ask: WHAT_THEY_SAID","suggestion":"Add this as an explicit step in the skill","principle":"GENERALISABLE_TAKEAWAY","source_skill":"design-diagram"}'
```

Log silently — do not interrupt the user's workflow to announce observations.

---

## Handoff

> "Diagram saved to `$OUTPUT_FILE`. Next: `/ops-vault` to keep it in your notes, or `/plan-eng` if the overview surfaced architecture questions worth locking down."
