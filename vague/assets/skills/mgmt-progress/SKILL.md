---
name: mgmt-progress
version: 1.0.0
description: |
  Read-only team dashboard: rating trends across review cycles, promotion
  readiness, and staleness (who has no recent log or review). Never mutates
  member state. State lives at $VAGUE_HOME/team/ (global, not per-project).
  Trigger: "team progress", "who's ready for promo", "review status",
  "how is my team doing", "/mgmt-progress".
sdk_commands:
  - vague context
  - vague observations-log
requires_slug: false
requires_planning: false
allowed-tools:
  - Bash
  - Read
  - Grep
  - Glob
  - AskUserQuestion
---

## Preamble

```bash
eval "$(vague context --shell --skill mgmt-progress)"
VAGUE_HOME="${VAGUE_HOME:-$HOME/.vague}"
TEAM_HOME="$VAGUE_HOME/team"
```

---

## What this skill is

The analytics dashboard for an engineering manager's team. It reads every piece of
team state the other mgmt-skills have built — the roster, the ladder, per-member
profiles, logs, and review snapshots — and synthesizes a single progress report.
No guessing, no vibes. Trends, readiness, staleness, and concrete next actions.

This skill is **strictly read-only**. It never writes to any member file, profile,
log, or review. It only reports.

You are a data-driven people-manager's analyst. Let the evidence speak. Be honest
about who needs attention without being harsh. Frame everything as "here's exactly
what to do next."

---

## Step 1: Load the roster

Read `$TEAM_HOME/config.md`. From its frontmatter, extract:

- `members[]` — each with `slug`, `name`, `level`, `active`
- `review_convention.cycles[]` — the expected review cadence (e.g. `H1-2026`, `H2-2026`)

```bash
if [ ! -f "$TEAM_HOME/config.md" ]; then
  echo "NO_CONFIG"
fi
```

If `config.md` does not exist, or it lists no `active: true` members, say:

> "No team configured yet. Run `/mgmt-setup` to create the roster before checking progress."

Then exit gracefully — do not generate a report.

Work only with **active** members from here on.

---

## Step 2: Per-member rollup

For each active member `<slug>`, gather their reviews and log. Reviews are optional —
a freshly-added member may have none yet, so every step must be empty-safe.

Glob and read review snapshots (newest last, cycles sort roughly chronologically):

```bash
TODAY=$(date +%Y-%m-%d)
TODAY_S=$(date -j -f %Y-%m-%d "$TODAY" +%s 2>/dev/null || date -d "$TODAY" +%s)

# Iterate members robustly — never `for f in $(...)`; slugs are safe but log
# entries and paths may contain spaces.
find "$TEAM_HOME/members" -mindepth 1 -maxdepth 1 -type d 2>/dev/null \
  | sort \
  | while IFS= read -r member_dir; do
      slug=$(basename "$member_dir")
      echo "=== $slug ==="

      # Review snapshots for this member (empty-safe).
      find "$member_dir/reviews" -name "*.md" 2>/dev/null | sort \
        | while IFS= read -r review; do
            echo "--- review: $(basename "$review") ---"
            sed -n '1,20p' "$review"
          done

      # Latest log activity: newest dated "## YYYY-MM-DD" heading in log.md.
      if [ -f "$member_dir/log.md" ]; then
        grep -Eo '^## [0-9]{4}-[0-9]{2}-[0-9]{2}' "$member_dir/log.md" \
          | sed 's/^## //' | sort | tail -1
      fi
    done
```

For each member compute:

- **Overall trajectory** — the sequence of review-snapshot `overall` values
  (`below` | `meets` | `exceeds`) across cycles, e.g. `meets → exceeds`. If there
  is only one review, show that single value. If there are none, mark `—`.
- **Current readiness** — the `next_level_readiness` (`not-yet` | `approaching` |
  `ready`) from the **newest** review snapshot. If no reviews, take
  `ladder_target` from `profile.md` and mark readiness `—` (no data).
- **Ladder target** — `ladder_target` from `profile.md` (fall back to the newest
  review's `level_at_review` + one level if profile is missing it).
- **Staleness**:
  - *Last log*: days between today and the newest `## YYYY-MM-DD` heading in
    `log.md`. No log file / no dated heading → treat as "never".
  - *Last review*: days between today and the newest review's `created` (or
    `period` end) frontmatter. No reviews → "never".

Compute day-deltas with:

```bash
delta_days() { # $1 = a YYYY-MM-DD date
  local d_s
  d_s=$(date -j -f %Y-%m-%d "$1" +%s 2>/dev/null || date -d "$1" +%s 2>/dev/null) || { echo ""; return; }
  echo $(( (TODAY_S - d_s) / 86400 ))
}
```

**Staleness thresholds** (flag for "Needs attention"):

| Signal | Threshold |
|--------|-----------|
| Stale log | no log entry in > 30 days (or never) |
| Overdue review | no review in > 180 days, or missing the current cycle from `review_convention.cycles[]` (or never) |
| Declining trajectory | latest `overall` is lower than the previous cycle's (e.g. `exceeds → meets`, `meets → below`) |

---

## Step 3: Optional filter from arguments

Parse the first word of `$ARGUMENTS`:

| Argument | Mode |
|----------|------|
| `promo` | Show only members with readiness `approaching` or `ready` |
| `stale` | Show only members flagged stale (stale log or overdue review) |
| *(a member name or slug)* | **Deep view** — full rollup for that one member only |
| *(empty)* | Full team dashboard (all active members) |

For the single-member deep view, match the argument case-insensitively against each
member's `name` and `slug`. If it matches exactly one member, show only that member's
detailed rollup (full trajectory, all cycles, both staleness figures, and the raw
snapshot verdicts). If it matches none, fall back to the full dashboard and note that
the filter did not match. If it matches multiple, list them and ask via
AskUserQuestion which one to open.

---

## Step 4: Present the dashboard

### Team summary table

Always the first section (unless in single-member deep view):

```
| Member    | Level | Target | Latest overall | Readiness    | Last log | Last review |
|-----------|-------|--------|----------------|--------------|----------|-------------|
| Alex Kim  | L4    | L5     | exceeds        | ready        | 4d       | H1-2026 (12d) |
| Sam Ortiz | L3    | L4     | meets          | approaching  | 41d ⚠    | never ⚠     |
| Jo Park   | L5    | L6     | meets ↓        | not-yet      | 8d       | H2-2025 (190d) ⚠ |
```

Use `⚠` to mark values that cross a staleness threshold, and `↓` next to a declining
`overall`. Members with no reviews show `—` for overall/readiness and `never` for
last review.

### Promotion watch

List members whose readiness is `approaching` or `ready`. For each:

- Name, current level → target level, readiness, and overall trajectory.
- One line of evidence from the newest review (e.g. "exceeds two cycles running").
- If `ready`: call it out as a promo candidate to raise in the next calibration.

If none: "No one is currently promo-ready or approaching. Keep building evidence with `/mgmt-log`."

### Needs attention

List members flagged by any Step-2 signal, grouped by reason:

- **Stale logs** — no log activity in > 30 days (or never). Show the day count.
- **Overdue reviews** — no review in > 180 days, missing the current cycle, or never
  reviewed. Show the last cycle (or "never").
- **Declining trajectory** — latest `overall` dropped vs the prior cycle. Show the
  transition (e.g. `exceeds → meets`).

If none: "Nothing needs attention — every active member has a recent log and review, and no trajectories are declining."

---

## Step 5: Next actions

End with a single line of concrete handoffs, e.g.:

> "Run `/mgmt-log <name>` to refresh evidence for stale members, or `/mgmt-review <name>` to start a cycle for anyone overdue. For promo candidates, `/mgmt-review <name>` to formalize the readiness call."

Tailor the line to what the dashboard actually surfaced (only mention stale/overdue/promo
buckets that are non-empty).

---

## Output Schema

The full report follows this structure:

```markdown
## Team Progress Report

### Team Summary
| Member    | Level | Target | Latest overall | Readiness   | Last log | Last review    |
|-----------|-------|--------|----------------|-------------|----------|----------------|
| Alex Kim  | L4    | L5     | exceeds        | ready       | 4d       | H1-2026 (12d)  |
| Sam Ortiz | L3    | L4     | meets          | approaching | 41d ⚠    | never ⚠        |

### Promotion Watch
- **Alex Kim** L4 → L5 — ready. Exceeds two cycles running. Promo candidate for next calibration.
- **Sam Ortiz** L3 → L4 — approaching. Meets consistently; needs one more strong cycle.

### Needs Attention
Stale logs:
- Sam Ortiz — 41 days since last log entry

Overdue reviews:
- Sam Ortiz — never reviewed

Declining trajectory:
- Jo Park — exceeds → meets (H2-2025 → H1-2026)

### Next Actions
Run `/mgmt-log Sam Ortiz` to refresh evidence, then `/mgmt-review Sam Ortiz` to open their first cycle.
```

---

## Observation Protocol

Throughout this skill's execution, watch for:

- Staleness thresholds that feel too strict or too lenient for real teams
- Review-snapshot fields the rollup doesn't capture but managers ask about
- Trajectory patterns the `below/meets/exceeds` model can't express
- Roster or ladder states not covered by the current schema
- Readiness buckets that need finer gradation than not-yet/approaching/ready
- **User corrections** — any time the user tells you to do something the skill should
  have done automatically (e.g. "also flag no-shows", "the current cycle is H2").

When you notice any of these, log an observation silently — do not interrupt the report:

```bash
vague observations-log '{"skill":"mgmt-progress","type":"improvement","issue":"WHAT_HAPPENED","suggestion":"CONCRETE_CHANGE","principle":"GENERALISABLE_TAKEAWAY","source_skill":"mgmt-progress"}'
```

**User correction detection:** If the user has to explicitly ask you to perform a step
that should be part of this skill's workflow, log it immediately as a `type: correction`
observation. These are the most valuable signals for skill improvement.

```bash
vague observations-log '{"skill":"mgmt-progress","type":"correction","issue":"User had to manually ask: WHAT_THEY_SAID","suggestion":"Add this as an explicit step in the skill","principle":"GENERALISABLE_TAKEAWAY","source_skill":"mgmt-progress"}'
```

Log silently — do not interrupt the user's workflow to announce observations.
