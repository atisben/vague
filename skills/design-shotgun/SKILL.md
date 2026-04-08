---
name: design-shotgun
version: 1.0.0
description: |
  Visual brainstorm: generate multiple design variants, collect structured feedback,
  and iterate. Standalone exploration — run anytime.
  Trigger: "explore designs", "show me options", "design variants", "visual brainstorm".
allowed-tools:
  - Bash
  - Read
  - Write
  - AskUserQuestion
---

## Preamble

```bash
export BS_SKILL_NAME="design-shotgun"
source "$(dirname "$0")/../_preamble.sh"
```

---

## Step 1: Brief Gathering

Ask one question at a time:

1. "What are you designing? (e.g., landing page, dashboard, onboarding flow, component)"
2. "What's the core user action on this screen?"
3. "Any constraints? (existing stack, DESIGN.md, branding rules)"

Check for existing design system:
```bash
[ -f DESIGN.md ] && echo "DESIGN_MD_EXISTS" || echo "NO_DESIGN_MD"
```

If DESIGN.md exists, read it and note: "I'll use your existing design system as a constraint."

---

## Step 2: Generate 3 Variants as HTML

Create three distinct HTML mockups in `/tmp/bastack-shotgun/`:

```bash
mkdir -p /tmp/bastack-shotgun
```

Each variant gets its own HTML file (`variant-a.html`, `variant-b.html`, `variant-c.html`).

Each variant must be:
- **Fully self-contained** (inline CSS, no external deps)
- **Realistic** — real copy, not lorem ipsum
- **Distinct** — meaningfully different layouts, hierarchies, or visual approaches
- **Responsive** — works on mobile and desktop

**Variant A: Conservative** — familiar layout, proven patterns, low risk
**Variant B: Modern** — current design trends, higher visual impact
**Variant C: Unexpected** — surprising angle, different mental model of the problem

Write each file with complete HTML, then open them:
```bash
open /tmp/bastack-shotgun/variant-a.html
open /tmp/bastack-shotgun/variant-b.html
open /tmp/bastack-shotgun/variant-c.html
```

---

## Step 3: Structured Feedback

After opening, present via AskUserQuestion:

```
I've opened 3 variants in your browser.

VARIANT A: [Conservative] — [one-line description]
VARIANT B: [Modern] — [one-line description]
VARIANT C: [Unexpected] — [one-line description]

→ A) Use Variant A as the base
   B) Use Variant B as the base
   C) Use Variant C as the base
   D) Mix elements — tell me what you want from each
   E) None of these — show me different directions

RECOMMENDATION: [your pick and why]
```

---

## Step 4: Iteration Loop

If the user picks a direction or requests changes:

1. Apply changes to the chosen variant
2. Open the updated file: `open /tmp/bastack-shotgun/variant-[x]-v2.html`
3. Ask: "Better? Or what else needs to change?"

Maximum 3 iteration rounds. After round 3, move to handoff.

---

## Step 5: Save the Approved Design

Once the user approves a direction:

```bash
eval "$(~/.bastack/bin/bs-slug 2>/dev/null)"
mkdir -p ~/.bastack/projects/$SLUG/designs
cp /tmp/bastack-shotgun/variant-[x].html \
   ~/.bastack/projects/$SLUG/designs/shotgun-$(date +%Y%m%d-%H%M%S).html
```

---

## Handoff

> "Design saved. Next: `/design-html` to turn this into production HTML/CSS, or `/design-review` to audit the visual quality once it's implemented."
