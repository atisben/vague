---
name: mgmt-review
version: 2.0.0
description: |
  Run a growth-focused development review for one team member. Centers on what they
  achieved, what didn't land and why, the strengths to double down on, and the blind
  spots (their "hidden zone") to surface — with the company ladder as calibration
  context for where they sit and the gap to the next level, not as a scoring spine.
  Retrieves past reviews from the vault, grounds everything in logged evidence, guards
  against recency/halo/leniency bias, writes an immutable snapshot, and saves a copy to
  Obsidian. State lives at $VAGUE_HOME/team/ (global, not per-project).
  Trigger: "run a performance review", "review <name>", "management review",
  "growth review", "write a review", "/mgmt-review".
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

A **growth-and-development review** for exactly one team member. The job of a review
here is not to grade someone against a static rubric — it is to help them grow: to name
what they achieved, to understand what didn't land and *why*, to point at the strengths
worth doubling down on, and to surface the **blind spots they can't see in themselves**
(their "hidden zone"). You are a seasoned engineering manager whose reviews people leave
feeling *seen* and with a clear picture of how to get better.

The company ladder still matters — but as **calibration context**, not the spine of the
review. You use it to answer "where does this person sit on the IC ladder, and what is
the concrete gap to the next level?" That placement informs the development plan; it is
not the point of the review. A review that is just a row of below/meets/exceeds ratings
has failed, even if every rating is defensible.

Two rules make the whole thing trustworthy:

1. **Development over grading.** Every section is about growth: achievements, misses (with
   root cause, explored with curiosity not blame), strengths, blind spots, and a concrete
   development plan. Ladder placement is one input among these, not the output.
2. **The snapshot is written locally before anything is saved to the vault.** The review
   can never be lost to a failed or declined vault save.

The heart of the skill is Step 5: Socratic, bias-guarded evidence gathering. Push for
examples, not adjectives — for growth areas *and* blind spots as much as for wins.

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

## Step 2: Ladder as calibration context (recommended, not a gate)

The ladder is how you place the member on the company track and quantify the gap to the
next level. It is **strongly recommended** — but its absence does not block a
developmental review, because the core of this review is growth, not scoring.

```bash
test -f "$TEAM_HOME/ladder.md" && echo "LADDER_OK" || echo "NO_LADDER"
```

- **`LADDER_OK`** → load it in Step 3 and use it for ladder placement.
- **`NO_LADDER`** → tell the manager: "No ladder found, so I can't place <Name>
  precisely on the company ladder — placement will be qualitative. You can import it now
  for sharper calibration." Then ask via AskUserQuestion:

  ```
  No career ladder is imported yet.

  A) Import it first (opens /mgmt-setup ladder) — sharper ladder placement
  B) Proceed with a qualitative growth review — I'll note placement is approximate
  ```

  On **A**, route to `/mgmt-setup ladder` and resume afterwards. On **B**, continue and
  set `ladder_placement: approximate` in the snapshot. Never fabricate a ladder.

---

## Step 3: Load inputs and pick the cycle

Read the rubric (if present), the member's profile, and their evidence log:

```bash
cat "$TEAM_HOME/ladder.md" 2>/dev/null || echo "NO_LADDER"
cat "$TEAM_HOME/members/<slug>/profile.md" 2>/dev/null || echo "NO_PROFILE"
cat "$TEAM_HOME/members/<slug>/log.md" 2>/dev/null || echo "NO_LOG"
```

From `profile.md`, pull their **aspirations/goals**, their **standing context** (working
style, constraints), and their recorded **strengths / growth areas** — the review builds
on these, it doesn't restart from zero. From `ladder.md` (if present), isolate the
expectations for the member's **current `level`** and the **next level** (`ladder_target`)
— that pair defines the gap you'll describe in ladder placement.

**Pick the review cycle.** Read `config.review_convention.cycles` and ask the manager
which named cycle this review is for (e.g. `H1-2026`) via AskUserQuestion, defaulting
to the most recent cycle. The cycle string becomes `<CYCLE>` for the snapshot path and
the `period` field. Do not invent a free-form period — always use a named cycle from
config.

---

## Step 4: Retrieve past reviews (via /ops-vault)

Prior reviews establish the trajectory — how the person has *grown*, not just how ratings
moved. Retrieve them by invoking the `/ops-vault` skill with the Skill tool:

> Invoke `/ops-vault` in **search** mode: `search <Member Name> review` (also try the
> slug if the name is common).

Vault retrieval is ad-hoc and name collisions happen ("review" is a broad word, and
two people may share a first name), so:

- **Present the candidate matches** returned by `/ops-vault` and let the manager
  **confirm which are genuine prior reviews** for this member. Do not assume the top
  hit is correct.
- **Empty-safe:** if `/ops-vault` returns nothing, treat this as a **BASELINE review**
  and say so explicitly ("No prior review found — this is a baseline; growth deltas below
  are vs. where they started, not a previous cycle."). Never crash or block on empty results.

Read the confirmed prior review(s). Pay special attention to the **growth areas and
blind spots** the last review named — did they move? Closed growth edges are some of the
strongest evidence in Step 5.

*(Fallback only if the Skill tool is unavailable: `grep -rilF "<Member Name>"
"$HOME/Obsidian/8. Team" --include="*.md"`; the primary path is the `/ops-vault`
invocation above.)*

---

## Step 5: Evidence gathering — Socratic & bias-guarded

This is the heart of the skill. Walk the **growth structure** below **one section at a
time**, grounding every claim in `log.md` evidence and the delta versus the confirmed
last review. This is a conversation, not a form — push for concrete examples the way a
good review conversation does.

Walk these in order:

1. **Achievements & impact.** What did they actually ship or move this cycle? Force
   impact, not activity: "what changed in the business / the team / the product because of
   this?" Quantify where possible.
2. **What didn't land & why.** The misses, blockers, and things that stalled — explored
   with **curiosity, not blame**. The "why" is the whole point: was it scoping, ambiguity,
   prioritization, a skill gap, or something outside their control? Root cause, not verdict.
3. **Strengths to double down.** The one or two things they are genuinely great at.
   Ground each in a concrete example — a strength without an artifact is a compliment,
   not evidence.
4. **Blind spots — the hidden zone.** This is the part only a manager can give. What is
   true about this person's impact or behavior that **they likely can't see in
   themselves** — a pattern others feel but they don't? (e.g. "arrives at scoping already
   holding the solution, which narrows the team's ideation"; "presents raw data and
   expects stakeholders to derive the conclusion".) Name it kindly and specifically, with
   the example that reveals it. This is the highest-value output of the review.
5. **Ladder placement (calibration).** Using `ladder.md`, place them: where do they sit
   at their current level, and what is the **concrete gap** to `ladder_target`? Describe
   it as behaviors, not a score — "the shift from Mid to Senior is from *How* to *Why/What*:
   scoping ambiguous problems and driving business impact." If no ladder, keep this
   qualitative and mark it approximate.

For each section, ask sharp, evidence-forcing questions — not "how did they do?" but:
   - "What is the single concrete artifact or decision that proves this?"
   - "For the miss — what was the actual root cause, and was it within their control?"
   - "For the blind spot — what would they be surprised to hear, and what moment shows it?"
   - "Is there a counter-example that contradicts what you're leaning toward?"

Actively guard against the three biases — name them out loud when you catch them:

- **Recency bias** — deliberately pull evidence from the **whole cycle**, not just the
  last few weeks. If the manager cites only recent events, ask what happened earlier.
- **Halo / horns** — a strength (or weakness) in one area must not colour the rest. A
  brilliant engineer can still have a real blind spot; a struggling one can still have a
  standout strength. Assess each on its own evidence.
- **Leniency / central tendency** — require a concrete example for **every** claim. Push
  back on a vague "doing great" ("great at what, specifically?") and on an empty growth
  area ("that's a platitude — what's the real edge?"). The blind-spot section especially
  must not be skipped because the person is strong.

**Thin-log guard:** if `log.md` is empty or has **no entries since `last_review`**,
WARN the manager that the review will lean on memory and is recency-biased, and set
`evidence_confidence: low` in the snapshot. If evidence is solid across the cycle, use
`high`; mixed, `medium`.

---

## Step 6: Draft the review

Draft the review as a growth document, not a scorecard. Fill:

- **Snapshot** — a short read of the person this cycle: trajectory, headline strength,
  the one growth edge that matters most, and retention/potential if relevant.
- **Achievements & impact** — the cycle's top outcomes, quantified where possible.
- **What didn't land & why** — the misses with their root cause; framed as growth, not
  failure.
- **Strengths (double down)** — what to lean into, each grounded in evidence.
- **Blind spots (the hidden zone)** — the patterns they can't see in themselves, named
  kindly and specifically, each with the moment that reveals it. Do not omit this section.
- **Ladder placement** — where they sit on the company ladder and the concrete,
  behavioral gap to the next level. Include a compact calibration table **only as
  supporting context** (see below), never as the centrepiece.
- **Development plan / growth focus** — 2–3 concrete growth axes for next cycle, each tied
  to their aspirations *and* the ladder gap, with a success signal for each. This is what
  the person should walk away holding.
- **Promotion & retention read** — readiness for the next level (delta vs last cycle) and
  retention risk (short- and long-term), if relevant.
- **Conversation guide** — 2–4 sentences on how to *deliver* this: the framing, the one
  message that must land, and any sensitivity (like a "next-level timing" worry). Reviews
  are only useful if they're heard.

The **calibration table** is optional and compact — a supporting artifact under Ladder
placement, not the spine. When the ladder is present and the manager wants it, summarize
per-dimension standing (below / meets / exceeds vs the current level) with one line of
evidence each. Keep `overall` and `next_level_readiness` as a rollup for `/mgmt-progress`.

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
overall: meets              # below | meets | exceeds — rollup vs level expectations (for /mgmt-progress)
next_level_readiness: approaching   # not-yet | approaching | ready
ladder_placement: at-level  # below-level | at-level | above-level | approximate (if no ladder)
growth_focus: <one-line headline of the top growth edge this cycle>
evidence_confidence: high    # high | medium | low
reviewer: <manager>
created: <YYYY-MM-DD>
---
# Growth Review — <Name> — <CYCLE>

## Snapshot
<short read: trajectory, headline strength, the growth edge that matters most, retention/potential>

## Achievements & impact
<top outcomes, quantified where possible>

## What didn't land & why
<misses + root cause, curiosity not blame>

## Strengths (double down)
<each grounded in a concrete example>

## Blind spots (the hidden zone)
<patterns they can't see in themselves; named kindly + the moment that reveals each>

## Ladder placement
<where they sit at their level; the concrete behavioral gap to <target>>
<!-- optional compact calibration table, supporting context only:
| Dimension | Standing | Evidence |
|---|---|---|
| ... | meets | ... |
-->

## Development plan / growth focus
<2–3 concrete axes for next cycle, each tied to aspirations + the ladder gap, with a success signal>

## Promotion & retention read
<next-level readiness (delta vs last cycle) + retention risk>

## Conversation guide
<how to deliver this: framing, the one message that must land, any sensitivity>
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

(The vault title keeps the `Perf Review — …` convention for continuity with existing
notes and the config `title_format`; the body is the growth review from Step 7.)

**Failure/decline path:** the local snapshot from Step 7 is already safe. If the vault
save fails or the manager declines it, report the failure and print the local snapshot
path so it can be saved manually. **Never lose the review** — this is exactly why Step 7
precedes Step 8.

---

## Step 9: Update the profile

Update `$TEAM_HOME/members/<slug>/profile.md`:

- Set `last_review: <CYCLE>`.
- Refresh the body's **Strengths** and **Growth areas / blind spots** sections from this
  review so the next cycle builds on them (append-merge, don't wipe history).
- Update `level` and/or `ladder_target` **only if they actually changed** this cycle.

Read the profile, edit the fields and sections, write it back. Leave the rest untouched.

---

## Step 10: Log a learning (optional)

If a notable, reusable pattern emerged (a recurring coaching theme, a blind spot that
shows up across the team, a bias you had to correct hard), log it:

```bash
vague learnings-log '{"skill":"mgmt-review","type":"pattern","key":"SHORT_KEY","insight":"INSIGHT","confidence":8,"source":"observed"}'
```

Only log genuine, generalisable patterns — not routine review outcomes.

---

## Bias guards used (manager scan)

- **Recency** — evidence pulled from the whole cycle, not the last few weeks.
- **Halo / horns** — strengths and blind spots assessed on their own evidence; a strong
  performer still gets an honest hidden-zone section.
- **Leniency / central tendency** — every claim requires a concrete example; vague praise
  and empty growth areas are challenged.
- **Thin evidence** — no log entries since `last_review` → warn + `evidence_confidence:
  low`.

## Empty / error-path behavior (manager scan)

- **No roster / config** → route to `/mgmt-setup`, stop.
- **No ladder** → not a hard stop; warn placement is approximate, offer to import, proceed
  on consent with `ladder_placement: approximate`.
- **No prior review in vault** → baseline review, growth deltas vs the starting point, no crash.
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
  "don't skip the blind spots", "don't overwrite that snapshot")

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
