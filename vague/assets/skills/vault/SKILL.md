---
name: vault
version: 1.0.0
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
find "$VAULT" -name "*.md" -iname "*${QUERY}*" 2>/dev/null

# Check content
grep -ril "$QUERY" "$VAULT" --include="*.md" 2>/dev/null | head -5
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

Run two passes — content and tags:

```bash
VAULT="$HOME/Obsidian"
QUERY="<query from arguments>"

# Content search
grep -ril "$QUERY" "$VAULT" --include="*.md" 2>/dev/null | head -10

# Tag-specific search
grep -ril "  - $QUERY" "$VAULT" --include="*.md" 2>/dev/null | head -10
```

For each match, extract title line and tags from frontmatter:

```bash
for f in $MATCHES; do
  echo "=== $f ==="
  head -15 "$f"
  echo ""
done
```

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

List the 10 most recently modified notes, excluding the Templates folder:

```bash
VAULT="$HOME/Obsidian"
find "$VAULT" -name "*.md" -not -path "*/Templates/*" -not -path "*/.obsidian/*" 2>/dev/null \
  | xargs ls -t 2>/dev/null \
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

When you notice any of these, log an observation:

```bash
vague observations-log '{{"skill":"vault","type":"improvement","issue":"WHAT_HAPPENED","suggestion":"CONCRETE_CHANGE","principle":"GENERALISABLE_TAKEAWAY","source_skill":"vault"}}'
```

Log silently — do not interrupt the user's workflow to announce observations.
