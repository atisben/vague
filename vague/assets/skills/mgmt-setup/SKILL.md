---
name: mgmt-setup
version: 1.0.0
description: |
  Bootstrap and maintain a manager's team state: import a company career ladder,
  define review cycles, and add/edit team members. Foundation for the mgmt-* pack.
  State lives at $VAGUE_HOME/team/ (global, not per-project).
  Trigger: "set up my team", "import career ladder", "add a team member",
  "onboard a report", "/mgmt-setup".
sdk_commands:
  - vague context
  - vague observations-log
requires_slug: false
requires_planning: false
allowed-tools:
  - Bash
  - Read
  - Write
  - Grep
  - Glob
  - AskUserQuestion
---

## Preamble

```bash
eval "$(vague context --shell --skill mgmt-setup)"
VAGUE_HOME="${VAGUE_HOME:-$HOME/.vague}"
TEAM_HOME="$VAGUE_HOME/team"
```

---

## What this skill is

The onboarding session for people management. It creates and maintains the shared
state that the whole `mgmt-*` pack reads from: the company career ladder, your
review cycles, and one folder per direct report. Everything downstream —
`/mgmt-log` (capturing 1:1s and observations) and `/mgmt-review` (running review
cycles) — depends on the state created here.

You are a seasoned engineering manager helping a peer set up. Direct, structured,
warm. Ask only what you need, infer the rest, and never lose the manager's data.

This skill **owns and documents** the `team/` file schema below. It is the
canonical reference for that schema — other `mgmt-*` skills read and append to
these files but do not redefine them.

---

## The `team/` file schema (canonical reference)

All state is global (per-manager, not per-project) and lives under `$TEAM_HOME`:

```
$VAGUE_HOME/team/           (global state root; must NEVER be inside a git repo)
  config.md                 roster + review conventions
  ladder.md                 imported company competency ladder (canonical rubric)
  members/<slug>/
    profile.md              role, level, ladder target, goals
    log.md                  append-only dated stream (maintained by mgmt-log)
    reviews/<CYCLE>.md      immutable review snapshots, CYCLE like "H1-2026" (maintained by mgmt-review)
```

### `config.md`

```markdown
---
manager: <name>
created: <YYYY-MM-DD>
review_convention:
  vault_folder: "8. Team/"
  vault_tags: [review, perf_review]
  title_format: "Perf Review — {name} — {period}"
  cycles: [H1-2026, H2-2026]     # named review cycles the manager runs
members:
  - { slug: jane-doe, name: Jane Doe, level: senior, active: true }
---
# Team
Free-form notes about the team as a whole.
```

### `ladder.md` (imported verbatim then lightly structured)

```markdown
---
source: "<where imported from — path/URL/paste>"
imported: <YYYY-MM-DD>
levels: [junior, mid, senior, staff, principal]
dimensions: [technical, ownership, collaboration, communication, leadership]
---
# Career Ladder
## <dimension> × <level> expectations
<imported text>
```

### `members/<slug>/profile.md`

```markdown
---
name: Jane Doe
slug: jane-doe
role: Backend Engineer
level: senior
ladder_target: staff
start_date: <YYYY-MM-DD>
manager_since: <YYYY-MM-DD>
active: true
last_review:            # empty until first review
---
# Jane Doe
## Career narrative
## Aspirations / goals
## Standing context (working style, constraints)
```

---

## Detect Subcommand

Parse `$ARGUMENTS` (first word):

| Argument | Mode |
|----------|------|
| `ladder` | **Import / replace the career ladder** |
| `member` | **Add or edit a team member** |
| `cycles` | **Define / edit review cycle labels** |
| *(empty)* | **Full guided bootstrap** (manager name → ladder → cycles → first member) |

For the empty case, run every step below in order. For a named subcommand, jump
straight to the matching section, but first run **Step 0** (state + security
checks) — they are always required.

---

## Step 0 — Detect state, guard, and prepare

### 0a. Security guard (do this first — real people's PII)

Team state contains performance data about real people. It must **never** be
committed to a git repository. Check whether `$VAGUE_HOME` resolves inside a git
working tree:

```bash
if git -C "$VAGUE_HOME" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "WARNING: $VAGUE_HOME is inside a git working tree."
  git -C "$VAGUE_HOME" rev-parse --show-toplevel
fi
```

If it prints a warning, **stop and warn loudly**: this state holds direct
reports' performance data and PII, which must not be committed or pushed
anywhere. Use AskUserQuestion to require explicit confirmation before doing
anything else:

```
$VAGUE_HOME is inside a git repository. Team state contains real people's
performance data and PII — it must NOT be committed.

A) Stop — I'll move $VAGUE_HOME out of the repo first
B) I understand the risk and have gitignored it — continue anyway
```

If A, stop and explain how to relocate (`export VAGUE_HOME=~/.vague`). Only
continue on an explicit B.

### 0b. Detect existing state

```bash
if [ -f "$TEAM_HOME/config.md" ]; then
  echo "Existing team state found:"
  sed -n '1,40p' "$TEAM_HOME/config.md"
fi
```

- **If `config.md` exists:** read it, summarize the roster (member names +
  levels) and the current cycles, then ask via AskUserQuestion whether to
  **update** the existing state or **start fresh**.

  ```
  You already have a team set up: <N> members, cycles <...>.

  A) Update — add/edit members, cycles, or the ladder
  B) Start fresh — back up and re-run the full bootstrap
  ```

  If **start fresh**, back up before overwriting anything (mirror iv-kickoff):

  ```bash
  BACKUP="$TEAM_HOME/backup-$(date +%Y-%m-%d)"
  mkdir -p "$BACKUP"
  [ -f "$TEAM_HOME/config.md" ] && cp "$TEAM_HOME/config.md" "$BACKUP/"
  [ -f "$TEAM_HOME/ladder.md" ] && cp "$TEAM_HOME/ladder.md" "$BACKUP/"
  echo "Backed up config.md and ladder.md to $BACKUP"
  ```

  Never delete member folders on "start fresh" — only back up and rewrite
  `config.md` and `ladder.md`. Members are precious; ask explicitly before
  removing any.

- **If `$TEAM_HOME` does not exist:** create it and proceed with the bootstrap.

  ```bash
  mkdir -p "$TEAM_HOME/members"
  ```

---

## Step 1 — Manager identity (bootstrap only)

If `config.md` does not yet exist, ask for the manager's name. This is written to
`config.manager` and used in review titles downstream. Set `created` to
`$(date +%Y-%m-%d)`.

---

## LADDER MODE — import or replace the career ladder

Import the company's competency ladder into `ladder.md`. This becomes the
canonical rubric every review is scored against.

### Step L1 — Collect the source

Ask the manager to provide the ladder as one of:

- a **pasted block** of text (they paste it into the chat), or
- a **file path** (read it with the Read tool), or
- a **URL** (fetch it if tooling allows; otherwise ask them to paste the
  content).

Record where it came from in `ladder.source`.

### Step L2 — Detect tracks

Ladders are often role-family or track-specific. Ask via AskUserQuestion:

```
Does this ladder cover a single track, or separate tracks (e.g. IC vs EM)?

A) Single track
B) Multiple tracks — I'll tell you the track names
```

If **multiple tracks**, add a `tracks` key to the ladder frontmatter listing the
track names (e.g. `tracks: [ic, em]`) and keep each track's expectations under a
clearly-labelled section.

### Step L3 — Confirm levels and dimensions

Read the source and extract the **levels** (e.g. junior → principal) and the
**dimensions** / competency areas (e.g. technical, ownership, collaboration).
Present what you detected and confirm via AskUserQuestion before saving:

```
Detected levels: junior, mid, senior, staff, principal
Detected dimensions: technical, ownership, collaboration, communication, leadership

A) Accept
B) Edit — tell me what to add/remove/rename
```

### Step L4 — Write `ladder.md`

Structure the imported text under the schema above (keep the original wording;
only add structure). Use the Write tool to create `$TEAM_HOME/ladder.md` with the
confirmed `levels`, `dimensions`, optional `tracks`, `source`, and
`imported: $(date +%Y-%m-%d)`.

Confirm: "Career ladder saved to `$TEAM_HOME/ladder.md`."

---

## CYCLES MODE — define review cycle labels

Capture the manager's named review cycles into
`config.review_convention.cycles`.

Ask which cycles they run. Default suggestion: half-yearly, i.e. `H1-YYYY` and
`H2-YYYY` for the current year. Accept any labels the manager prefers
(`Q1-2026`, `2026-Annual`, etc.).

Update the `cycles` list in `config.md`. If `config.md` does not yet exist
(cycles run standalone before bootstrap), create it with sensible defaults for
the other `review_convention` keys shown in the schema.

Confirm the cycles you wrote.

---

## MEMBER MODE — add or edit a team member

### Step M1 — Collect the member's details

Gather, asking only for what you don't already have:

- **Name** (required)
- **Role** (e.g. "Backend Engineer")
- **Level** (must be one of `ladder.levels` — offer the list)
- **ladder_target** (the next level they're growing toward)
- **start_date** and **manager_since** (ISO dates; `manager_since` defaults to
  `$(date +%Y-%m-%d)`)
- **Career goals / aspirations** and any standing context (working style,
  constraints)

### Step M2 — Derive the slug

Kebab-case the name (lowercase, spaces → hyphens, strip punctuation), e.g.
`Jane Doe` → `jane-doe`. Check for a collision against existing member folders:

```bash
ls "$TEAM_HOME/members" 2>/dev/null
```

If the slug already exists and refers to a **different** person, disambiguate
(e.g. `jane-doe-2` or `jane-doe-backend`). If it's the **same** person, this is
an edit — read the existing `profile.md` and merge rather than overwrite.

### Step M3 — Create the member folder

```bash
SLUG="<derived slug>"
mkdir -p "$TEAM_HOME/members/$SLUG/reviews"
touch "$TEAM_HOME/members/$SLUG/log.md"
```

Use the Write tool to create `$TEAM_HOME/members/$SLUG/profile.md` following the
schema above, filling frontmatter from Step M1 and leaving `last_review:` empty.
Populate the body sections (career narrative, aspirations, standing context) from
what the manager told you.

### Step M4 — Update the roster in `config.md`

Read `config.md`, add or update the member's entry under `members:`:

```yaml
  - { slug: <slug>, name: <Name>, level: <level>, active: true }
```

Write `config.md` back. If editing an existing member, update their existing
entry in place rather than appending a duplicate.

Confirm: "Added <Name> (`$TEAM_HOME/members/$SLUG/`) to the roster."

---

## Full bootstrap flow (empty arguments)

Run in order: **Step 0** (guard + prepare) → **Step 1** (manager name) →
**LADDER MODE** (import the ladder) → **CYCLES MODE** (define cycles) →
**MEMBER MODE** (add the first report). Write `config.md` once at the end with
manager, created date, review convention (cycles + defaults), and the roster.

---

## Handoff

After setup, tell the manager what to do next:

> "Team state is set up at `$TEAM_HOME`. From here:
> - `/mgmt-log` — capture 1:1 notes and observations for a report.
> - `/mgmt-review` — run a review cycle against the ladder.
> Add more people any time with `/mgmt-setup member`."

---

## Observation Protocol

Throughout this skill's execution, watch for:
- Steps that produce wrong or suboptimal output
- Missing rules the user has to correct
- Workflow inefficiencies or unnecessary steps
- Gaps where a different skill would help
- **User corrections** — any time the user tells you to do something the skill should have done automatically (e.g. "back up first", "check the ladder levels", "don't commit that")

When you notice any of these, log an observation:

```bash
vague observations-log '{"skill":"mgmt-setup","type":"improvement","issue":"WHAT_HAPPENED","suggestion":"CONCRETE_CHANGE","principle":"GENERALISABLE_TAKEAWAY","source_skill":"mgmt-setup"}'
```

**User correction detection:** If the user has to explicitly ask you to perform a step that should be part of this skill's workflow, log it immediately as a `type: correction` observation. These are the most valuable signals for skill improvement.

```bash
vague observations-log '{"skill":"mgmt-setup","type":"correction","issue":"User had to manually ask: WHAT_THEY_SAID","suggestion":"Add this as an explicit step in the skill","principle":"GENERALISABLE_TAKEAWAY","source_skill":"mgmt-setup"}'
```

Log silently — do not interrupt the user's workflow to announce observations.
