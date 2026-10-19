---
name: mgmt-log
version: 1.1.0
description: |
  Minimal between-cycle capture: append a dated 1:1 note, win, concern, strength,
  growth note, or blind spot to a team member's running log. Feeds the growth-focused
  mgmt-review with evidence so reviews aren't memory-based.
  State lives at $VAGUE_HOME/team/ (global, not per-project).
  Trigger: "log a 1:1", "note feedback for <name>", "capture a win",
  "jot down a concern about <name>", "note a blind spot", "/mgmt-log".
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
  - AskUserQuestion
---

## Preamble

```bash
eval "$(vague context --shell --skill mgmt-log)"
VAGUE_HOME="${VAGUE_HOME:-$HOME/.vague}"
TEAM_HOME="$VAGUE_HOME/team"
```

---

## Design principle

This is a **high-frequency, low-ceremony** command. The whole pack's value depends on
capture being frictionless: **one command, one entry, minimal prompting.** Do NOT
interrogate the user. If the note is already in `$ARGUMENTS`, log it and confirm — no
questions. Ask at most once, and only for what's genuinely missing.

---

## Step 1 — Resolve the member

The member is the first token(s) of `$ARGUMENTS`. Fuzzy-match it against the roster.

```bash
CONFIG="$TEAM_HOME/config.md"
if [ ! -f "$CONFIG" ]; then
  echo "NO_ROSTER"
else
  cat "$CONFIG"
fi
```

- **No roster** (`NO_ROSTER` or file missing): tell the user to run `/mgmt-setup` first.
  Optionally offer to add a lightweight stub member and continue — keep it to a single
  yes/no via AskUserQuestion; do not run a setup dialogue here.
- **Roster present**: read the `members[]` entries and fuzzy-match the leading argument
  against each member's `name` or `slug` (case-insensitive, substring or first-name match).
  - **Exactly one match** → use it. Do not confirm.
  - **Multiple matches** → AskUserQuestion listing the candidates; pick one.
  - **No match** → tell the user the name isn't on the roster and suggest `/mgmt-setup`
    (or offer the stub-member path above).

Hold the resolved `<slug>` and display name for later steps.

---

## Step 2 — Parse the note

Everything after the member name in `$ARGUMENTS` is the note text.

- **Note text present** → use it as-is. Do not ask for more.
- **Note text empty** → ask **once** via AskUserQuestion for the note text, and offer the
  type in the same prompt (`1:1` / `win` / `concern` / `strength` / `growth` / `blindspot`).
  Default type: `note`.

Infer the **type** from the wording when obvious:
- "win:", "shipped", "great" → `win`
- "concern", "worried", "hesitant" → `concern`
- "1:1" → `1:1`; "feedback" → `feedback`
- "strength", "really strong at", "double down" → `strength`
- "growth", "needs to work on", "development" → `growth`
- "blind spot", "doesn't see", "unaware", "others feel" → `blindspot`

Fall back to `note`. Never block on type — it is a convenience, not a requirement.
The `strength`, `growth`, and `blindspot` types are what `/mgmt-review` leans on most:
they map straight onto the review's Strengths, Development plan, and Hidden-zone sections,
so capturing them as they happen is the highest-value logging you can do.

If the user tagged competency areas (e.g. "ownership", "leadership", "communication"),
capture them as `dimensions` — useful context for ladder placement. **Never force this**
— omit the line if none were given.

---

## Step 3 — Append the entry

Target file: `$TEAM_HOME/members/<slug>/log.md`.

Create it with the frontmatter header if missing, then append a dated entry. The entry
heading is always `## <today> — <type>`. Use `$(date +%Y-%m-%d)` — never hardcode a date.

```bash
SLUG="<resolved slug>"
NAME="<display name>"
TYPE="<1:1|win|concern|feedback|strength|growth|blindspot|note>"
LOGDIR="$TEAM_HOME/members/$SLUG"
LOG="$LOGDIR/log.md"
mkdir -p "$LOGDIR"

if [ ! -f "$LOG" ]; then
  {
    printf -- '---\n'
    printf 'member: %s\n' "$SLUG"
    printf -- '---\n'
    printf '# Log — %s\n' "$NAME"
  } > "$LOG"
fi

{
  printf '\n## %s — %s\n' "$(date +%Y-%m-%d)" "$TYPE"
} >> "$LOG"
```

Then append the note as four labelled bullets, always in this order. This mirrors the
manager's feedback journal (Context / Observation / Impact / Next steps), so evidence
stays comparable across entries and `/mgmt-review` can separate what happened from
why it mattered and what to do about it.

| Field | What goes in it |
|---|---|
| `context` | The situation: meeting, project, incident, request. |
| `observation` | The concrete behavior seen — facts, not judgement. |
| `impact` | The effect on the team, stakeholders, the project, or the manager. |
| `next` | The follow-up or growth action, if any. |

Split the note text into these fields from its wording. **Never ask the user to fill a
missing field** — write `none` instead. A one-line note becomes `observation`, with
`none` for the rest unless the wording clearly carries context or impact. Keep the user's
facts; do not invent context, impact, or next steps.

Only if the user tagged competencies, add a final `- dimensions: [ownership, leadership]`
line. Use the Write/Bash append tools; keep the `member:` frontmatter and `# Log — <Name>`
header intact when the file already exists (append only — never rewrite the file).

The heading date is always a full `YYYY-MM-DD`: `/mgmt-progress` detects activity by
matching `## YYYY-MM-DD`. If a source only gives a month, use the first of the month
and say so in `context`.

Example resulting entry:

```markdown
## 2026-09-01 — win
- context: Meeting with Risk regarding travel
- observation: Brought strong arguments for using only the cart table; analysis complete, clean, and documented; owned the communication of results
- impact: Made decision-making easier for other teams and steered decisions our way
- next: none
- dimensions: [ownership, communication]
```

---

## Step 4 — Confirm (one line)

Confirm in a single line and stop. Do NOT open a dialogue or ask follow-ups.

```
Logged <type> for <Name> → team/members/<slug>/log.md
```

If nothing else was requested, you are done.

---

## Observation Protocol

Throughout this skill's execution, watch for:
- Steps that produce wrong or suboptimal output
- Missing rules the user has to correct
- Workflow inefficiencies or unnecessary steps (especially: prompting the user when the
  note was already fully specified in the arguments)
- Gaps where a different skill would help
- **User corrections** — any time the user tells you to do something the skill should have
  done automatically (e.g. "just log it", "don't ask", "you had the name already")

When you notice any of these, log an observation:

```bash
vague observations-log '{"skill":"mgmt-log","type":"improvement","issue":"WHAT_HAPPENED","suggestion":"CONCRETE_CHANGE","principle":"GENERALISABLE_TAKEAWAY","source_skill":"mgmt-log"}'
```

**User correction detection:** If the user has to explicitly ask you to perform a step that
should be part of this skill's workflow, log it immediately as a `type: correction`
observation. These are the most valuable signals for skill improvement.

```bash
vague observations-log '{"skill":"mgmt-log","type":"correction","issue":"User had to manually ask: WHAT_THEY_SAID","suggestion":"Add this as an explicit step in the skill","principle":"GENERALISABLE_TAKEAWAY","source_skill":"mgmt-log"}'
```

Log silently — do not interrupt the user's workflow to announce observations.
