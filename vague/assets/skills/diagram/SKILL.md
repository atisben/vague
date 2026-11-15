---
name: diagram
version: 2.0.0
category: Design
summary: Build a mind map or an architecture overview as a self-contained HTML diagram.
description: |
  Build a mind map or an architecture overview as a single self-contained HTML page
  (inline SVG, light + dark theme). Reads the real codebase for architecture views,
  or the user's notes/topic for mind maps. Real names and paths in every box.
  Trigger: "mind map", "map this out", "architecture overview", "draw the architecture",
  "diagram this", "visualize the system", "how do these pieces connect".
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
eval "$(vague context --shell --skill diagram)"
DIAGRAM_DIR="/tmp/vague-diagrams"   # drafts only: the approved diagram moves to the vault in Step 5
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
| Mind map | Radial tree: root in the center, 3–7 branches, ≤ 3 levels deep | The user's notes, a doc, a design doc (`vague memory-search --kind doc` lists the vault paths), or the conversation |
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
| e.g. CLI | `vague/cli.py` | installer | install command |

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

Save the draft and open it:
```bash
OUTPUT_FILE="/tmp/vague-diagrams/<kind>-<short-topic>-$(date +%Y%m%d-%H%M%S).html"
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

Once approved, keep it. The draft in `/tmp/vague-diagrams/` is temporary, so the vault holds the kept copy.

1. Export it through the `/vault` skill (see its "Saving for Another Skill" section). It copies the HTML to `7. Attachments/` and writes a note that embeds it. Use `6. Atomic Notes/Alma/` and add the `alma` tag for Alma work:

   ```
   /vault export "$OUTPUT_FILE" title "<Diagram Title>" folder "6. Atomic Notes/" tags "architecture,code"
   ```

2. Point the ledger at the note. `<name>` is the title in lowercase with hyphens, so a redrawn diagram replaces the older pointer:

   ```bash
   eval "$(vague context --shell --skill diagram)" >/dev/null
   vague memory-log "diagram-<name>" "<one-line summary of what it shows>" --doc --files "<VAULT_NOTE path>" --files "<attachment path>" --skill diagram
   ```

Also offer to copy it into the repo (e.g. `docs/architecture.html`) if it documents this codebase.

---

## Handoff

> "Diagram saved to `$OUTPUT_FILE`. Next: `/vault` to keep it in your notes, or `/plan-eng` if the overview surfaced architecture questions worth locking down."
