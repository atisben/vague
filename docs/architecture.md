# Architecture

## Overview

bastack is a collection of Claude Code slash commands (skills) + a set of shell scripts that manage local state. There is no server, no cloud, no registry.

```
Claude Code session
    │
    ├── reads  ~/.claude/skills/bastack/{skill-name}/SKILL.md
    ├── sources skills/_preamble.sh  (shared setup)
    └── calls  bin/bs-*              (state management)
               └── writes to ~/.bastack/
```

---

## State Directory Layout

```
~/.bastack/
├── config.yaml                         ← user config (proactive, telemetry)
├── sessions/                           ← PID-based session tracking (cleaned after 2h)
├── analytics/
│   └── skill-usage.jsonl               ← {skill, ts, repo, session}
└── projects/
    └── {slug}/                         ← one dir per git repo
        ├── learnings.jsonl             ← append-only learning entries
        ├── timeline.jsonl              ← session events (started, completed)
        ├── retros/
        │   └── retro-YYYY-MM-DD.md    ← weekly retro archives
        └── designs/
            └── *.md / *.html          ← design docs, shotgun variants, HTML output
```

### Project Slug

Derived from `git remote get-url origin` → `owner-repo`. Falls back to `basename $PWD`. Sanitized to `[a-zA-Z0-9._-]`.

```bash
eval "$(bs-slug)"  # sets $SLUG and $BRANCH
```

---

## Preamble Lifecycle

Every skill starts by sourcing `skills/_preamble.sh`. The preamble:

1. Sets `BASTACK_HOME` (default `~/.bastack`)
2. Touches a session file at `~/.bastack/sessions/$PPID` (proves session is alive)
3. Cleans up session files older than 2 hours
4. Reads `proactive` and `telemetry` from `bs-config`
5. Runs `bs-slug` → exports `$SLUG`, `$BRANCH`
6. Surfaces top 3 learnings if project has > 5 entries
7. Logs to `analytics/skill-usage.jsonl` (if telemetry is on)
8. Fires a background `bs-timeline-log` with `started` event

The skill then runs its own logic, and at the end should call `bs-timeline-log` with a `completed` event.

---

## JSONL Schemas

### learnings.jsonl
```json
{
  "skill": "review",
  "type": "pitfall",
  "key": "n-plus-one-user-scope",
  "insight": "User association is always loaded separately — use includes(:user) on every list query.",
  "confidence": 8,
  "source": "observed",
  "files": ["app/controllers/posts_controller.rb"],
  "ts": "2025-04-08T09:00:00.000Z"
}
```

**Types:** `pattern`, `pitfall`, `preference`, `architecture`, `tool`, `operational`
**Sources:** `observed`, `user-stated`, `inferred`
**Confidence:** 1-10. Observed patterns: 7-9. Inferences: 4-6. User-stated: 10.
**Dedup rule:** Latest entry per `key+type` wins (append-only, resolve at read time).

### timeline.jsonl
```json
{"skill": "ship", "event": "started", "branch": "feat/auth", "session": "12345-1712566800", "ts": "2025-04-08T09:00:00.000Z"}
{"skill": "ship", "event": "completed", "branch": "feat/auth", "session": "12345-1712566800", "outcome": "success", "ts": "2025-04-08T09:25:00.000Z"}
```

### analytics/skill-usage.jsonl
```json
{"skill": "ship", "ts": "2025-04-08T09:25:00.000Z", "repo": "owner-myrepo"}
```

---

## Bin Scripts

| Script | Purpose |
|--------|---------|
| `bs-config` | Read/write `~/.bastack/config.yaml` |
| `bs-slug` | Derive `$SLUG` and `$BRANCH` from git context |
| `bs-learnings-log` | Append a learning entry to `learnings.jsonl` |
| `bs-learnings-search` | Filter/display learnings with confidence decay and dedup |
| `bs-timeline-log` | Append a session event to `timeline.jsonl` |
| `bs-analytics` | Local skill usage dashboard from `skill-usage.jsonl` |

All scripts accept `BASTACK_HOME` env override for testing.

---

## Skill Chaining

Skills chain through design doc discovery:

```
/office-hours       → writes design doc to ~/.bastack/projects/{slug}/designs/
/plan-ceo-review    → reads that doc, writes CEO plan doc
/plan-eng-review    → reads CEO plan + design doc, writes engineering plan

/design-consultation → writes DESIGN.md to project root
/design-shotgun      → reads DESIGN.md, writes HTML variants to /designs/
/design-html         → reads DESIGN.md + shotgun HTML, writes production HTML
/design-review       → reads DESIGN.md, audits source files
```

Each skill that writes a doc announces the output path and suggests the next skill to run.
