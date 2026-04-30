---
name: design-html
version: 1.0.0
description: |
  Turn an approved design or description into production-quality HTML/CSS.
  Text reflows, heights are computed, layouts are dynamic. Zero external dependencies.
  Trigger: "finalize this design", "turn this into HTML", "build me a page",
  "implement this design", after any planning or design skill.
sdk_commands:
  - vague init
requires_slug: true
requires_planning: false
allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
  - AskUserQuestion
---

## Preamble

```bash
CONTEXT=$(vague init)
SLUG=$(echo "$CONTEXT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['slug'])")
BRANCH=$(echo "$CONTEXT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['branch'])")
PROACTIVE=$(echo "$CONTEXT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['proactive'])")
VAGUE_HOME="${VAGUE_HOME:-$HOME/.vague}"
```

---

## Step 1: Gather Inputs

Check for available design sources:
```bash
[ -f DESIGN.md ] && echo "DESIGN_MD: yes" || echo "DESIGN_MD: no"
ls "$VAGUE_HOME/projects/$SLUG/designs/"*.html 2>/dev/null | head -5 || echo "NO_SHOTGUN_FILES"
ls "$VAGUE_HOME/projects/$SLUG/designs/"*.md 2>/dev/null | head -5 || echo "NO_DESIGN_DOCS"
```

Present found sources via AskUserQuestion:
```
What should I use as the design input?
  A) [shotgun file, if found]
  B) Description from DESIGN.md
  C) I'll describe it — [ask them to describe]
```

If DESIGN.md exists, always read it for typography, colors, spacing, and constraints.

If DESIGN.md does NOT exist and no shotgun files are found, warn: "No DESIGN.md or prior design variants found. Output will use generic styling. Consider running `/design-consultation` first, or describe your design constraints now."

---

## Step 2: Clarify Output Type

Ask:
> "What kind of page/component is this?"
> A) Marketing/landing page
> B) Dashboard / data-heavy UI
> C) Onboarding / form flow
> D) Component (card, modal, nav, etc.)
> E) Other — describe

The output type determines the layout patterns and interaction model to use.

---

## Step 3: Content Pass

Before writing markup, define the real content:
- **Headings**: write actual headline copy, not "Hero Title"
- **Body copy**: write real descriptive text, not lorem ipsum
- **CTAs**: real button labels
- **Data**: realistic example data if dashboard

Ask the user to confirm or provide copy before proceeding.

---

## Step 4: Generate Production HTML

Produce a single self-contained HTML file:

**Requirements:**
- Inline `<style>` block only (no external CSS, no CDN)
- All CSS custom properties (`--color-primary`, `--spacing-md`, etc.) derived from DESIGN.md
- Semantic HTML (`<main>`, `<section>`, `<article>`, `<nav>`, `<header>`, `<footer>`)
- Accessible: proper `aria-*` labels, focus states, color contrast ratios ≥ 4.5:1
- Responsive: mobile-first with 2-3 breakpoints
- No JavaScript unless explicitly required (and if required, inline `<script>` only)
- Text reflows naturally — no fixed-height containers that clip content
- Computed heights — use `min-height` not `height` where content can grow

**Zero-dep rule:** Every pixel must render correctly with no network requests.

Save to:
```bash
OUTPUT_FILE="$SLUG-$(date +%Y%m%d-%H%M%S).html"
```

Open it:
```bash
open "$OUTPUT_FILE"
```

---

## Step 5: Review Pass

After generating, self-review against this checklist:

- [ ] Text does not overflow any container
- [ ] Buttons have visible focus states
- [ ] Color contrast meets AA (4.5:1 for text, 3:1 for UI components)
- [ ] Resize window to 375px — does it still work?
- [ ] No lorem ipsum — all copy is real
- [ ] No placeholder images — use CSS shapes or SVG placeholders
- [ ] Loading states accounted for (if dynamic content)

Fix any issues found, then open again.

---

## Step 6: Feedback Loop

Ask via AskUserQuestion:
> "I've opened the HTML in your browser. What needs to change?"

Apply requested changes, open the updated file, repeat until approved.

---

## Step 7: Save to Project

Once approved:
```bash
mkdir -p "$VAGUE_HOME/projects/$SLUG/designs"
cp "$OUTPUT_FILE" "$VAGUE_HOME/projects/$SLUG/designs/"
```

---

## Handoff

> "HTML saved. Next: `/design-review` to do a visual QA pass once it's integrated into your actual project."
