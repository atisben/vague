---
name: vault
version: 1.5.0
description: |
  Obsidian vault operations: save notes, export artifacts (HTML diagrams, SVG,
  images) as embedded notes, search, and retrieve content.
  Trigger: "save to vault", "save this note", "note this down", "add to obsidian",
  "export to vault", "send this diagram to obsidian", "search the vault",
  "find in vault", "recall from vault", "/vault save", "/vault export",
  "/vault search", "/vault find".
sdk_commands:
  - vague context
  - vague vault-scan
  - vague memory-log
  - vague memory-search
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
eval "$(vague context --shell --skill vault)"
VAULT="$HOME/Obsidian"
TODAY=$(date +%Y-%m-%d)
echo "VAULT: $VAULT"
echo "TODAY: $TODAY"
echo "FOLDERS (the only valid destinations):"
find "$VAULT" -maxdepth 2 -type d -not -path '*/.*' | sed "s|$VAULT/||" | sort
```

## Vault map

This is the layout at the time of writing. The `FOLDERS` list the preamble prints wins when the two differ.

| Folder | Holds | Written by this skill? |
|---|---|---|
| `1. Rough Notes/` | Daily and scratch notes | no |
| `2. Source Materials/` | Saved links and sources | no |
| `3. Tags/`, `5. Templates/` | Obsidian structure | no |
| `4. indexes/` | Topic hubs that link related notes, written by `/vault-clean` | no |
| `6. Atomic Notes/` | Every finished note | **yes, notes** |
| `6. Atomic Notes/Alma/` | Work notes for Alma, tagged `alma` | **yes, notes** |
| `6. Atomic Notes/Team/` | Management notes: perf reviews from `/mgmt-review` | **yes, notes** |
| `7. Attachments/` | Images, SVG, HTML | **yes, attachments** |
| `8. Excalidraw/` | Drawings the Excalidraw plugin owns | no |
| `9. Archive/` | Retired notes, created and filled by `/vault-clean` only | no |

**Never create a folder.** Do not run `mkdir` under `$VAULT`. Every destination must appear in the `FOLDERS` list. Code walkthroughs, engineering reviews and architecture notes go in `6. Atomic Notes/` with an `architecture` or `review` tag. If no folder fits, use `6. Atomic Notes/` and tell the user.

---

## Detect Subcommand

Parse `$ARGUMENTS` (first word):

| Argument | Mode |
|----------|------|
| `save [title]` | **Save** |
| `export [path]` | **Export** |
| `search <query>` | **Search** |
| `find <title>` | **Find** |
| *(empty)* | **Recent** |

---

## SAVE MODE

### Step 1 — Dedup check

Before creating anything, check for an existing note on the same topic. `vague vault-scan --similar` matches title words loosely (case, accents, word order) and skips `9. Archive/`. The grep catches notes that cover the topic under another title.

```bash
VAULT="$HOME/Obsidian"
QUERY="<inferred title or keyword>"
vague vault-scan --similar "$QUERY"

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

**Caller-specified folder:** if the invoker passed an explicit target folder (see [Saving for another skill](#saving-for-another-skill)), check it against the `FOLDERS` list.

- It exists: use it verbatim and skip the table below. Do the same for caller-supplied tags in Step 3.
- It does not exist: do **not** create it. Ask via AskUserQuestion: A) save to `6. Atomic Notes/`, B) the user names an existing folder.

Otherwise, infer:

| Content type | Folder |
|---|---|
| Work at Alma (scoring, fraud, roadmap, team, backend), tagged `alma` | `$VAULT/6. Atomic Notes/Alma/` |
| Everything else: code walkthroughs, architecture, how-tos, decisions, research, personal, ML concepts | `$VAULT/6. Atomic Notes/` |

Code and architecture notes get the `code` or `architecture` tag, not their own folder. If ambiguous between the two rows, ask.

### Step 3 — Propose tags and kind

Analyze the content and propose 2–5 tags, and the note's kind. The kind tells `/vault-clean` what it may do to the note later:

| Kind | The note is… | `/vault-clean` may… |
|---|---|---|
| `record` | history: a review, an interview, a meeting, a decision record | fix hygiene only, never rewrite it |
| `knowledge` | evergreen: a how-to, a concept, an architecture walkthrough | merge and refresh it |
| `plan` | work to do: an eng plan, a design doc, a critique | archive it once the work ships |

Tags use these conventions:

| Domain | Tags |
|--------|------|
| Work | `alma` (every Alma note), `engineering`, `ml`, `data`, `oncall`, `scoring`, `fraud`, `strategy` |
| ML / AI | `ml_fundamental`, `llm`, `ai`, `model_training` |
| Infrastructure / homelab | `homelab`, `devops`, `proxmox`, `docker` |
| Personal | `personal` |
| Topic overlays | `architecture`, `code`, `how_to`, `review`, `decision`, `debugging`, `research` |

Present proposed tags and confirm/adjust via AskUserQuestion:
```
Proposed tags: engineering, architecture, decision
Kind: plan

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
kind: knowledge
status: active
---
# YYYY-MM-DD - Note Title

<content>

# Next Actions
- [ ]

# References
 -
```

Use the Write tool to create `$FOLDER/$TITLE.md`. The folder must already exist. If Write fails because it does not, stop and re-run Step 2. Never `mkdir` to fix it.

Confirm: "Saved to `$FOLDER/$TITLE.md`." Then [record the write](#record-the-write). This also applies when you update an existing note.

---

## Record the Write

Every note this skill writes gets a `doc` pointer in the memory ledger. The pointer makes the note findable with `vague memory-search --kind doc`, and the usage graph reads it to show which project asked for the file. Telemetry never logs Write or Edit calls, so this step is the only record. After every note, attachment or edit you write, run:

```bash
vague memory-log vault-<title-slug> "<one-line summary of the note>" --doc --files "<absolute path>" --skill vault
```

- `<title-slug>`: the title in lowercase ASCII with hyphens, for example `vault-perf-review-jane-h1-2026`. Re-using the key for an updated note replaces the earlier pointer.
- `<one-line summary>`: what the note is about, in one sentence. Never paste note content.
- `<absolute path>`: the full path of the file you wrote. A path with a comma or a space is fine inside the quotes. Pass `--files` once per file for an attachment.
- Run it from the project the user is working in. That project becomes the note's owner in the graph.
- Tell the user in the same breath: "Logged a doc pointer to the note."
- **Skip this step when another skill called you.** That skill logs its own pointer under its own key (see [Saving for another skill](#saving-for-another-skill)).

---

## Saving for Another Skill

Skills such as `/plan-eng`, `/plan-ideation` and `/diagram` save their documents through this skill. The caller names the destination in the arguments:

```
/vault save "<Title>" folder "<folder>/" tags "<tag1>,<tag2>" kind "<kind>"
/vault export "<source path>" title "<Title>" folder "<folder>/" tags "<tag1>,<tag2>" kind "<kind>"
```

Each argument changes one step of Save mode:

| Argument | Effect | The rule it keeps |
|---|---|---|
| `folder` | Step 2 uses it verbatim | It must appear in the `FOLDERS` list. A missing folder is never created: Step 2 asks the user instead. |
| `tags` | Step 3 uses them without the confirmation question | Tags stay lowercase with underscores |
| `kind` | Step 3 uses it as the note's `kind:` | One of `record`, `knowledge`, `plan`. Without it, Step 3 infers the kind. |
| `title` (or the quoted title after `save`) | Step 4 uses it without the confirmation question | The filename holds no date |
| none of the above | The step runs as usual | n/a |

The dedup check in Step 1 still runs. When the match has the same title, update that note without asking: the caller is saving a newer version of its own document. Skip [Record the Write](#record-the-write). End by printing the absolute path of every file written, so the caller can log its pointer:

```
VAULT_NOTE: <absolute path of the note>
```

---

## EXPORT MODE

Turns a file artifact into a vault note that displays it. For an editable drawing instead of a static artifact, use `/vault-excalidraw`. The artifact goes to `7. Attachments/`; a note in the usual template embeds it with `![[...]]`.

### What Obsidian can display

| Artifact | Embed | Needs |
|---|---|---|
| `.html` (e.g. `/diagram` output) | `![[name.html]]` | the **Embed HTML** community plugin |
| `.svg`, `.png`, `.jpg`, `.gif` | `![[name.svg]]` | nothing, built in |
| Mermaid or Markdown text | none: paste it into the note body with **Save** mode | nothing, built in |
| claude.ai React/JS artifact | cannot run in Obsidian | ask for a static HTML version first, then export that |

### Step 1 — Pick the artifact

If `$ARGUMENTS` gives a path, use it. Otherwise ask the user for the path via AskUserQuestion. A `/diagram` draft lives in `/tmp/vague-diagrams/`:

```bash
ls -t /tmp/vague-diagrams/*.html 2>/dev/null | head -5
```

Stop with an explanation if the file type is not in the table above.

### Step 2 — Check the HTML plugin (HTML only)

```bash
grep -q '"embed-html"' "$VAULT/.obsidian/community-plugins.json" 2>/dev/null && echo "EMBED_HTML: on" || echo "EMBED_HTML: off"
```

If off, tell the user: "Obsidian won't display the HTML inline until you enable the Embed HTML community plugin. I'll still export it; the note will show a link until then."

### Step 3 — Title, folder, tags

Run **Save** Steps 1–4 (dedup check, folder, tags, title). Diagrams follow the same folder table: `6. Atomic Notes/Alma/` for Alma work, else `6. Atomic Notes/`.

### Step 4 — Copy the artifact

Name the attachment after the note title, not the timestamped source name:

```bash
[ -d "$VAULT/7. Attachments" ] || { echo "MISSING: 7. Attachments"; exit 1; }
DEST="$VAULT/7. Attachments/<Title>.<ext>"
[ -e "$DEST" ] && echo "EXISTS: $DEST"
cp "<source path>" "$DEST"
```

If `EXISTS`, ask before overwriting (A: overwrite, B: save as `<Title> 2.<ext>`).

### Step 5 — Write the wrapper note

Obsidian search does not index text inside an embedded file. Write the key facts as plain text too, so the note is findable. Use the Save template with this content:

```markdown
<one-sentence summary of what the artifact shows>

![[<Title>.<ext>]]

<for /diagram architecture views: the "one thing to remember" sentence and the main component names>

Source: `<original absolute path>`
```

Confirm: "Exported to `$FOLDER/$TITLE.md`, artifact in `7. Attachments/<Title>.<ext>`." Then [record the write](#record-the-write) for the note and for the attachment.

Mention once: the HTML diagram picks light/dark from the OS setting, not the Obsidian theme.

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

Log feedback about this skill with `vague memory-log <key> "<issue → suggestion>" --about vault` (see the Memory guideline).
