---
name: vault-excalidraw
version: 2.0.0
description: |
  Draw an editable Excalidraw diagram for the Obsidian vault by writing a Mermaid flowchart:
  an architecture with big zones (subgraphs) holding their real parts, a numbered flow,
  a mind map, or a timeline, with feedback loops drawn explicitly. Saves a vault note
  holding the Mermaid block (Obsidian and Notion render it) and copies the block to the
  clipboard for Excalidraw's Mermaid import, which turns it into editable shapes.
  Trigger: "excalidraw", "draw this in excalidraw", "excalidraw in my vault",
  "add this to my excalidraw", "draw the architecture in excalidraw",
  "draw the training windows", "/vault-excalidraw".
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
  - Agent
  - AskUserQuestion
---

## Preamble

```bash
eval "$(vague context --shell --skill vault-excalidraw)"
VAULT="$HOME/Obsidian"
PLUGIN="$VAULT/.obsidian/plugins/obsidian-excalidraw-plugin"
[ -d "$PLUGIN" ] && echo "PLUGIN: on" || echo "PLUGIN: off"
command -v pbcopy >/dev/null && echo "CLIPBOARD: pbcopy" || echo "CLIPBOARD: none"
ls "$VAULT"
```

- `PLUGIN: off`: tell the user to enable the **Excalidraw** community plugin. The note still works without it, because Obsidian renders Mermaid natively.
- `CLIPBOARD: none`: print the Mermaid block in the final report instead of copying it.
- The `ls` output gives the real vault folder names. Use them as they are; never create a numbered folder that does not exist.

You never place coordinates. Mermaid lays the diagram out, and Excalidraw's Mermaid import turns it into editable shapes. You cannot see the result, so every label must read correctly without a picture of it.

Write a **flowchart** every time. Excalidraw converts flowcharts into editable shapes; other Mermaid types (`gantt`, `mindmap`, `timeline`) arrive as a flat image.

---

## Step 1: Pick the Layout from the Content

The content decides the layout. Pick without asking when the table makes it obvious.

| The content is… | Layout | Mermaid skeleton |
|---|---|---|
| A system: data stores, jobs, services, deployments | **Architecture**: one `subgraph` per zone (warehouse, orchestration, registries, cluster, consumers), the real parts inside, arrows between parts | `flowchart LR` + one `subgraph` per zone |
| Steps that happen in order | **Flow**: numbered nodes, a label on every arrow | `flowchart LR` |
| The parts of one concept, no direction | **Map**: a centre node, one branch node per part, items hanging off each branch, a dashed `NOT` branch | `flowchart TB` |
| Date ranges or schedules (training windows, crons) | **Timeline**: one `subgraph` per moment in time order, the date in its title; the delay written on the arrow between moments | `flowchart LR` |

If two layouts fit, ask once via AskUserQuestion with your recommendation first. A system with more than one kind of part is always an architecture.

---

## Step 2: Gather the Real Content

Read the source of truth (code, config, infra repos, query results, the conversation) before writing anything. Every node holds a real name: a table, a job, a service, a path. Delegate to Explore or general-purpose agents when the facts span several repos, and run them in parallel.

### For an architecture: trace every dependency, not just the next hop

1. **List the zones** (5–7). Name each with its real platform: `BigQuery tranquil-garage-393215`, `Vertex AI · europe-west1`, `GKE ns ml-customer-risk`.
2. **List each zone's parts** with what triggers them (cron, event, manual) and what they read and write.
3. **Follow every output through all of its readers**, then through *their* readers, over at least two cycles (two days for daily jobs). One hop is not enough: the interesting failures cross zones and days.
4. **Name every loop** that brings an output back to an earlier input, such as a job whose output feeds the next day's build. Confirm each loop in the code (the join, the read) before drawing it.
5. **Say what is NOT linked** when a link would be expected: two jobs on a clock with no completion check, a service that never calls the store it seems to depend on.

### For a flow, a map or a timeline

- **Flow:** 2–9 steps, each a real name; each arrow says what moves across it (`writes john_p_value`, `HTTP POST /predict`).
- **Map:** 2–7 branches with real names, up to about 5 items each; add `NOT` items whenever a misconception is likely.
- **Timeline:** anchor on one real reference day and compute real dates from it. Write the relative form next to the date: `2026-06-24 (D − 3m25d)`. Put the filters of each window on the arrow that feeds it.

---

## Step 3: Write the Mermaid

Use only the subset below. It renders in Obsidian and Notion and survives the Excalidraw import.

| Element | Syntax | Rule |
|---|---|---|
| Direction | `flowchart LR` | `LR` for architectures, flows and timelines; `TB` for maps |
| Zone | `subgraph dwh["🗄️ Data warehouse · BigQuery"]` … `end`, with `direction TB` inside | At most 2 nesting levels |
| Part | `train["customer-risk-training<br>06:15 Mon–Sat"]` | Quote every label. Use `<br>` for line breaks, under about 40 characters per line. |
| Table or store | `training[("dwh_ml.training")]` | Cylinder shape for data |
| Arrow | `a -->|"reads"| b` | A label on every arrow, saying what flows |
| Pull or config | `a -.->|"image by env tag"| b` | Dotted for things read at start-up or by reference |
| Loop | `a ==>|"🔁 LOOP 1 · next day 03:00"| b` | Thick, numbered, and explained under the diagram |

Hard rules:

- **IDs** are short `snake_case` words. Never use `end`, `graph` or `subgraph` as an ID.
- **No styling**: no `classDef`, `style` or `linkStyle`. The import may drop them, so meaning must sit in the labels.
- **At most ~40 nodes per diagram.** For a bigger system, write an overview diagram (one node per zone) plus one zoom diagram per zone, each in its own block, with the same names.
- **Group arrows by purpose** under `%%` comments (`%% Inputs`, `%% Deploy`, `%% Loops`) so the source stays reviewable.

---

## Step 4: Write the Vault Note

The note is the deliverable. Obsidian renders the Mermaid block, and its text stays searchable, unlike the text inside a drawing.

| Content | Folder |
|---|---|
| Architecture, code walkthrough | `7. Code/` if it exists, else `6. Atomic Notes/` |
| Anything else | `6. Atomic Notes/` |

Use the `/vault` save template exactly: frontmatter with `aliases` and `tags`, `# YYYY-MM-DD - Title` heading, then:

1. One sentence on what the diagram is for.
2. **Open it in Excalidraw** instructions (Step 5).
3. The Mermaid block or blocks.
4. **How to read it**: a table with one row per zone (zone → what it holds → the lesson it carries).
5. **Loops**: one numbered item per loop, with the file that proves it.
6. **Not verified**: every fact you could not confirm. Never leave this section out; write "none" if empty.
7. `# Next Actions` and `# References` (the real source files and repos).

---

## Step 5: Hand the Diagram to Excalidraw

Copy the Mermaid source (without the fences) to the clipboard:

```bash
python3 -c "import re,sys;print(re.search(r'\`\`\`mermaid\n(.*?)\`\`\`', open(sys.argv[1]).read(), re.S).group(1), end='')" "<note path>" | pbcopy
```

The user then pastes it into Excalidraw's Mermaid import ("Mermaid to Excalidraw"), which creates editable shapes they can rearrange. In the Excalidraw web app it sits under **More tools**; the menu in the Obsidian plugin may differ, so name the feature, not a menu path you have not seen.

With several blocks, copy the overview first and say which block is in the clipboard.

---

## Step 6: Report

Tell the user, in this order:

1. The note path.
2. A small ASCII sketch of the zones and loops, so they know what to look for.
3. What is in the clipboard and how to import it.
4. That you cannot see the import: ask them which labels break, which arrows lose their style, and whether nested zones flatten. Fix the Mermaid, rewrite the note and copy the block again.

---

## Observation Protocol

Throughout this skill's execution, watch for:
- Steps that produce wrong or suboptimal output
- Missing rules the user has to correct
- Workflow inefficiencies or unnecessary steps
- Gaps where a different skill would help
- **User corrections**: any time the user tells you to do something the skill should have done automatically (e.g. "show the loop", "put the tables inside the warehouse box")
- **Import problems**: any Mermaid construct that the Excalidraw import breaks or drops (`<br>` shown literally, flattened zones, lost arrow styles)

When you notice any of these, log an observation:

```bash
vague observations-log '{"skill":"vault-excalidraw","type":"improvement","issue":"WHAT_HAPPENED","suggestion":"CONCRETE_CHANGE","principle":"GENERALISABLE_TAKEAWAY","source_skill":"vault-excalidraw"}'
```

**User correction detection:** If the user has to explicitly ask you to perform a step that should be part of this skill's workflow, log it immediately as a `type: correction` observation. These are the most valuable signals for skill improvement. Import complaints ("labels show <br>", "the zones are gone") are corrections too: they mean the Step 3 subset needs work.

```bash
vague observations-log '{"skill":"vault-excalidraw","type":"correction","issue":"User had to manually ask: WHAT_THEY_SAID","suggestion":"Add this as an explicit step in the skill","principle":"GENERALISABLE_TAKEAWAY","source_skill":"vault-excalidraw"}'
```

Log silently. Do not interrupt the user's workflow to announce observations.

---

## Handoff

> "Note written to `<path>`; the Mermaid is in your clipboard. Paste it into Excalidraw's Mermaid import, then tell me what breaks. Next: `/vault save` for related notes, or `/diagram` for a non-editable HTML version."
