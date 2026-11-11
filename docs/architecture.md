# Architecture

## Overview

`vague` is a Python CLI package that sits between AI tool skills (Markdown files) and the local filesystem. There is no server, no cloud, no registry.

```
AI tool session (Claude Code / Cursor / Windsurf)
    │
    ├── reads  ~/.claude/skills/{skill-name}/SKILL.md   (or ~/.cursor/skills/…)
    │          └── skill calls `vague` CLI commands
    └── vague  ← Python package on $PATH
               └── reads/writes ~/.vague/
```

---

## What Gets Injected Into the LLM

When the user types `/dev-ship` (or any skill), this is what ends up in the LLM's context window, in order:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         LLM CONTEXT WINDOW                              │
│                                                                         │
│  1. CLAUDE.md / .cursor/rules/vague.mdc          (always present)       │
│     guidelines.md (incl. the Memory section) + skill routing table      │
│                              │                                          │
│                              ▼                                          │
│  2. SKILL.md                 (the invoked skill's instructions)         │
│     frontmatter, preamble, steps, Observation Protocol, Handoff         │
│                              │                                          │
│      agent runs eval "$(vague context --shell --skill dev-ship)"        │
│                              ▼                                          │
│  3. Preamble output          (tool output, ≤ 1,500 tokens of memory)    │
│     SLUG=acme-api  BRANCH=feat/payments  PROACTIVE=True  TELEMETRY=local│
│     vague memory · scope acme-api · 2 memories                          │
│     Memories (most relevant first):                                     │
│     - [payments-stripe] Use Stripe webhooks for async confirmation.     │
│     - [global/verify-subagent-claims] Re-run tests after subagents.     │
│                              │                                          │
│                              ▼                                          │
│  4. On-demand reads          (skill-specific tool outputs)              │
│     /triage → vague status, git · /dev-ship → git diff, tests           │
│     /dev-investigate → vague memory-search, stack trace, git log        │
│     /retro → git log, events log · /meta → memory-search --scope all    │
│                              │                                          │
│                              ▼                                          │
│  5. Conversation history     (grows throughout the session)             │
└─────────────────────────────────────────────────────────────────────────┘
```

### Approximate Token Budget Per Skill Invocation

| Layer | Typical size | Notes |
|-------|-------------|-------|
| CLAUDE.md | ~4,000–5,000 tokens | Guidelines plus the routing table |
| SKILL.md | ~1,500–4,000 tokens | Varies by skill complexity |
| Preamble MEMORY block | ≤ 1,500 tokens | Hard cap of 6,000 characters, whatever the ledger size |
| On-demand reads | ~500–15,000 tokens | Git diffs are the biggest variable |
| Conversation history | ~500–10,000 tokens | Grows across multi-turn sessions |
| **Total at invocation** | **~8,000–35,000 tokens** | Well within the context window |

The MEMORY block fills its budget in this order:

| Part | Content | Cap |
|---|---|---|
| Scratch | Notes from this scope's agents, last 7 days | 300 tokens |
| Full lines | `- [key] text` for this scope plus `global`, ranked | 1,200 tokens, global at most a third |
| Index lines | `- [key]` only, for the next memories in rank order | 300 tokens |
| Pointer | `+N more: vague memory-search <words>` | 1 line |

Ranking is deterministic: shared files with the uncommitted changes first, then the running skill's own memories, then the newest.

### What Is NOT Injected

- Observations (feedback about skills). Only `/meta` reads them.
- Memories past the budget. `vague memory-search <words>` finds them on demand.
- Other projects' memories, unless they are `global` or searched with `--scope all` or `--scope <project>`.

---

## State Directory Layout

```
~/.vague/
├── config.md                 ← frontmatter: proactive, telemetry
├── memory.jsonl              ← every learning and observation, all projects (append-only)
├── scratch/<scope>.jsonl     ← shared working notes per project, hidden after 7 days
├── events/YYYY-MM.jsonl      ← skill starts, memory reads/writes with `ids`
├── projects/<owner-repo>/    ← documents, not memory
│   ├── designs/              ← design docs, eng plans, HTML output
│   ├── diagrams/             ← /diagram output
│   └── retros/               ← retro-YYYY-MM-DD.md
├── team/                     ← mgmt-* state
├── interview/                ← iv-* state
└── archive/<date>/           ← old stores, after `vague migrate --archive`
```

Every write to `memory.jsonl`, `scratch/` and `events/` is one `os.write` on an `O_APPEND` file descriptor. No lock is taken. A torn last line is skipped with a warning.

### Project Scope

The `scope` of a memory is the project slug:

| Where the command runs | `scope` |
|---|---|
| A git repo with an `origin` remote | `owner-repo` from the remote URL |
| A git repo without a remote | Folder name of the main checkout, so all worktrees share it |
| Outside a repo | Folder name of the current directory |
| `$HOME` or `/` | None: `memory-log` refuses unless `--global` is passed |

```bash
vague slug         # prints SLUG=owner-repo and BRANCH=main
```

---

## Skill Lifecycle

Every skill follows this pattern:

```
0. hook: vague log-event
   └── appends a skill_start event to ~/.vague/events/YYYY-MM.jsonl

1. eval "$(vague context --shell --skill {name})"
   └── sets SLUG/BRANCH/PROACTIVE/TELEMETRY
   └── prints the MEMORY block, logs a context_read event with the served ids

2. [skill does its work — reads files, writes code, asks questions]

3. vague memory-log <key> "<text>" --files <paths> --skill {name}   (when a fact is worth keeping)
   └── appends one line to ~/.vague/memory.jsonl, logs context_write with the id
```

Step 0 is **mechanical telemetry**: a Claude Code hook records each skill start, so no agent can skip it. Step 3 stays discretionary. The Memory section of `guidelines.md` tells the agent when to use it.

`vague context` is the **keystone**: it never fails. Missing config returns defaults. A missing git remote falls back to the folder name. A broken ledger drops the MEMORY block, and the variables still print.

`vague status` reads the events log and the memory ledger: one row per `repo`
seen in events, its latest `main_root` path, last activity, design docs newer
than the last `dev-ship` start ("in-flight plans"), active memory counts — and renders the cross-project dashboard that `/triage`
runs as Step 0.

---

## Data Model

`memory.jsonl` holds one record type, `Memory`, with 8 fields:

```json
{"ts":"2026-10-05T14:01:29Z","scope":"acme-api","key":"tests-need-docker","kind":"learning","text":"Tests and mypy run only inside the train container; the host .venv has no pytest.","files":["Taskfile.yml"],"skill":"dev-ship","status":"active"}
{"ts":"2026-11-11T12:46:09Z","scope":"global","key":"ship-no-test-step","kind":"observation","text":"dev-ship committed before running tests → add a test step before commit","skill":"dev-ship","status":"active"}
```

| Field | Meaning |
|---|---|
| `ts` | UTC time of the write, set by the CLI |
| `scope` | A project slug, or `global` |
| `key` | Kebab-case name, unique within its scope |
| `kind` | `learning`, or `observation` when written with `--about` |
| `text` | The fact, at most 600 characters |
| `files` | Repo-relative paths the fact touches, used for ranking |
| `skill` | For a learning, the skill that wrote it. For an observation, the skill it is about |
| `status` | `active`, `forgotten`, `actioned` or `declined` |

**Fold rule:** a reader merges lines per (`scope`, `key`) in file order, and the latest non-empty value of each field wins. Re-logging a key supersedes it. A status-only line forgets it. History stays in the file.

**Curation:** `/meta` reads every memory with `vague memory-search --scope all` and the model judges what to fix: duplicates within a project, the same fact in two projects (re-logged once with `--global`), and memories whose `files` no longer exist. It acts with `memory-log` and asks before forgetting anything. Nothing is deleted automatically.

---

## Skill Chaining

Skills chain through shared file artifacts. `/triage` is the front door: it writes
no artifact, it reads git state and routes to the skill below that fits.

```
/triage         → triage; routes to any skill below (no artifact written)

/plan-ideation      → writes design doc to ~/.vague/projects/{slug}/designs/
                       ("think bigger" on an existing doc writes a scope review doc)
/plan-eng           → reads scope review + design doc, writes engineering plan

/diagram            → reads code or notes, writes HTML diagram to ~/.vague/projects/{slug}/diagrams/
/vault export       → copies an artifact into ~/Obsidian/Attachments/, writes a note that embeds it
/vault-excalidraw   → writes a Mermaid flowchart into a vault note, copies it for Excalidraw's Mermaid import
/slides             → reads notes or a .pptx, writes a self-contained HTML deck to the user's cwd

/dev-develop        → implements the plan
/dev-ship           → runs tests, reviews the diff, commits, opens PR
/retro              → reads events + git log, writes retro-YYYY-MM-DD.md
```

Each skill that writes a doc announces the output path and suggests the next skill.

---

## Workflow Examples

### Memory Across Sessions and Agents

`~/.vague/` is agent-agnostic. A memory written by Claude Code reaches Cursor's next preamble, and the reverse.

```
Day 1 — Claude Code — /dev-investigate on acme-api
  preamble    → MEMORY block: 0 memories
  agent       → traces a slow checkout to an N+1 on Order.line_items
  memory-log  → vague memory-log order-lineitems-n-plus-one \
                  "Order.line_items is never eager-loaded. Fix: includes(:line_items)." \
                  --files app/models/order.rb --skill dev-investigate
              → memory.jsonl +1 line, events +1 context_write (ids: acme-api/order-lineitems-n-plus-one)

─────────────────────────────────────────────── Day 3 — Cursor — /dev-ship
  preamble    → git diff touches app/models/order.rb, so the memory ranks first:
                - [order-lineitems-n-plus-one] Order.line_items is never eager-loaded...
  agent       → applies the fix, writes a regression test, commits
  memory-log  → vague memory-log eager-load-in-controller \
                  "Add includes() in the controller scope, not the view." --skill dev-ship

─────────────────────────────────────────────── Day 4 — any repo — /dev-develop
  memory-log  → vague memory-log verify-subagent-claims \
                  "Re-run tests yourself after subagents report success." --global
              → scope global: every repo's preamble can show it

─────────────────────────────────────────────── Day 7 — /retro, then /meta
  /retro      → events: 3 skill runs on acme-api, 2 memories written this week
  /meta       → memory-search --scope all: no duplicates, 1 dead path → forget it
```

**Key properties of this model:**

| Property | Behaviour |
|----------|-----------|
| Agent-agnostic | Claude Code and Cursor read and write the same `~/.vague/` |
| Session-persistent | Memories survive session restarts and reboots |
| Scoped, with a global layer | Each repo has its own scope. `--global` memories reach every repo |
| Bounded | The preamble never prints more than 1,500 tokens of memory |
| Superseding | Re-logging a key keeps only the latest text, and history stays in the file |
| Measurable | Events carry the `ids` served and written, so unused memories show up |
| No sync required | Fully local — nothing to push, pull, or configure |
