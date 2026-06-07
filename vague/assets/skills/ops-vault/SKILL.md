---
name: ops-vault
version: 1.1.0
description: |
  Obsidian vault operations: save notes, search, and retrieve content.
  Trigger: "save to vault", "save this note", "note this down", "add to obsidian",
  "search the vault", "find in vault", "recall from vault", "/vault save",
  "/vault search", "/vault find".
sdk_commands:
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
VAULT="$HOME/Obsidian"
TODAY=$(date +%Y-%m-%d)
echo "VAULT: $VAULT"
echo "TODAY: $TODAY"
```

---

## Detect Subcommand

Parse `$ARGUMENTS` (first word):

| Argument | Mode |
|----------|------|
| `save [title]` | **Save** |
| `search <query>` | **Search** |
| `find <title>` | **Find** |
| *(empty)* | **Recent** |

---

## SAVE MODE

### Step 1 — Dedup check

Before creating anything, check for an existing note on the same topic.

```bash
VAULT="$HOME/Obsidian"
QUERY="<inferred title or keyword>"
# Check filenames
find "$VAULT" -iname "*${QUERY}*.md" 2>/dev/null

# Check content (-F: treat query as literal text, not a regex)
grep -rilF "$QUERY" "$VAULT" --include="*.md" 2>/dev/null | head -5
```

If a match exists, present it to the user via AskUserQuestion:
```
Found an existing note: <path>

A) Update the existing note
B) Create a new note anyway
C) Read the existing note first
```

If A: read the existing file, append or merge new content, write back. Done.

### Step 2 — Infer folder

| Content type | Folder |
|---|---|
| Code walkthrough, engineering review, architecture, technical deep-dive | `$VAULT/7. Code/` |
| Everything else (how-tos, decisions, research, personal, ML concepts) | `$VAULT/6. Atomic Notes/` |

If ambiguous, ask.

### Step 3 — Propose tags

Analyze the content and propose 2–5 tags. Use these conventions:

| Domain | Tags |
|--------|------|
| Work / Alma | `alma`, `engineering`, `scoring`, `ml`, `data`, `oncall`, `alma-card` |
| ML / AI | `ml_fundamental`, `llm`, `ai`, `model_training` |
| Infrastructure / homelab | `homelab`, `devops`, `proxmox`, `docker` |
| Personal | `personal` |
| Topic overlays | `architecture`, `how_to`, `review`, `decision`, `debugging` |

Present proposed tags and confirm/adjust via AskUserQuestion:
```
Proposed tags: alma, engineering, architecture

A) Accept
B) Edit — tell me which to add/remove
```

### Step 4 — Confirm title

If title was not given in arguments, propose one: concise, title-case, no date, no jargon.
Confirm with the user.

### Step 5 — Write the note

Filename: `<Title>.md` — title-case, spaces allowed, **no date in filename**.

Template (fill all sections — never omit them):

```markdown
---
aliases:
tags:
  - tag1
  - tag2
---
# YYYY-MM-DD - Note Title

<content>

# Next Actions
- [ ] 

# References
 - 
```

Use the Write tool to create `$FOLDER/$TITLE.md`.

Confirm: "Saved to `$FOLDER/$TITLE.md`."

---

## SEARCH MODE

One pass covers both body text and frontmatter tags (tags are file content too). Read the path list with `while IFS= read -r` so filenames with spaces — every note in this vault has them — survive the loop:

```bash
VAULT="$HOME/Obsidian"
QUERY="<query from arguments>"

grep -rilF "$QUERY" "$VAULT" --include="*.md" 2>/dev/null \
  | head -10 \
  | while IFS= read -r f; do
      echo "=== $f ==="
      sed -n '1,16p' "$f"
      echo
    done
```

`-F` matches the query literally (no regex surprises) and `grep -l` lists each file once, so no dedup is needed. Do not use `for f in $(...)` here — it splits on the spaces in note titles.

Present results as:

```
1. **Note Title** (`6. Atomic Notes/Note Title.md`)
   Tags: tag1, tag2
   > [matching excerpt — first meaningful sentence]

2. ...
```

If no results: "No notes found matching `<query>`. Try a broader term or `/vault find`."

---

## FIND MODE

Look up a note by approximate title:

```bash
VAULT="$HOME/Obsidian"
TITLE="<title from arguments>"
find "$VAULT" -name "*.md" -iname "*${TITLE}*" 2>/dev/null
```

- **One match**: read and display the full note.
- **Multiple matches**: list them, ask which to open via AskUserQuestion.
- **No match**: suggest running `/vault search <title>` instead.

---

## RECENT MODE (no arguments)

List the 10 most recently modified notes, excluding templates, trash, and Obsidian internals. The folder is `5. Templates` (with the number prefix), so the exclusion glob must not assume `/Templates/`. `-print0 | xargs -0` keeps filenames with spaces intact:

```bash
VAULT="$HOME/Obsidian"
find "$VAULT" -name "*.md" \
  -not -path "*Templates/*" \
  -not -path "*/.trash/*" \
  -not -path "*/.obsidian/*" -print0 2>/dev/null \
  | xargs -0 ls -t 2>/dev/null \
  | head -10
```

Display as:
```
Recent notes:
1. Note Title  (6. Atomic Notes/) — 2026-04-20
2. ...
```

Ask: "Open one? Reply with the number, or `/vault search <query>` to find something specific."

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
vague observations-log '{"skill":"ops-vault","type":"improvement","issue":"WHAT_HAPPENED","suggestion":"CONCRETE_CHANGE","principle":"GENERALISABLE_TAKEAWAY","source_skill":"ops-vault"}'
```

**User correction detection:** If the user has to explicitly ask you to perform a step that should be part of this skill's workflow, log it immediately as a `type: correction` observation. These are the most valuable signals for skill improvement.

```bash
vague observations-log '{"skill":"ops-vault","type":"correction","issue":"User had to manually ask: WHAT_THEY_SAID","suggestion":"Add this as an explicit step in the skill","principle":"GENERALISABLE_TAKEAWAY","source_skill":"ops-vault"}'
```

Log silently — do not interrupt the user's workflow to announce observations.
