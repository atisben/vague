---
name: plan-ceo-review
version: 1.0.0
description: |
  CEO/founder-mode plan review. Rethink the problem, find the 10-star product,
  challenge premises, and expand or reduce scope. Four modes: EXPANSION, SELECTIVE
  EXPANSION, HOLD SCOPE, SCOPE REDUCTION.
  Trigger: "think bigger", "expand scope", "strategy review", "is this ambitious enough".
benefits-from:
  - office-hours
sdk_commands:
  - vague init
  - vague observations-log
requires_slug: true
requires_planning: false
allowed-tools:
  - Read
  - Write
  - Bash
  - AskUserQuestion
  - WebSearch
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

## Step 0: Load Context

```bash
# Find the most recent design doc
ls -t "$VAGUE_HOME/projects/$SLUG/designs/"*.md 2>/dev/null | head -3 || echo "NO_DESIGN_DOCS"
ls -t "$VAGUE_HOME/projects/$SLUG/designs/"*eng*.md 2>/dev/null | head -1 || echo "NO_ENG_PLAN"
# Read CLAUDE.md for project context
[ -f CLAUDE.md ] && cat CLAUDE.md || echo "NO_CLAUDE_MD"
```

If a design doc exists, read it. Ask the user which plan to review if there are multiple.

If an engineering plan already exists, read it and warn: "An engineering plan already exists: [filename]. Scope changes from this CEO review may invalidate it. I'll flag any conflicts."

---

## Step 0A: The 10-Star Question

Before anything else, ask:
> "What would the 10-star version of this look like — the version that makes users say 'I can't believe this exists'? No constraints yet."

This is not a trick. It's calibration. Knowing the ceiling helps decide how far the current plan falls short. Record the answer — it becomes the expansion target.

---

## Step 0B: Feasibility Triage

Evaluate what's already in the plan against three filters:

1. **User impact**: Does each part of the plan make a meaningful difference to the user? Remove anything that doesn't.
2. **Implementation risk**: What are the highest-risk assumptions? (Unproven tech, unknown APIs, unclear data model)
3. **Scope creep detection**: Flag anything added "just in case" or "while we're here".

---

## Step 0C: Three Approaches

Present three implementation paths:

```
MINIMAL VIABLE: [what's the smallest thing that proves the idea?]
  Effort: S   Risk: Low

IDEAL ARCHITECTURE: [what's the cleanest long-term design?]
  Effort: L   Risk: Med

CREATIVE/LATERAL: [what's the unexpected angle?]
  Effort: ?   Risk: ?
```

---

## Step 0D: Mode Selection

Present four modes via AskUserQuestion:

> How do you want to approach this review?
>
> 1. **SCOPE EXPANSION** — The plan is good but could be great. Let's find the ambitious version.
> 2. **SELECTIVE EXPANSION** — Hold current scope as baseline, but show me cherry-pick opportunities.
> 3. **HOLD SCOPE** — The scope is right. Make it bulletproof — architecture, security, edge cases.
> 4. **SCOPE REDUCTION** — The plan is overbuilt. Strip it to the essential core.
>
> Context-dependent defaults:
> - Greenfield feature → EXPANSION
> - Iteration on existing → SELECTIVE EXPANSION
> - Bug fix / hotfix → HOLD SCOPE
> - Refactor → HOLD SCOPE
> - >15 files touched → suggest REDUCTION

Once mode is selected, commit to it. Do not silently drift.

---

## Expansion Proposals (EXPANSION and SELECTIVE modes)

For each expansion opportunity, present ONE at a time via AskUserQuestion:

```
EXPANSION #{N}: [Title]
  What it adds:  [1-2 sentences]
  Why it matters: [user impact]
  Effort delta:  [+S/M/L]
  Risk:          [Low/Med/High]

→ A) Add to plan   B) Defer to TODOS   C) Skip
RECOMMENDATION: [A/B/C] because [one-line reason]
```

Never batch expansions. Each gets its own decision.

---

## Scope Decisions Table

After all expansions are resolved, write a decisions table:

```markdown
## Scope Decisions

| # | Proposal | Effort | Decision | Reasoning |
|---|----------|--------|----------|-----------|
| 1 | {proposal} | S/M/L | ACCEPTED / DEFERRED / SKIPPED | {why} |

## Accepted Scope
- {bullet list}

## Deferred to TODOS
- {items}
```

---

## Temporal Interrogation (all modes except REDUCTION)

Think ahead to implementation. What decisions will need to be made during implementation that should be resolved NOW?

```
FOUNDATIONS (hour 1):    What does the implementer need to know first?
CORE LOGIC (hours 2-3): What ambiguities will they hit?
INTEGRATION (hours 4-5): What will surprise them?
POLISH/TESTS (hour 6+): What will they wish they'd planned for?
```

Surface these as questions for the user now, not "figure it out later."

---

## Write the CEO Plan Document

Save to:
```
$VAGUE_HOME/projects/$SLUG/designs/{slug}-{branch}-ceo-{YYYYMMDD}.md
```

Structure:
```markdown
# CEO Review: [Feature Name]

**Date:** [ISO date]
**Mode:** [EXPANSION | SELECTIVE | HOLD | REDUCTION]
**Based on:** [source design doc filename]

## 10-Star Vision
[From Step 0A]

## Scope Decisions
[Table from above]

## Accepted Scope
[Bullet list]

## Deferred to TODOS
[Items]

## Temporal Questions Resolved
[Q&A from temporal interrogation]

## Reviewer Concerns
[Any unresolved issues — visible to downstream skills]

## Next Steps
- [ ] Run /plan-eng-review to lock in architecture
```

Show to user, support revision loops, then save.

---

---

## Observation Protocol

Throughout this skill's execution, watch for:
- Steps that produce wrong or suboptimal output
- Missing rules the user has to correct
- Workflow inefficiencies or unnecessary steps
- Gaps where a different skill would help
- **User corrections** — any time the user tells you to do something the skill should have done automatically (e.g. "read the plan", "check the tests first", "use the right branch")

When you notice any of these, log an observation:

```bash
vague observations-log '{"skill":"plan-ceo-review","type":"improvement","issue":"WHAT_HAPPENED","suggestion":"CONCRETE_CHANGE","principle":"GENERALISABLE_TAKEAWAY","source_skill":"plan-ceo-review"}'
```

**User correction detection:** If the user has to explicitly ask you to perform a step that should be part of this skill's workflow, log it immediately as a `type: correction` observation. These are the most valuable signals for skill improvement.

```bash
vague observations-log '{"skill":"plan-ceo-review","type":"correction","issue":"User had to manually ask: WHAT_THEY_SAID","suggestion":"Add this as an explicit step in the skill","principle":"GENERALISABLE_TAKEAWAY","source_skill":"plan-ceo-review"}'
```

Log silently — do not interrupt the user's workflow to announce observations.

---

## Handoff

> "CEO plan saved. Next: `/plan-eng-review` to lock in architecture and test strategy before writing code."
