# bastack

Personal AI-powered development workflow. Twelve slash commands that cover the full software development lifecycle — from idea to retro.

## Quickstart

```bash
./install.sh
```

Then in Claude Code, use any slash command.

---

## Skill Map

### Planning
| Command | When to use |
|---------|-------------|
| `/office-hours` | You have an idea. Validates it, challenges it, writes a design doc. |
| `/plan-ceo-review` | Pressure-test scope. Expand, hold, or reduce. |
| `/plan-eng-review` | Lock in architecture, data model, test strategy. |

### Design
| Command | When to use |
|---------|-------------|
| `/design-consultation` | New project UI — creates `DESIGN.md` from scratch. |
| `/design-shotgun` | Visual brainstorm — generate 3 variants, pick one. |
| `/design-html` | Turn an approved design into production HTML/CSS. |
| `/design-review` | Visual QA on a live site — find and fix issues. |

### Execution
| Command | When to use |
|---------|-------------|
| `/ship` | Implement, test, commit, push, PR. |
| `/review` | Pre-landing code review before merging. |
| `/investigate` | Debug systematically — root cause first. |

### Reflection
| Command | When to use |
|---------|-------------|
| `/learn` | Browse, search, prune, and export project learnings. |
| `/retro` | Weekly engineering retrospective. |

---

## Workflow

```
Idea
  └─ /office-hours          → design doc
      ├─ /plan-ceo-review   → scope decisions
      └─ /plan-eng-review   → architecture locked

      ┌─ /design-consultation  → DESIGN.md
      ├─ /design-shotgun       → pick a layout
      └─ /design-html          → production HTML

          └─ /ship         → implement + PR
              └─ /review   → pre-landing review
                              └─ merge

                              /investigate   (when bugs happen)
                              /learn         (anytime)
                              /retro         (end of week)
```

---

## State

All data lives in `~/.bastack/`:

```
~/.bastack/
├── config.yaml
├── sessions/
├── analytics/
│   └── skill-usage.jsonl
└── projects/
    └── {slug}/
        ├── learnings.jsonl
        ├── timeline.jsonl
        ├── retros/
        └── designs/
```

---

## Config

```bash
bs-config set proactive true    # auto-suggest skills
bs-config set proactive false   # only explicit /commands
bs-config set telemetry local   # log locally
bs-config set telemetry off     # no logging
bs-config list                  # show all config
```

---

## Analytics

```bash
bs-analytics        # last 7 days
bs-analytics 30d    # last 30 days
bs-analytics all    # all time
```

---

## Requirements

- macOS or Linux
- `bun` (for JSON processing in bin scripts)
- `git`
- `gh` CLI (optional, for PR creation in `/ship`)
- Claude Code

---

## Docs

- [Architecture](docs/architecture.md) — state directory, data model, preamble lifecycle
- [Skill authoring](docs/skill-authoring.md) — how to write a new skill
- [Telemetry](docs/telemetry.md) — what is logged and where
