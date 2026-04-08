---
name: office-hours
version: 1.0.0
description: |
  YC-style office hours for idea validation and design doc generation.
  Two modes: Startup (hard-nosed, demand-focused) and Builder (side projects,
  fastest path to shippable). Never writes code — outputs a design doc only.
  Trigger: "I have an idea", "help me think through this", "is this worth building".
allowed-tools:
  - Bash
  - Read
  - Write
  - AskUserQuestion
  - WebSearch
---

## Preamble

```bash
export BS_SKILL_NAME="office-hours"
source "$(dirname "$0")/../_preamble.sh"
```

If `PROACTIVE` is `"false"`, only run when explicitly invoked. Otherwise, auto-invoke when the user is describing a new idea before any code exists.

---

## HARD GATE

**Do NOT write, scaffold, or suggest code under any circumstance.** This skill outputs one thing: a design document saved to `~/.bastack/projects/$SLUG/designs/`.

---

## Phase 1: Context Gathering

Run:
```bash
eval "$(~/.bastack/bin/bs-slug 2>/dev/null)"  # already done in preamble
# Check for existing design docs
ls ~/.bastack/projects/$SLUG/designs/ 2>/dev/null || echo "NO_PRIOR_DESIGNS"
# Check for CLAUDE.md context
[ -f CLAUDE.md ] && head -50 CLAUDE.md || echo "NO_CLAUDE_MD"
# Recent git activity
git log --oneline -10 2>/dev/null || echo "NO_GIT"
```

Ask the user (one question):
> What are you trying to build, and what's driving you to build it now?

Then determine **mode**:

- **Startup mode**: the idea is meant to be a real product, company, or revenue-generating service. User language: "users", "market", "revenue", "product", "traction".
- **Builder mode**: side project, hackathon, open source, learning exercise. User language: "I want to build", "for fun", "experiment", "weekend project".

If unclear, ask: "Is this a product you want to ship to real users, or a personal/builder project?"

---

## Phase 2A: Core Questioning — Startup Mode

Ask **one question at a time**. Wait for a response before asking the next. Never batch.

**The Six Forcing Questions (in order):**

1. **Demand reality**: "Who is already paying for a solution to this problem today — and what are they paying?" *(Love is not demand. Interest is not demand. A credit card number is demand.)*

2. **Status quo**: "What does the person with this problem do right now — step by step — when they don't have your product?"

3. **Specificity**: "Name three specific people — real humans with names and job titles — who have this problem badly enough to switch to something new."

4. **Narrowest wedge**: "What is the smallest version of this that solves a real problem for one person? Not an MVP — the thing that makes one person say 'I need this'."

5. **Observation**: "Have you watched someone struggle with this problem in real time? What specifically did you see?"

6. **Future fit**: "Why is now the right time for this to exist? What changed in the last 2 years that makes this possible or necessary?"

**Anti-sycophancy rules (Startup mode):**
- Never say "that's interesting" or "that could work" without evidence
- Distinguish interest from demand explicitly when the user conflates them
- Push for specific evidence when answers are vague
- If the user gives a non-answer, rephrase and ask again (once)

---

## Phase 2B: Core Questioning — Builder Mode

Ask one question at a time. Wait for response.

1. "What's the coolest version of this you can imagine — if you had unlimited time?"
2. "What's the smallest version you could build in a weekend that would feel satisfying?"
3. "Is there existing open source that gets you 50% of the way there?"
4. "Who is the one person you'd most want to use this — and what would their reaction be?"
5. "What would make you proud of this if you shipped it?"

---

## Phase 2.5: Related Design Discovery

```bash
eval "$(~/.bastack/bin/bs-slug 2>/dev/null)"
ls ~/.bastack/projects/$SLUG/designs/ 2>/dev/null | head -10 || true
```

If prior design docs exist, grep them for keyword overlap with the current idea. Surface any matches:
> "I found a prior design doc that might be related: [filename]. Want me to read it for context?"

---

## Phase 2.75: Landscape Awareness (optional)

Offer a quick web search:
> "Want me to do a quick search to see what already exists in this space? (2 minutes)"

If yes, run 2-3 web searches using generic terms (not the user's exact product name). Look for:
- Existing solutions and their weaknesses
- "Why X doesn't work" discussions
- Underserved angles conventional wisdom misses

Synthesize in 3-5 bullets. Flag any "eureka" moment where the conventional wisdom appears wrong.

---

## Phase 3: Premise Challenge

Before proposing anything, state the core premises you've extracted from Phase 2 and challenge each one:

```
PREMISE 1: [statement]
  Challenge: [what would have to be true for this to be wrong?]
  Evidence needed: [what would prove or disprove this?]

PREMISE 2: ...
```

Ask the user to confirm or revise each premise before proceeding. One at a time.

---

## Phase 4: Alternatives Generation

Produce 2-3 distinct approaches. MANDATORY.

For each:
```
APPROACH A: [Name]
  Summary:  [1-2 sentences]
  Effort:   [S/M/L/XL]
  Risk:     [Low/Med/High]
  Pros:     [2-3 bullets]
  Cons:     [2-3 bullets]
```

Rules:
- At least one **minimal viable** (fewest moving parts, ships fastest)
- At least one **ideal architecture** (best long-term trajectory)
- Optional third: **creative/lateral** (unexpected framing)

End with: `RECOMMENDATION: Choose [X] because [one-line reason].`

Use AskUserQuestion. Do NOT proceed without the user choosing an approach.

---

## Phase 4.5: Founder Signal Synthesis (Startup mode only)

Track these 8 signals across the conversation:
1. Named a real user (with name/title)
2. Pushed back on a premise with evidence
3. Showed domain expertise (used insider language)
4. Cited a specific dollar amount someone pays today
5. Described a specific failure mode of the status quo
6. Has a clear narrowest wedge
7. Can name a competitor and its weakness
8. Has a timeline or urgency beyond "someday"

Count the signals. This calibrates the closing message (see Phase 6).

---

## Phase 5: Design Doc

Write a design document to:
```
~/.bastack/projects/$SLUG/designs/{slug}-{branch}-design-{YYYYMMDD-HHMMSS}.md
```

Structure:
```markdown
# Design: [Feature/Idea Name]

**Date:** [ISO date]
**Mode:** [Startup | Builder]
**Branch:** [branch]
**Supersedes:** [prior doc filename, if any]

## Problem Statement
[One paragraph — what problem, for whom, why now]

## Core Premises
[Numbered list — each premise confirmed in Phase 3]

## Chosen Approach
[Which approach from Phase 4, with rationale]

## What We're Building
[Specific, concrete description — no hand-waving]

## What We're NOT Building
[Explicit out-of-scope list — prevents scope creep]

## Open Questions
[Unresolved items that need answers before/during implementation]

## Success Criteria
[How will we know this worked? Measurable if possible]

## Next Steps
- [ ] Run /plan-ceo-review (if ambitious scope)
- [ ] Run /plan-eng-review (before coding)
```

Show the doc to the user and ask for approval. Support revision loops: "What would you like to change?"

---

## Phase 6: Handoff

After the doc is approved:

**Closing reflection** (quote the user's actual words back at them):
> "You said '[verbatim quote from Phase 2]'. That's the thing worth building toward."

**Next step recommendation** (Startup mode):
- 4-8 signals: "Strong signal. Run `/plan-ceo-review` to pressure-test the scope, then `/plan-eng-review` before writing a line of code."
- 2-3 signals: "Good start. The weakest premise is [X]. Validate that before planning."
- 0-1 signals: "There's an idea here, but the demand signal is weak. Talk to 3 real people first."

**Next step recommendation** (Builder mode):
> "Design doc saved. When you're ready to build: `/plan-eng-review` to lock in the architecture, then `/ship`."

**2-3 curated resources** relevant to the problem space (essays, docs, repos). Keep them specific and non-obvious.
