---
name: design-review
version: 1.0.0
description: |
  Visual QA: finds spacing issues, hierarchy problems, inconsistencies, and
  AI slop patterns in a live site or component. Fixes them atomically with
  before/after verification. For plan-mode design review, use /plan-eng-review.
  Trigger: "audit the design", "visual QA", "check if it looks good", "design polish".
sdk_commands:
  - vague init
  - vague learnings-log
  - vague observations-log
requires_slug: true
requires_planning: false
allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
  - AskUserQuestion
  - WebSearch
---

## Preamble

```bash
CONTEXT=$(vague init)
SLUG=$(echo "$CONTEXT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['slug'])")
BRANCH=$(echo "$CONTEXT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['branch'])")
PROACTIVE=$(echo "$CONTEXT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['proactive'])")
```

---

## Step 1: Locate the Target

Ask:
> "What should I audit? (URL, file path, or component name)"

Check for DESIGN.md to use as the reference standard:
```bash
[ -f DESIGN.md ] && echo "DESIGN_REFERENCE: found" || echo "DESIGN_REFERENCE: none — will infer style from existing code"
```

If no DESIGN.md, read existing CSS/styles to infer the intended design system before auditing.

---

## Step 2: Run the Audit

Read the target file(s). For each of the following categories, find all issues and list them:

### A. Spacing & Rhythm
- Inconsistent margins/padding (e.g., mixing 13px and 16px)
- Elements that don't align to the spacing scale
- Missing or inconsistent gutters
- Content that feels cramped or too spread out

### B. Typography
- Font sizes outside the defined scale
- Inconsistent font weights for the same role
- Line heights that make text hard to read
- Missing or wrong letter-spacing
- Headings that don't establish clear hierarchy

### C. Color
- Colors that don't match the defined palette (off-by-a-shade)
- Insufficient contrast (< 4.5:1 for text, < 3:1 for UI components)
- Inconsistent use of semantic colors (error/warning/success)
- Hover/focus states that are invisible or jarring

### D. Layout & Alignment
- Elements misaligned on the grid
- Containers with inconsistent max-widths
- Responsive breakpoints that break the layout
- Content that overflows or clips unexpectedly

### E. Interaction States
- Missing hover states
- Missing focus states (accessibility)
- Missing loading/empty/error states
- Animations that feel too fast, too slow, or unnecessary

### F. AI Slop Patterns (common LLM-generated design mistakes)
- Gradient borders on everything
- Drop shadows on every card regardless of hierarchy
- Emojis used as UI elements instead of actual icons
- Centered body text
- Too many font sizes (more than 5)
- "Glassmorphism" applied indiscriminately
- Every section has a different background color

---

## Step 3: Prioritize Issues

Classify each issue:

- **P1 (fix now)**: breaks the layout, accessibility failure, color contrast failure
- **P2 (fix in this session)**: visual inconsistency, obvious polish issue
- **P3 (note for later)**: minor refinement, preference-level

Present a summary table:
```
DESIGN AUDIT RESULTS
──────────────────────────────────────────
P1 (critical):  N issues
P2 (polish):    N issues
P3 (notes):     N issues
──────────────────────────────────────────
[list each issue with category and file:line]
```

---

## Step 4: Fix Loop

Fix P1 and P2 issues atomically — one fix at a time, verifying each before moving to the next.

For each fix:
1. Apply the change to the source file
2. Describe what changed and why: `[FIXED] app/styles/button.css:42 — padding was 13px, aligned to 12px (spacing scale)`
3. Move to the next issue

Do NOT batch fixes. Each is atomic and verifiable.

For P3 issues, list them at the end as "Design notes for later" — no action taken.

---

## Step 5: Log Learnings

If a non-obvious visual pattern was discovered (e.g., "this codebase uses 13px as its base unit"):

```bash
vague learnings-log '{"skill":"design-review","type":"pattern","key":"SHORT_KEY","insight":"INSIGHT","confidence":8,"source":"observed","files":["path/to/file"]}'
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
vague observations-log '{{"skill":"design-review","type":"improvement","issue":"WHAT_HAPPENED","suggestion":"CONCRETE_CHANGE","principle":"GENERALISABLE_TAKEAWAY","source_skill":"design-review"}}'
```

Log silently — do not interrupt the user's workflow to announce observations.

---

## Handoff

> "Design audit complete. [N P1 + N P2 issues fixed, N P3 notes logged]."
> "Next: `/ship` to commit and push these fixes."
