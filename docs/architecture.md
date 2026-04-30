# Architecture

## Overview

`vague` is a Python CLI package that sits between AI tool skills (Markdown files) and the local filesystem. There is no server, no cloud, no registry.

```
AI tool session (Claude Code / GitHub Copilot CLI / Cursor / Windsurf)
    │
    ├── reads  ~/.claude/skills/{skill-name}/SKILL.md   (or ~/.copilot/skills/…)
    │          └── skill calls `vague` CLI commands
    └── vague  ← Python package on $PATH
               └── reads/writes ~/.vague/
```

---

## What Gets Injected Into the LLM

When the user types `/ship` (or any skill), this is what ends up in the LLM's context window, in order:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         LLM CONTEXT WINDOW                              │
│                                                                         │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │ 1. CLAUDE.md / .github/copilot-instructions.md                   │   │
│  │    (project-level, always present)                               │   │
│  │                                                                  │   │
│  │    - Skill routing table (which /command maps to which skill)    │   │
│  │    - Project description and stack                               │   │
│  │    - Testing framework and commands                              │   │
│  │    ~ 1–3 KB                                                      │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                              │                                          │
│                              ▼                                          │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │ 2. SKILL.md  (the invoked skill's full instruction set)          │   │
│  │                                                                  │   │
│  │    - Frontmatter (name, version, sdk_commands, allowed-tools)    │   │
│  │    - `vague init` call  ◄── agent executes this first            │   │
│  │    - Step-by-step instructions for the skill                     │   │
│  │    - AskUserQuestion patterns, decision trees                    │   │
│  │    - Handoff block                                               │   │
│  │    ~ 3–8 KB per skill                                            │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                              │                                          │
│              Agent runs `CONTEXT=$(vague init)`                         │
│                              │                                          │
│                              ▼                                          │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │ 3. vague init OUTPUT  (runtime context, injected as tool output) │   │
│  │                                                                  │   │
│  │    {                                                             │   │
│  │      "slug":      "bastien-myrepo",                              │   │
│  │      "branch":    "feat/payments",                               │   │
│  │      "proactive": true,                                          │   │
│  │      "telemetry": "local",                                       │   │
│  │      "learnings": [                                              │   │
│  │        {                                                         │   │
│  │          "type": "pitfall", "key": "n-plus-one-user-scope",      │   │
│  │          "insight": "Always use includes(:user) on list queries.",│   │
│  │          "confidence": 8, "source": "observed"                   │   │
│  │        },                                                        │   │
│  │        { "type": "pattern", "key": "slug-derivation", ... }      │   │
│  │      ]                                                           │   │
│  │    }                                                             │   │
│  │                                                                  │   │
│  │    ~ 0.5–2 KB depending on learnings count                       │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                              │                                          │
│            Agent then reads additional files per skill logic            │
│                              │                                          │
│                              ▼                                          │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │ 4. ON-DEMAND READS  (skill-specific, injected as tool outputs)   │   │
│  │                                                                  │   │
│  │    /office-hours      → prior design docs (if any)              │   │
│  │    /plan-ceo-review   → most recent design doc                   │   │
│  │    /plan-eng-review   → design doc + CEO plan doc                │   │
│  │    /design-*          → DESIGN.md (if present)                  │   │
│  │    /ship              → git diff, git log, test output           │   │
│  │    /review            → full git diff                            │   │
│  │    /investigate       → stack trace, git log, error logs         │   │
│  │    /retro             → git log --stat, prior retro doc          │   │
│  │                                                                  │   │
│  │    ~ 1–50 KB depending on diff/log size                          │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                              │                                          │
│                              ▼                                          │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │ 5. CONVERSATION HISTORY  (accumulated during the session)        │   │
│  │                                                                  │   │
│  │    - User messages and AskUserQuestion responses                 │   │
│  │    - Tool call outputs (bash, read, write, edit)                 │   │
│  │    - Agent's own prior responses in this session                 │   │
│  │                                                                  │   │
│  │    ~ grows throughout the session                                │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Approximate Token Budget Per Skill Invocation

| Layer | Typical size | Notes |
|-------|-------------|-------|
| CLAUDE.md | ~500–1,000 tokens | Grows if you add project context |
| SKILL.md | ~1,500–4,000 tokens | Varies by skill complexity |
| `vague init` output | ~100–500 tokens | Grows with learnings surfaced |
| On-demand reads | ~500–15,000 tokens | Git diffs are the biggest variable |
| Conversation history | ~500–10,000 tokens | Grows across multi-turn sessions |
| **Total at invocation** | **~3,000–30,000 tokens** | Well within 200K context window |

### What Is NOT Injected

- Full `learnings.md` (only top 3 by confidence, surfaced by `vague init`)
- Full `timeline.md` (write-only from skills — read by `/retro` only)
- `skill-usage.md` analytics (only read by `vague analytics-show`, not by LLM)
- Other projects' data (scoped strictly to the current slug)

---

## State Directory Layout

```
~/.vague/
├── config.md                           ← frontmatter: proactive, telemetry
├── sessions/                           ← PID files for session tracking
├── analytics/
│   └── skill-usage.md                  ← frontmatter list of usage entries
└── projects/
    └── {owner-repo}/                   ← one dir per git repo
        ├── learnings.md                ← frontmatter list of LearningEntry (max 500)
        ├── timeline.md                 ← frontmatter list of TimelineEntry
        ├── retros/
        │   └── retro-YYYY-MM-DD.md    ← weekly retro archives
        └── designs/
            └── *.md / *.html          ← design docs, shotgun variants, HTML output
```

All state files use YAML frontmatter. `vague` reads and writes them atomically with `fcntl` file locking — safe for concurrent skill invocations.

### Project Slug

Derived from `git remote get-url origin` → `owner-repo`. Falls back to `basename $PWD` if no remote. Never raises.

```bash
vague slug         # prints SLUG=owner-repo and BRANCH=main
CONTEXT=$(vague init)   # full JSON context including slug and branch
```

---

## Skill Lifecycle

Every skill follows this pattern:

```
1. CONTEXT=$(vague init)
   └── reads config, slug, top-3 learnings → JSON into agent context

2. [skill does its work — reads files, writes code, asks questions]

3. vague learnings-log '{"skill":"...", "type":"pitfall", "key":"...", ...}'
   └── appended to ~/.vague/projects/{slug}/learnings.md

4. vague timeline-log '{"skill":"...", "event":"completed", ...}'
   └── appended to ~/.vague/projects/{slug}/timeline.md
```

`vague init` is the **keystone**: it never fails. If config is missing, it returns defaults. If there's no git remote, it falls back to directory name. Skills always get a valid JSON context.

---

## Data Model

All files use YAML frontmatter. Example `learnings.md`:

```markdown
---
entries:
  - skill: review
    type: pitfall
    key: n-plus-one-user-scope
    insight: Always use includes(:user) on list queries — loading users separately causes N+1s.
    confidence: 8
    source: observed
    files:
      - app/controllers/posts_controller.rb
    ts: "2025-04-08T09:00:00Z"
  - skill: ship
    type: pattern
    key: migration-always-reversible
    insight: Every migration must have a down() method. Irreversible migrations blocked deploys twice.
    confidence: 9
    source: observed
    ts: "2025-04-15T14:22:00Z"
---
```

**Learning types:** `pattern` · `pitfall` · `preference` · `architecture` · `tool` · `operational`
**Sources:** `observed` · `user-stated` · `inferred`
**Confidence:** 1–10. Observed: 7–9. Inferred: 4–6. User-stated: 10.
**Dedup rule:** Latest entry per `(key, type)` pair wins — resolved at read time, not write time.
**Pruning:** When entries exceed 500, lowest-confidence entries are evicted on write.

---

## Skill Chaining

Skills chain through shared file artifacts:

```
/office-hours       → writes design doc to ~/.vague/projects/{slug}/designs/
/plan-ceo-review    → reads that doc, writes CEO plan doc
/plan-eng-review    → reads CEO plan + design doc, writes engineering plan

/design-shotgun     → writes HTML variants to ~/.vague/projects/{slug}/designs/
/design-html        → reads shotgun HTML, writes production HTML to project root
/design-review      → audits live source files against DESIGN.md

/ship               → implements, commits, opens PR
/review             → reads git diff, applies fixes pre-merge
/retro              → reads timeline.md + git log, writes retro-YYYY-MM-DD.md
```

Each skill that writes a doc announces the output path and suggests the next skill.

---

## Workflow Examples

### Classic: Feature from Idea to PR

A complete feature development cycle using four skills in sequence.

```
Day 1 — Claude Code session

  User: "I have an idea for a payments feature"

  ┌─ /office-hours ──────────────────────────────────────────────────────┐
  │  CONTEXT=$(vague init)                                               │
  │  → slug: "acme-api", branch: "main", learnings: []                  │
  │                                                                      │
  │  Agent: challenges the idea, validates demand, scope                 │
  │  Output: ~/.vague/projects/acme-api/designs/payments-20260430.md    │
  └──────────────────────────────────────────────────────────────────────┘
                              │ "Design saved. Run /plan-eng-review next."
                              ▼

  ┌─ /plan-eng-review ───────────────────────────────────────────────────┐
  │  CONTEXT=$(vague init)                                               │
  │  → slug: "acme-api", branch: "main", learnings: []                  │
  │                                                                      │
  │  Agent: reads design doc, locks architecture, data model, tests      │
  │  Output: ~/.vague/projects/acme-api/designs/acme-api-eng-20260430.md │
  │                                                                      │
  │  vague learnings-log '{"type":"architecture","key":"payments-stripe",│
  │    "insight":"Use Stripe webhooks for async confirmation, not polling"│
  │    "confidence":9,"source":"user-stated"}'                           │
  └──────────────────────────────────────────────────────────────────────┘
                              │ "Plan locked. Run /ship to implement."
                              ▼

  ┌─ /ship ──────────────────────────────────────────────────────────────┐
  │  CONTEXT=$(vague init)                                               │
  │  → slug: "acme-api", branch: "feat/payments"                        │
  │  → learnings: [{ key: "payments-stripe", confidence: 9, ... }]  ◄── surfaced
  │                                                                      │
  │  Agent reads the architecture learning before writing any code.      │
  │  Implements Stripe webhooks (not polling) — learning guided this.    │
  │                                                                      │
  │  vague commit "feat: add Stripe webhook payment confirmation"        │
  │  vague timeline-log '{"skill":"ship","event":"completed",...}'       │
  └──────────────────────────────────────────────────────────────────────┘
                              │ "PR opened. Run /review before merging."
                              ▼

  ┌─ /review ────────────────────────────────────────────────────────────┐
  │  CONTEXT=$(vague init)                                               │
  │  → learnings: [{ key: "payments-stripe", confidence: 9 }]           │
  │                                                                      │
  │  Agent reads git diff, checks for N+1s, missing rollbacks, etc.     │
  │  No issues found. PR approved.                                       │
  │                                                                      │
  │  vague learnings-log '{"type":"pattern","key":"webhook-idempotency", │
  │    "insight":"Always check event.id before processing webhooks",...}'│
  └──────────────────────────────────────────────────────────────────────┘

  Learnings written: 2
  Timeline events:   3 (ship started, ship completed, review completed)
```

---

### Complex: Persistent Memory Across Sessions and Agents

`~/.vague/` is agent-agnostic. Learnings written by Claude Code are read by GitHub Copilot CLI (and vice versa). Memory persists indefinitely across sessions.

```
Day 1 — Claude Code session — investigating a production bug

  ┌─ /investigate ───────────────────────────────────────────────────────┐
  │  CONTEXT=$(vague init)                                               │
  │  → slug: "acme-api", branch: "fix/slow-checkout", learnings: []     │
  │                                                                      │
  │  Agent traces the slow checkout to an N+1 on Order.line_items       │
  │                                                                      │
  │  vague learnings-log '{                                              │
  │    "skill": "investigate",                                           │
  │    "type": "pitfall",                                                │
  │    "key": "order-lineitems-n-plus-one",                              │
  │    "insight": "Order.line_items is never eager-loaded. Every         │
  │      checkout page triggers N queries. Fix: includes(:line_items).", │
  │    "confidence": 9,                                                  │
  │    "source": "observed",                                             │
  │    "files": ["app/models/order.rb", "app/views/checkout/show.html"] │
  │  }'                                                                  │
  │                                                                      │
  │  Session ends. The fix is too large for today.                       │
  └──────────────────────────────────────────────────────────────────────┘

  Written to disk: ~/.vague/projects/acme-api/learnings.md
                                      ↑
                              persists between sessions,
                              agents, and tools

─────────────────────────────────────────────────────── Day 3 — new session

  ┌─ /ship — GitHub Copilot CLI session ─────────────────────────────────┐
  │  CONTEXT=$(vague init)                                               │
  │  → slug: "acme-api", branch: "fix/slow-checkout"                    │
  │  → learnings: [                                                      │
  │      {                                                               │
  │        "key": "order-lineitems-n-plus-one",   ◄── from Day 1        │
  │        "type": "pitfall",                                            │
  │        "insight": "Order.line_items is never eager-loaded...",       │
  │        "confidence": 9                                               │
  │      }                                                               │
  │    ]                                                                 │
  │                                                                      │
  │  A completely different agent, different tool, different session —   │
  │  but it opens with full knowledge of what was found on Day 1.        │
  │                                                                      │
  │  Agent applies the fix: adds includes(:line_items) in the right      │
  │  places, writes a regression test, commits.                          │
  │                                                                      │
  │  vague learnings-log '{                                              │
  │    "type": "pattern",                                                │
  │    "key": "eager-load-associations",                                 │
  │    "insight": "Add includes() in the controller scope, not the view. │
  │      View-level fixes get lost on refactors.",                       │
  │    "confidence": 8, "source": "observed"                             │
  │  }'                                                                  │
  └──────────────────────────────────────────────────────────────────────┘

─────────────────────────────────────────────────── Day 7 — weekly retro

  ┌─ /retro — Claude Code session ───────────────────────────────────────┐
  │  CONTEXT=$(vague init)                                               │
  │  → slug: "acme-api"                                                  │
  │  → learnings: 2 entries (both surfaced — only 2 total)              │
  │                                                                      │
  │  Agent reads:                                                        │
  │    - timeline.md  → 4 events across 2 sessions (investigate+ship)   │
  │    - git log      → 3 commits on fix/slow-checkout this week        │
  │    - prior retros → none yet                                         │
  │                                                                      │
  │  Output: ~/.vague/projects/acme-api/retros/retro-2026-05-07.md      │
  │                                                                      │
  │  Retro excerpt:                                                       │
  │  > "Resolved N+1 on checkout (detected Day 1, fixed Day 3).         │
  │  > Lesson: N+1s in order associations are a recurring pattern here.  │
  │  > Consider adding a linter rule."                                   │
  └──────────────────────────────────────────────────────────────────────┘

State at end of week:
  ~/.vague/projects/acme-api/
    ├── learnings.md     ← 2 entries (pitfall + pattern)
    ├── timeline.md      ← 4 events across 2 agents, 2 tools
    └── retros/
        └── retro-2026-05-07.md
```

**Key properties of this model:**

| Property | Behaviour |
|----------|-----------|
| Agent-agnostic | Claude Code and GitHub Copilot CLI read and write the same `~/.vague/` |
| Session-persistent | Learnings survive session restarts, computer reboots |
| Slug-scoped | Each repo has isolated memory — `acme-api` and `acme-frontend` never mix |
| Deduplicating | Logging the same `(key, type)` twice keeps only the latest insight |
| Self-pruning | Capped at 500 entries; lowest-confidence entries evicted automatically |
| No sync required | Fully local — nothing to push, pull, or configure |
