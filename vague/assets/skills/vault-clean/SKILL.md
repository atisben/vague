---
name: vault-clean
version: 1.0.0
category: Reflection
summary: "Keep the vault current: fix frontmatter, distill shipped plans into decisions, merge duplicates, build topic hubs, archive before deleting."
description: |
  Maintain the Obsidian vault so search returns the current truth. Scans every note
  with `vague vault-scan`, fixes frontmatter hygiene on its own, then asks before it
  distills shipped plans into decisions, merges duplicate knowledge notes, builds topic
  hubs and checks stale notes. Retired notes go to `9. Archive/`; only archived notes
  past their grace period are ever deleted, and only with approval. Writes a cleaning
  report to the vault.
  Trigger: "clean the vault", "vault cleaning", "tidy my vault", "dedupe the vault",
  "the vault is a mess", "distill the vault", "/vault-clean".
allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
  - Grep
  - Glob
  - AskUserQuestion
---

## Preamble

```bash
eval "$(vague context --shell --skill vault-clean)"
VAULT="${VAGUE_VAULT:-$HOME/Obsidian}"
TODAY=$(date +%Y-%m-%d)
echo "VAULT: $VAULT"
echo "TODAY: $TODAY"
[ -d "$VAULT/9. Archive" ] && echo "ARCHIVE: present" || echo "ARCHIVE: missing"
vague memory-search --kind doc --skill vault-clean | head -3
```

The last line shows earlier cleaning reports. Read the newest one: its **Backlog** section is where this run starts.

## The Goal

A vault is worth something only when a search returns the current truth, not a stale plan beside it. This skill optimises retrieval quality, not note count. Deleting notes is the last resort.

```
 ┌────────────┐   ┌────────────┐   ┌────────────┐   ┌────────────┐   ┌────────────┐   ┌────────────┐
 │ 1. Scan    │──▶│ 2. Hygiene │──▶│ 3. Classify│──▶│ 4. Distill │──▶│ 5. Archive │──▶│ 6. Report  │
 │ vault-scan │   │ automatic  │   │ confirm    │   │ plans,     │   │ expired?   │   │ vault note │
 │ inventory  │   │ frontmatter│   │ kinds once │   │ merges,    │   │ ask before │   │ + backlog  │
 │            │   │ + sections │   │            │   │ hubs, stale│   │ delete     │   │            │
 └────────────┘   └────────────┘   └────────────┘   └────────────┘   └────────────┘   └────────────┘
```

## The Three Kinds of Note

Every note has one kind, stored as `kind:` in its frontmatter. The kind decides what this skill may do to it:

| Kind | What it is | Examples | Allowed actions |
|---|---|---|---|
| `record` | History: what happened or what was decided at a moment | perf review, interview notes, 1:1, coaching session, decision record | Hygiene fixes, links. **Never rewrite or merge the body.** |
| `knowledge` | Evergreen: how something works or how to do it | how-to, ML concept, homelab setup, architecture walkthrough | Merge duplicates, refresh, link into a hub |
| `plan` | Work to do; it expires when the work ships | eng plan, design doc, design critique, roadmap | Distill its decisions, then archive |

## The Retirement Order

Every retirement follows this order of preference. Never skip a step because a later one is easier:

1. **Factorize.** Merge the content into the canonical note, or distill the decisions out of a plan. The knowledge survives in a live note.
2. **Archive.** Move the emptied original to `9. Archive/`. Links to it are rewritten first.
3. **Delete.** Only an archived note past its grace period (90 days), only after the user approves it, only into Obsidian's `.trash/`.

The archive is a guardrail before deletion, not a parking lot. A note never goes to the archive with knowledge that lives nowhere else.

## Run Budget

One run handles at most **5 clusters, 5 plans, 3 hub proposals and 5 stale checks**. Everything else goes to the report's Backlog section. A bounded run finishes. An unbounded run fills the context and leaves the vault half-edited.

---

## Step 1: Scan

```bash
vague vault-scan
```

The scan measures and never edits. Its sections are:

| Section | What it lists |
|---|---|
| Header | Note count by kind, orphans (notes no other note links to), notes an agent wrote |
| `HYGIENE` | Per note: `no-frontmatter`, `bad-frontmatter`, `no-tags`, `bad-tag: <tag>`, `missing-sections` |
| `CLUSTERS` | Groups of likely duplicates: near-identical titles, or bodies with high word overlap |
| `PLANS` | Every plan with its `status`, age in days (from the H1 date) and whether an agent wrote it |
| `GUESSED KINDS` | Notes with no `kind:` in frontmatter, grouped by the kind the scanner guessed |
| `EXPIRED` | Archived notes past the grace period |

Use `vague vault-scan --json` when you need one note's full record, such as its tags or inbound link count.

## Step 2: Hygiene (automatic)

Fix these without asking, in `6. Atomic Notes/` only. `1. Rough Notes/` and `2. Source Materials/` are the user's scratch space: report their issues, never edit them.

| Issue | Fix |
|---|---|
| `no-frontmatter` | Add the vault template frontmatter: `aliases: []`, inferred `tags`, `kind`, `status: active` |
| `bad-frontmatter` | Read the file, repair the YAML by hand, keep every value |
| `no-tags` | Infer 2–5 tags from the content, with the tag conventions of the `/vault` skill |
| `bad-tag: <tag>` | A template prompt saved as a tag (`Problem and solution statement`): remove it. A tag with capitals or spaces: rewrite it lowercase with underscores (`Alma` → `alma`). |
| `missing-sections` | Append `# Next Actions` with `- [ ]` and `# References` with ` -`, the vault template sections |

Rules for every hygiene edit:

- Edit only the frontmatter and the two template sections. Never touch the body.
- Use the Edit tool, one note at a time. Never rewrite a note with a shell loop.
- Count the fixes per issue type. The report lists the counts, not every file.

## Step 3: Classify (one confirmation)

A guessed kind is only a guess. Confirm the guesses that change what the skill may do, in one question:

1. Show the `record` and `plan` lists from `GUESSED KINDS`, one title per line.
2. Ask with AskUserQuestion: *"These notes look like records (never rewritten) and plans (archived once shipped). Which are wrong?"* Options: A) all correct, B) I'll name the wrong ones.
3. Every note not named is accepted. `knowledge` is the default and needs no confirmation.
4. Write `kind: <kind>` into the frontmatter of every note you classified, records and plans included. The next scan then reads the kind instead of guessing.

## Step 4: Distill

Work through the four sub-steps in order. Each one stops at its budget line from [Run Budget](#run-budget).

### 4a. Plans

Take plans with `status` unset or `active`, oldest first. For each plan:

1. **Find evidence.** For a plan about a repo, search the repo for the plan's key names (functions, commands, files) and its git log. Say what you found: "`vague skill-check` exists and the hook is in `.pre-commit-config.yaml`: the plan shipped."
2. **Ask** with AskUserQuestion: A) shipped, B) still in progress, C) abandoned. Put your evidence in the question.
3. **Act** on the answer:

| Answer | Action |
|---|---|
| Shipped | Distill, then archive (see below) |
| In progress | Set `status: active`. Leave the note in place. |
| Abandoned | Write one line to the matching decision note: what was dropped and why. Then archive the plan with `archived_reason: abandoned`. |

**Distilling a shipped plan.** The task lists and step-by-step build details go. The *decisions and their reasons* stay:

1. List each decision in the plan as one line: what was chosen, what was rejected, why.
2. Find a home with `vague vault-scan --similar "<topic>"`: the knowledge note on the same system. When none exists, create `Decisions - <System>.md` with `kind: record` and the vault template.
3. Append the decisions under a dated heading, `## YYYY-MM-DD - <Plan title>`, and link the archived plan in References.
4. Show the distilled lines to the user before you write them.
5. Archive the plan (see [Archiving a Note](#archiving-a-note)).

### 4b. Clusters

For each cluster, read every note in it fully. Then propose one action by kind:

| Cluster holds | Proposal |
|---|---|
| Only `knowledge` notes on the same subject | **Merge.** The canonical note is the one with the most inbound links. Fold every unique fact from the others into it, then archive them with `merged_into`. |
| `record` notes | **Never merge.** Propose links between them in References. Archive one only when the user says it is a superseded draft (for example a review and its `(Lattice)` copy). |
| A `plan` and a `knowledge` note | Handle the plan in [4a. Plans](#4a-plans). It distills into the knowledge note. |
| A false positive (same template, different subject) | Skip it, and log it in the report so the next run skips it too |

Ask before every merge with AskUserQuestion. Show the canonical title, the notes to fold in, and the facts that only the folded notes hold. A merge that drops a unique fact is a bug.

### 4c. Hubs

The scanner finds duplicates, not related notes. Notes that share a topic but not words (`How to use datadog`, `Interview Datadog`) need a hub, not a merge.

1. Group the `knowledge` notes by their most specific tag. Skip groups under 4 notes.
2. Read the titles of each group and the first lines of each orphan in it.
3. Propose at most 3 hubs, each with the notes it links and a one-line reason.
4. On approval, write the hub to `4. indexes/<Topic>.md` with the vault template, `kind: knowledge`, the tag `index`, and one bullet per note: `- [[Note Title]]: <what the note answers>`.

A hub links notes. It never copies their content.

### 4d. Stale knowledge

Pick up to 5 `knowledge` notes over 180 days old, most inbound links first. A heavily linked stale note does the most damage.

| The note is about | How to check it |
|---|---|
| Code in a local repo | Check that the paths, commands and functions it names still exist. Report each missing name. |
| Anything else (homelab, ML concept, process) | Ask the user: *"`<title>` was written on `<date>`. Is it still true?"* A) yes, B) partly: I'll say what changed, C) no longer true. |

Update a note that is partly stale, and add a line under References: `Checked by /vault-clean on YYYY-MM-DD`. Archive a note that is no longer true only after you have moved anything still true into a live note.

## Archiving a Note

Archiving is one procedure. Run it the same way for merges, plans and stale notes:

1. **Create the folder once.** When the preamble printed `ARCHIVE: missing`, ask the user once, then run `mkdir "$VAULT/9. Archive"`. This skill is the only one allowed to create it.
2. **Rewrite inbound links.** Grep live notes for `[[<Old Title>`. Point each link at the canonical note, keeping the visible text: `[[Old Title]]` becomes `[[Canonical|Old Title]]`. Obsidian resolves links by file name anywhere in the vault, so an unrewritten link would lead into the archive.
3. **Mark it.** Add to the frontmatter: `status: archived`, `archived: <TODAY>`, `archived_reason: merged | shipped | abandoned | stale | superseded`, and `merged_into: "[[Canonical]]"` when there is one.
4. **Move it.** `mv "$VAULT/<path>" "$VAULT/9. Archive/"`. On a name clash, append ` (2)` to the file name.
5. **Add the old title** to the canonical note's `aliases`, so a search for the old title still finds the live note.

## Step 5: Expired Archive

List the `EXPIRED` section. When it is empty, skip this step. Otherwise ask once with AskUserQuestion, showing each title and its `archived_reason`: A) delete all, B) delete some: I'll name them, C) keep all for another grace period.

To delete, move the file into Obsidian's trash, never `rm`:

```bash
mkdir -p "$VAULT/.trash" && mv "$VAULT/9. Archive/<file>" "$VAULT/.trash/"
```

To keep a note for another grace period, set `archived: <TODAY>`.

## Step 6: Report

Write the report with the vault template to `6. Atomic Notes/Vault Cleaning <TODAY>.md`, tags `review` and `vault_maintenance`, `kind: record`. Its sections:

| Section | Content |
|---|---|
| Before / after | Note count, orphans, hygiene issues, from the first scan and a final `vague vault-scan` |
| Hygiene | Fix counts per issue type |
| Distilled | Each plan: where its decisions went |
| Merged and archived | Each retired note, its reason, and the note that holds its content now |
| Hubs | Each new hub and the notes it links |
| Deleted | Each note moved to `.trash/` |
| Skipped clusters | False positives, so the next run skips them |
| Backlog | Clusters, plans and stale notes left for the next run, in priority order |

Then log the pointer, and tell the user you logged it:

```bash
vague memory-log vault-clean-$TODAY "Vault cleaning report: <N> fixed, <M> archived, <K> left in backlog" --doc --files "$VAULT/6. Atomic Notes/Vault Cleaning $TODAY.md" --skill vault-clean
```

End with the before/after line and the size of the backlog: "284 → 271 live notes, 143 → 118 orphans, 9 items in the backlog for the next run."

## Never

- Never rewrite or merge the body of a `record`.
- Never archive a note whose knowledge lives nowhere else.
- Never delete a note outside `9. Archive/`, and never with `rm`.
- Never create a folder other than `9. Archive/`. Hubs go in the existing `4. indexes/`.
- Never edit `1. Rough Notes/`, `2. Source Materials/`, `5. Templates/` or `8. Excalidraw/`.

## Observation Protocol

Log feedback about this skill with `vague memory-log <key> "<issue → suggestion>" --about vault-clean` (see the Memory guideline). A scanner false positive or a missed duplicate is the most useful feedback: name both notes.
