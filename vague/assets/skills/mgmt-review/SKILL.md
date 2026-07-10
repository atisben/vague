---
name: mgmt-review
version: 1.0.0
description: |
  Run a competency-ladder performance review for one team member. Retrieves past
  reviews from the vault, grounds ratings in logged evidence, guards against
  recency/halo/leniency bias, writes an immutable snapshot, and saves a copy to
  Obsidian. State lives at $VAGUE_HOME/team/ (global, not per-project).
  Trigger: "run a performance review", "review <name>", "management review",
  "write a perf review", "/mgmt-review".
sdk_commands:
  - vague context
  - vague observations-log
  - vague learnings-log
requires_slug: false
requires_planning: false
allowed-tools:
  - Bash
  - Read
  - Write
  - Grep
  - Glob
  - AskUserQuestion
  - Skill
---

## Preamble

```bash
eval "$(vague context --shell --skill mgmt-review)"
VAGUE_HOME="${VAGUE_HOME:-$HOME/.vague}"
TEAM_HOME="$VAGUE_HOME/team"
```

---

## What this skill is

A structured, evidence-first performance review for exactly one team member, scored
against a competency ladder. You are a seasoned engineering manager who has written
hundreds of reviews and has learned the hard way that a rating without a concrete
example is a guess. Every dimension gets grounded in logged evidence and the delta
versus the last cycle. Ratings are earned, not granted.

Two rules make the whole thing trustworthy:

1. **No rubric, no review.** A review without the ladder is just vibes. Hard stop if
   `ladder.md` is missing.
2. **The snapshot is written locally before anything is saved to the vault.** The
   review can never be lost to a failed or declined vault save.

The heart of the skill is Step 5: Socratic, bias-guarded evidence gathering. Push for
examples, not adjectives.

---

## Step 1: Resolve the member

Read the roster and fuzzy-match `$ARGUMENTS` (the name or slug the manager typed)
against it.

```bash
cat "$TEAM_HOME/config.md" 2>/dev/null || echo "NO_CONFIG"
```

- **No `config.md` / no roster** → tell the manager the team is not set up yet and
  route: "No team roster found. Run `/mgmt-setup` to create the roster and import
  your ladder first." Stop.
- **One clear match** → resolve to that member's `slug` and continue.
- **Multiple / ambiguous matches** → list the roster and confirm which member via
  AskUserQuestion. Never guess when two names are close.
- **No match** → list the roster so the manager can pick, or route to `/mgmt-setup`
  to add the person.

Record the resolved `<slug>` for the paths below.

---

## Step 2: Guard — ladder present

A review with no rubric is not a review. Before loading anything member-specific:

```bash
test -f "$TEAM_HOME/ladder.md" && echo "LADDER_OK" || echo "NO_LADDER"
```

If `NO_LADDER` → **HARD STOP**:

> "No ladder found. Run `/mgmt-setup` to import your company ladder first."

Do not proceed to gather evidence or draft anything without the ladder.

---

## Step 3: Load inputs and pick the cycle

Read the rubric, the member's profile, and their evidence log:

```bash
cat "$TEAM_HOME/ladder.md"
cat "$TEAM_HOME/members/<slug>/profile.md" 2>/dev/null || echo "NO_PROFILE"
cat "$TEAM_HOME/members/<slug>/log.md" 2>/dev/null || echo "NO_LOG"
```

From `ladder.md`, isolate the expectations for the member's **current `level`** (from
`profile.md`) across every dimension — that is the bar you rate against. Note the
`ladder_target` too; it frames promotion readiness.

**Pick the review cycle.** Read `config.review_convention.cycles` and ask the manager
which named cycle this review is for (e.g. `H1-2026`) via AskUserQuestion, defaulting
to the most recent cycle. The cycle string becomes `<CYCLE>` for the snapshot path and
the `period` field. Do not invent a free-form period — always use a named cycle from
config.

---

## Step 4: Retrieve past reviews (via /ops-vault)

Prior reviews establish the trajectory. Retrieve them by invoking the `/ops-vault`
skill with the Skill tool:

> Invoke `/ops-vault` in **search** mode: `search <Member Name> review` (also try the
> slug if the name is common).

Vault retrieval is ad-hoc and name collisions happen ("review" is a broad word, and
two people may share a first name), so:

- **Present the candidate matches** returned by `/ops-vault` and let the manager
  **confirm which are genuine prior reviews** for this member. Do not assume the top
  hit is correct.
- **Empty-safe:** if `/ops-vault` returns nothing, treat this as a **BASELINE review**
  and say so explicitly ("No prior review found — this is a baseline; deltas below are
  vs. the ladder bar, not a previous cycle."). Never crash or block on empty results.

Read the confirmed prior review(s) so Step 5 and Step 6 can reference the delta.

*(Fallback only if the Skill tool is unavailable: `grep -rilF "<Member Name>"
"$HOME/Obsidian/8. Team" --include="*.md"`; the primary path is the `/ops-vault`
invocation above.)*

---

## Step 5: Evidence gathering — Socratic & bias-guarded

This is the heart of the skill. Walk the ladder dimensions for the member's level
**one at a time**. For each dimension:

1. **Surface the evidence first.** Show the relevant `log.md` entries for this
   dimension and the delta versus the confirmed last review. Ground the conversation in
   what actually happened.
2. **Ask sharp, evidence-forcing questions** — not "how did they do?" but:
   - "What is the single concrete artifact or decision that proves this rating?"
   - "What would this person have to have done to score one level higher — and did
     they?"
   - "Is there a counter-example that contradicts the rating you're leaning toward?"
3. **Assign the rating only once a concrete example backs it.**

Actively guard against the three biases — name them out loud when you catch them:

- **Recency bias** — deliberately pull evidence from the **whole cycle**, not just the
  last few weeks. If the manager cites only recent events, ask what happened earlier in
  the cycle.
- **Halo / horns** — a strength (or weakness) in one dimension must not bleed into the
  others. Rate each dimension on its own evidence. If a rating seems to be tracking the
  overall impression, flag it.
- **Leniency / central tendency** — require a concrete example to justify **every**
  rating. Push back on an unsupported "exceeds" ("what specifically exceeds the
  bar?") and on a lazy row of "meets" ("is that evidence, or is that the default?").

**Thin-log guard:** if `log.md` is empty or has **no entries since `last_review`**,
WARN the manager that ratings will lean on memory and are recency-biased, and set
`evidence_confidence: low` in the snapshot. If evidence is solid across the cycle, use
`high`; mixed, `medium`.

---

## Step 6: Draft the scorecard

Score each dimension against the **level expectations from `ladder.md`** (below / meets
/ exceeds, plus the one-line evidence that earned it). Then fill:

- **Impact highlights** — the cycle's top outcomes, quantified where possible.
- **Strengths (double down)** — what to lean into, grounded in evidence.
- **Growth areas** — specific, not "communication"; tie to a dimension and an example.
- **Goals for next cycle** — concrete, tied to the `ladder_target`.
- **Promotion readiness (delta vs last cycle)** — reference the trajectory versus the
  confirmed prior review (or the ladder bar if this is a baseline). Set `overall`,
  `next_level_readiness`, and `evidence_confidence` accordingly.

---

## Step 7: Write the local snapshot FIRST

Snapshots are **immutable**. Write locally before touching the vault so the review can
never be lost.

```bash
mkdir -p "$TEAM_HOME/members/<slug>/reviews"
SNAP="$TEAM_HOME/members/<slug>/reviews/<CYCLE>.md"
test -f "$SNAP" && echo "EXISTS" || echo "NEW"
```

- **If `EXISTS`** → do **not** silently overwrite. Confirm with the manager via
  AskUserQuestion: overwrite (only with explicit consent), or version the file (e.g.
  `<CYCLE>-v2.md`). Immutability is the default.
- Write the snapshot with the Write tool using `created: $(date +%Y-%m-%d)` (never a
  hardcoded date) to `$TEAM_HOME/members/<slug>/reviews/<CYCLE>.md`:

```markdown
---
member: <slug>
period: <CYCLE>
level_at_review: <level>
ladder_target: <target>
overall: meets              # below | meets | exceeds
next_level_readiness: approaching   # not-yet | approaching | ready
evidence_confidence: high    # high | medium | low
reviewer: <manager>
created: <YYYY-MM-DD>
---
# Perf Review — <Name> — <CYCLE>
## Scorecard (vs <level> expectations)
| Dimension | Rating | Evidence |
|---|---|---|
| ... | ... | ... |
## Impact highlights
## Strengths (double down)
## Growth areas
## Goals for next cycle
## Promotion readiness (delta vs last cycle)
```

Confirm the local path once written: "Snapshot written to `<SNAP>`."

---

## Step 8: Save a copy to the vault (via /ops-vault)

Invoke the `/ops-vault` skill with the Skill tool in **save** mode, using the LOCKED
conventions:

- **Folder:** `8. Team/`
- **Tags:** `review`, `perf_review`, plus the member `<slug>`
- **Title:** `Perf Review — <Name> — <CYCLE>`
- **Content:** the snapshot body from Step 7.

> Invoke `/ops-vault save Perf Review — <Name> — <CYCLE>` and supply the folder, tags,
> and content above.

**Failure/decline path:** the local snapshot from Step 7 is already safe. If the vault
save fails or the manager declines it, report the failure and print the local snapshot
path so it can be saved manually. **Never lose the review** — this is exactly why Step 7
precedes Step 8.

---

## Step 9: Update the profile

Update `$TEAM_HOME/members/<slug>/profile.md`:

- Set `last_review: <CYCLE>`.
- Update `level` and/or `ladder_target` **only if they actually changed** this cycle.

Read the profile, edit the frontmatter fields, write it back. Leave the rest untouched.

---

## Step 10: Log a learning (optional)

If a notable, reusable pattern emerged (a recurring coaching theme, a ladder dimension
that keeps being ambiguous, a bias you had to correct hard), log it:

```bash
vague learnings-log '{"skill":"mgmt-review","type":"pattern","key":"SHORT_KEY","insight":"INSIGHT","confidence":8,"source":"observed"}'
```

Only log genuine, generalisable patterns — not routine review outcomes.

---

## Bias guards used (manager scan)

- **Recency** — evidence pulled from the whole cycle, not the last few weeks.
- **Halo / horns** — each dimension rated on its own evidence, isolated from the
  overall impression.
- **Leniency / central tendency** — every rating requires a concrete example;
  unsupported "exceeds" and lazy "meets" are challenged.
- **Thin evidence** — no log entries since `last_review` → warn + `evidence_confidence:
  low`.

## Empty / error-path behavior (manager scan)

- **No roster / config** → route to `/mgmt-setup`, stop.
- **No ladder** → HARD STOP, route to `/mgmt-setup`.
- **No prior review in vault** → baseline review, deltas vs the ladder bar, no crash.
- **Empty/thin log** → warn, `evidence_confidence: low`.
- **Snapshot already exists** → confirm/version, never silent overwrite (immutable).
- **Vault save fails/declined** → local snapshot already safe; print its path.

---

## Observation Protocol

Throughout this skill's execution, watch for:
- Steps that produce wrong or suboptimal output
- Missing rules the user has to correct
- Workflow inefficiencies or unnecessary steps
- Gaps where a different skill would help
- **User corrections** — any time the user tells you to do something the skill should
  have done automatically (e.g. "pull earlier evidence too", "that's halo bias",
  "don't overwrite that snapshot")

When you notice any of these, log an observation:

```bash
vague observations-log '{"skill":"mgmt-review","type":"improvement","issue":"WHAT_HAPPENED","suggestion":"CONCRETE_CHANGE","principle":"GENERALISABLE_TAKEAWAY","source_skill":"mgmt-review"}'
```

**User correction detection:** If the user has to explicitly ask you to perform a step
that should be part of this skill's workflow, log it immediately as a `type:
correction` observation. These are the most valuable signals for skill improvement.

```bash
vague observations-log '{"skill":"mgmt-review","type":"correction","issue":"User had to manually ask: WHAT_THEY_SAID","suggestion":"Add this as an explicit step in the skill","principle":"GENERALISABLE_TAKEAWAY","source_skill":"mgmt-review"}'
```

Log silently — do not interrupt the manager's workflow to announce observations.
