# vague

Python CLI layer for LLM skill-based AI workflows. Sixteen slash commands covering the full software development lifecycle — from triage to retro.

Skills are markdown files. `vague` is the stable CLI contract between them and the filesystem.

## Quickstart

```bash
git clone https://github.com/atisben/vague.git && cd vague
uv tool install .      # installs vague globally via ~/.local/bin
vague install          # auto-detects Claude Code, Copilot, Cursor, or Windsurf
```

Then use any slash command in your AI tool.

---

## Skill Map

### Entry point
| Command | When to use |
|---------|-------------|
| `/desk` | The front door. Triage what's on your plate and route to the right skill. |

### Planning
| Command | When to use |
|---------|-------------|
| `/office-hours` | You have an idea. Validates it, challenges it, writes a design doc. |
| `/plan-ceo-review` | Pressure-test scope. Expand, hold, or reduce. |
| `/plan-eng-review` | Lock in architecture, data model, test strategy. |

### Design
| Command | When to use |
|---------|-------------|
| `/design-consultation` | Create a complete design system — aesthetic, typography, color, layout. |
| `/design-shotgun` | Visual brainstorm — generate 3 variants, pick one. |
| `/design-html` | Turn an approved design into production HTML/CSS. |
| `/design-review` | Visual QA on a live site — find and fix issues. |

### Execution
| Command | When to use |
|---------|-------------|
| `/develop` | Orchestrate a feature across fresh-context subagents. |
| `/ship` | Implement, test, commit, push, PR. |
| `/review` | Pre-landing code review before merging. |
| `/investigate` | Debug systematically — root cause first. |

### Reflection
| Command | When to use |
|---------|-------------|
| `/learn` | Browse, search, prune, and export project learnings. |
| `/retro` | Weekly engineering retrospective. |
| `/meta` | Review observations and improve the skills themselves. |
| `/vault` | Save and retrieve notes from your Obsidian vault. |

---
## System design

![architecture](architecture.png)

---

## Workflow

```
/desk                       → triage + route to any skill below

Idea
  └─ /office-hours          → design doc
      ├─ /plan-ceo-review   → scope decisions
      └─ /plan-eng-review   → architecture locked

      ├─ /design-shotgun    → pick a layout
      └─ /design-html       → production HTML

          └─ /ship          → implement + PR
              └─ /review    → pre-landing review
                               └─ merge

                              /investigate   (when bugs happen)
                              /learn         (anytime)
                              /retro         (end of week)
```

---

## State

All data lives in `~/.vague/`:

```
~/.vague/
├── config.md
├── sessions/
├── analytics/
│   └── skill-usage.md
└── projects/
    └── {owner-repo}/
        ├── learnings.md
        ├── timeline.md
        ├── retros/
        └── designs/
```

---

## CLI Reference

```bash
vague init                              # JSON context for skills (slug, branch, config, learnings)
vague context --shell                   # eval-able SLUG=/BRANCH=/PROACTIVE=/TELEMETRY= for preambles
vague config-get proactive              # read config value
vague config-set proactive false        # write config value
vague learnings-log '<json>'            # append a learning
vague learnings-search --type pitfall   # filter learnings
vague analytics-show 7d                 # usage dashboard (7d | 30d | all)
vague slug                              # print SLUG= and BRANCH=
vague timeline-log '<json>'             # append session event
vague commit "msg" --files f1 f2        # atomic git commit
vague skill-validate <dir>              # validate a skill against the contract
vague skill-audit <dir> --strict        # scan for legacy bash patterns
```

---

## Requirements

- Python 3.11+
- `git`
- `gh` CLI (optional, for PR creation in `/ship`)
- Claude Code and/or GitHub Copilot CLI

---

## Docs

- [Architecture](docs/architecture.md) — state directory, data model, skill lifecycle
- [Skill authoring](docs/skill-authoring.md) — how to write a new skill
- [Telemetry](docs/telemetry.md) — what is logged and where


## Updates

In order to reinstall the latest update of vague, use 
```bash
uv tool install . --force --reinstall
```

## Inspirations

- [gstack](https://github.com/garrytan/gstack): An ensemble of advanced skills using bash command to interract with persistent, project checkpoints
- [karpathy's wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f): A paradigm for saving persisent files to local wiki that serves as a brain for LLM supported tasks
- [get shit done](https://github.com/gsd-build/get-shit-done): A light-weight meta-prompting, context engineering, and spec-driven development system
