---
name: design-shotgun
version: 1.0.0
description: |
  Visual brainstorm: generate multiple design variants, collect structured feedback,
  and iterate. Standalone exploration — run anytime.
  Trigger: "explore designs", "show me options", "design variants", "visual brainstorm".
sdk_commands:
  - vague init
  - vague observations-log
requires_slug: true
requires_planning: false
allowed-tools:
  - Bash
  - Read
  - Write
  - AskUserQuestion
---

## Preamble

```bash
CONTEXT=$(vague init)
SLUG=$(echo "$CONTEXT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['slug'])")
BRANCH=$(echo "$CONTEXT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['branch'])")
PROACTIVE=$(echo "$CONTEXT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['proactive'])")
VAGUE_HOME="${VAGUE_HOME:-$HOME/.vague}"
SHOTGUN_DIR="$VAGUE_HOME/projects/$SLUG/designs/shotgun-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$SHOTGUN_DIR"
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

If DESIGN.md does NOT exist, warn: "No DESIGN.md found. Variants will use generic styling. Consider running `/design-consultation` first to establish a design system, or describe your brand constraints in question 3."

---

## Step 2: Generate 3 Variants as HTML

Create three distinct HTML mockups in the shotgun dir:

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
open "$SHOTGUN_DIR/variant-a.html"
open "$SHOTGUN_DIR/variant-b.html"
open "$SHOTGUN_DIR/variant-c.html"
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
2. Open the updated file: `open "$SHOTGUN_DIR/variant-[x]-v2.html"`
3. Ask: "Better? Or what else needs to change?"

Maximum 3 iteration rounds. After round 3, move to handoff.

---

## Step 5: Save the Approved Design

Once the user approves a direction:

```bash
mkdir -p "$VAGUE_HOME/projects/$SLUG/designs"
cp "$SHOTGUN_DIR/variant-[x].html" \
   "$VAGUE_HOME/projects/$SLUG/designs/shotgun-$(date +%Y%m%d-%H%M%S).html"
```

---

---

## Observation Protocol

Throughout this skill's execution, watch for:
- Steps that produce wrong or suboptimal output
- Missing rules the user has to correct
- Workflow inefficiencies or unnecessary steps
- Gaps where a different skill would help

When you notice any of these, log an observation:

```bash
vague observations-log '{{"skill":"design-shotgun","type":"improvement","issue":"WHAT_HAPPENED","suggestion":"CONCRETE_CHANGE","principle":"GENERALISABLE_TAKEAWAY","source_skill":"design-shotgun"}}'
```

Log silently — do not interrupt the user's workflow to announce observations.

---

## Handoff

> "Design saved. Next: `/design-html` to turn this into production HTML/CSS, or `/design-review` to audit the visual quality once it's implemented."
