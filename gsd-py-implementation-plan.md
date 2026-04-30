# GSD-PY — Implementation Plan v1.0

> A Python CLI package that replaces bash-based skill commands with a structured, file-agnostic state management layer. Designed to renovate existing skill-based projects and accept new skills dynamically via a skill template contract.

---

## Goals

- Replace ad-hoc bash commands embedded in skills with clean Python CLI calls (`gsd-sdk <command>`)
- Provide a stable, versioned interface between LLM skill prompts and the filesystem
- Be **skill-agnostic**: any new skill following the skill template contract can plug in without modifying the package
- Be installable via `pip install` or `pipx run`, with a single `gsd-install` command that copies skills to the right runtime directory

---

## Core Design Principles

1. **The package owns the CLI, not the skills** — Skills are markdown files that call the CLI. The package does not hard-code skill logic.
2. **The CLI is the contract** — Skills interact with the filesystem exclusively through `gsd-sdk` commands. No raw file reads/writes in skill prompts.
3. **Skill template compliance** — A skill is valid if it follows the skill template. The package validates but does not dictate skill content.
4. **Atomic state writes** — All STATE.md, ROADMAP.md, and PLAN.md mutations go through the SDK to prevent corruption.
5. **Crash-safe** — Every state transition is idempotent. Re-running a command after a crash resumes cleanly.

---

## Package Structure

```
gsd-py/
├── pyproject.toml
├── README.md
├── gsd/
│   ├── __init__.py
│   ├── installer.py          # gsd-install entry point
│   ├── sdk/
│   │   ├── __init__.py
│   │   ├── cli.py            # gsd-sdk entry point (main CLI used by skills)
│   │   ├── commands/
│   │   │   ├── init.py       # gsd-sdk init <phase>
│   │   │   ├── state.py      # gsd-sdk state-set / state-get
│   │   │   ├── plan.py       # gsd-sdk plan-list / plan-status
│   │   │   ├── commit.py     # gsd-sdk commit <msg> --files ...
│   │   │   ├── config.py     # gsd-sdk config-get / config-set
│   │   │   └── skill.py      # gsd-sdk skill-list / skill-validate
│   │   ├── core/
│   │   │   ├── state.py      # STATE.md read/write
│   │   │   ├── plan_parser.py# PLAN.md frontmatter parsing
│   │   │   ├── roadmap.py    # ROADMAP.md read/write
│   │   │   ├── config.py     # config.json management
│   │   │   └── git_ops.py    # git commit, worktrees
│   │   └── models.py         # Pydantic models (Plan, State, Phase, Skill)
│   └── assets/
│       ├── skills/           # Bundled default skills (markdown)
│       │   ├── gsd-execute-phase/
│       │   │   └── SKILL.md
│       │   ├── gsd-plan-phase/
│       │   │   └── SKILL.md
│       │   └── gsd-new-project/
│       │       └── SKILL.md
│       ├── agents/           # Bundled agent definitions (markdown)
│       │   ├── gsd-executor.md
│       │   └── gsd-verifier.md
│       └── templates/
│           └── SKILL.template.md   # The skill contract template
```

---

## Phase 1 — Core CLI Layer

**Goal:** Replace all bash commands in existing skills with `gsd-sdk` equivalents.

### 1.1 — State Management Commands

| Command | Replaces | Description |
|---|---|---|
| `gsd-sdk state-get <key>` | `grep` / `awk` on STATE.md | Read a single field from STATE.md |
| `gsd-sdk state-set <key> <value>` | `sed -i` on STATE.md | Write a field atomically |
| `gsd-sdk init <phase>` | Multiple bash reads | Return full phase context as JSON |
| `gsd-sdk config-get <key>` | `jq` on config.json | Read nested config value |
| `gsd-sdk config-set <key> <value>` | Manual JSON edit | Write config value safely |

**Implementation:**
```python
# gsd/sdk/commands/state.py
@app.command("state-get")
def state_get(key: str):
    post = frontmatter.load(STATE_PATH)
    value = post.metadata.get(key)
    typer.echo(json.dumps(value))

@app.command("state-set")
def state_set(key: str, value: str):
    post = frontmatter.load(STATE_PATH)
    post[key] = _coerce_type(value)
    post["last_activity"] = datetime.now(timezone.utc).isoformat()
    STATE_PATH.write_text(frontmatter.dumps(post))
```

### 1.2 — Plan Management Commands

| Command | Description |
|---|---|
| `gsd-sdk plan-list <phase>` | List all PLAN.md files for a phase with status (has summary or not) |
| `gsd-sdk plan-status <plan_id>` | Return plan frontmatter as JSON |
| `gsd-sdk plan-complete <plan_id>` | Mark a plan complete in ROADMAP.md |
| `gsd-sdk plan-waves <phase>` | Return plans grouped by wave as JSON |

### 1.3 — Git Commands

| Command | Replaces | Description |
|---|---|---|
| `gsd-sdk commit "<msg>" --files f1 f2` | Raw `git add && git commit` | Atomic commit, only if staged diff exists |
| `gsd-sdk worktree-create <branch> <path>` | `git worktree add` | Create isolated worktree |
| `gsd-sdk worktree-remove <path> <branch>` | `git worktree remove` | Clean up worktree |

### 1.4 — Init Query (Most Critical)

This is what every orchestrator skill calls first:

```bash
# In a skill prompt, replaces 5+ bash reads:
INIT=$(gsd-sdk init 2)
# Returns JSON:
# {
#   "phase_number": 2,
#   "phase_dir": ".planning/phases/02-auth",
#   "plan_count": 3,
#   "incomplete_count": 2,
#   "plans": [{"id": "02-01-PLAN", "wave": 1, "has_summary": true}, ...],
#   "state": { "status": "executing", "phase": 2, ... },
#   "config": { "parallelization": true, "use_worktrees": true }
# }
```

**Deliverables:**
- [ ] `gsd/sdk/core/state.py` with frontmatter read/write
- [ ] `gsd/sdk/core/plan_parser.py` with wave grouping
- [ ] `gsd/sdk/core/roadmap.py` with phase/plan tracking
- [ ] `gsd/sdk/core/git_ops.py` with atomic commit
- [ ] `gsd/sdk/commands/` — all commands wired to Typer
- [ ] `gsd/sdk/cli.py` — main `gsd-sdk` entry point

---

## Phase 2 — Installer

**Goal:** One command copies all skills + SDK to the right runtime directory.

### 2.1 — Runtime Support

| Runtime | Global install path | Local install path |
|---|---|---|
| Claude Code | `~/.claude/skills/` | `./.claude/skills/` |
| Cursor | `~/.cursor/rules/` | `./.cursor/rules/` |
| Windsurf | `~/.codeium/windsurf/memories/` | `./.windsurf/` |
| Generic | `~/.gsd/skills/` | `./.gsd/skills/` |

### 2.2 — Installer Logic

```bash
# Equivalent of: npx get-shit-done-cc@latest
pipx run get-shit-done-py

# Non-interactive
gsd-install --runtime claude --scope global
gsd-install --runtime claude --scope local --minimal
```

The installer:
1. Detects or prompts for runtime and scope
2. Copies bundled skills from `gsd/assets/skills/` to target directory
3. Copies bundled agents from `gsd/assets/agents/` to target directory
4. Verifies `gsd-sdk` is on `$PATH` (it is, via pip entry points)
5. Prints a verification command

### 2.3 — Skill Discovery

The installer also scans for **external skills** passed via a directory:

```bash
# Install built-in skills + custom skills from a local directory
gsd-install --runtime claude --scope local --skills-dir ./my-custom-skills/
```

Any directory containing a valid `SKILL.md` (passing template validation) is copied alongside built-ins.

**Deliverables:**
- [ ] `gsd/installer.py` with runtime detection and file copy logic
- [ ] `gsd-install` entry point registered in `pyproject.toml`
- [ ] External skills directory support with validation

---

## Phase 3 — Skill Template Contract

**Goal:** Define what makes a valid skill so the package can validate and integrate any new skill without code changes.

### 3.1 — The Skill Template

Every skill must be a directory containing a `SKILL.md` file with this structure:

```markdown
---
name: gsd-my-skill
version: 1.0.0
description: One line description of what this skill does
sdk_commands:
  - gsd-sdk init
  - gsd-sdk state-set
  - gsd-sdk commit
requires_planning_dir: true
---

# My Skill

[Skill prompt content here — instructions for the LLM]

## Steps

1. Initialize: `gsd-sdk init ${PHASE}`
2. Do work...
3. Commit: `gsd-sdk commit "feat: done" --files src/x.ts`
```

**Required frontmatter fields:**

| Field | Type | Description |
|---|---|---|
| `name` | string | Unique skill identifier, must match directory name |
| `version` | semver | Skill version |
| `description` | string | One-line description |
| `sdk_commands` | list | SDK commands this skill uses (for validation) |
| `requires_planning_dir` | bool | Whether `.planning/` must exist before running |

### 3.2 — Skill Validation Command

```bash
# Validate a single skill
gsd-sdk skill-validate ./my-custom-skills/gsd-my-skill/

# Validate all installed skills
gsd-sdk skill-list --validate
```

Validation checks:
- `SKILL.md` exists and has valid frontmatter
- All `sdk_commands` listed in frontmatter are valid registered commands
- No raw bash file manipulation (`sed -i`, `grep STATE.md`, etc.) in skill body
- `name` matches directory name

### 3.3 — Skill Registry

The package maintains a lightweight registry of installed skills:

```json
// ~/.gsd/registry.json (or .gsd/registry.json for local)
{
  "skills": [
    {
      "name": "gsd-execute-phase",
      "version": "1.0.0",
      "source": "builtin",
      "path": "~/.claude/skills/gsd-execute-phase/"
    },
    {
      "name": "gsd-my-custom-skill",
      "version": "0.2.0",
      "source": "external",
      "path": "/my-project/.claude/skills/gsd-my-custom-skill/"
    }
  ]
}
```

**Deliverables:**
- [ ] `gsd/assets/templates/SKILL.template.md`
- [ ] `gsd/sdk/models.py` — `SkillManifest` Pydantic model
- [ ] `gsd/sdk/commands/skill.py` — `skill-validate`, `skill-list`, `skill-add`
- [ ] Registry read/write in `gsd/sdk/core/registry.py`

---

## Phase 4 — Migration of Existing Project

**Goal:** Update existing skill files to replace bash commands with `gsd-sdk` equivalents.

### 4.1 — Audit Command

Before migrating, run:

```bash
gsd-sdk skill-audit ./existing-skills/
```

This scans all skill files and outputs a report of bash patterns that need replacing:

```
Audit Report — 3 skills scanned

gsd-execute-phase/SKILL.md
  Line 14: grep "status:" .planning/STATE.md   → replace with: gsd-sdk state-get status
  Line 22: sed -i 's/status: .*/status: done/' STATE.md  → replace with: gsd-sdk state-set status done
  Line 31: cat .planning/phases/*/PLAN.md      → replace with: gsd-sdk plan-list ${PHASE}

gsd-plan-phase/SKILL.md
  Line 8:  jq '.parallelization' config.json   → replace with: gsd-sdk config-get parallelization
```

### 4.2 — Migration Mapping

| Old bash pattern | New `gsd-sdk` command |
|---|---|
| `grep "status:" STATE.md` | `gsd-sdk state-get status` |
| `sed -i 's/phase:.*/phase: 2/' STATE.md` | `gsd-sdk state-set phase 2` |
| `ls .planning/phases/02-*/*-PLAN.md` | `gsd-sdk plan-list 2` |
| `jq '.key' .planning/config.json` | `gsd-sdk config-get key` |
| `git add X && git commit -m "msg"` | `gsd-sdk commit "msg" --files X` |
| Multiple reads to build context | `gsd-sdk init <phase>` |

### 4.3 — Validation After Migration

```bash
# Run full validation on migrated skills
gsd-sdk skill-list --validate

# Check no raw bash file patterns remain
gsd-sdk skill-audit ./migrated-skills/ --strict
```

**Deliverables:**
- [ ] `gsd-sdk skill-audit` command with pattern detection
- [ ] Migration guide document
- [ ] Updated existing skill files using `gsd-sdk` commands

---

## Pydantic Models (`gsd/sdk/models.py`)

```python
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class PlanModel(BaseModel):
    plan_id: str
    wave: int
    depends_on: list[str] = []
    files_modified: list[str] = []
    autonomous: bool = True
    requirements: list[str] = []
    has_summary: bool = False
    path: str

class StateModel(BaseModel):
    status: str
    phase: int
    last_activity: datetime
    current_focus: Optional[str] = None
    position: Optional[str] = None

class PhaseInitResult(BaseModel):
    phase_number: int
    phase_dir: str
    plan_count: int
    incomplete_count: int
    plans: list[PlanModel]
    state: StateModel
    config: dict

class SkillManifest(BaseModel):
    name: str
    version: str
    description: str
    sdk_commands: list[str] = []
    requires_planning_dir: bool = True
```

---

## `pyproject.toml`

```toml
[project]
name = "get-shit-done-py"
version = "0.1.0"
requires-python = ">=3.11"
description = "Context engineering CLI layer for LLM skill-based workflows"

dependencies = [
    "typer>=0.12",
    "python-frontmatter>=1.1",
    "pyyaml>=6.0",
    "gitpython>=3.1",
    "pydantic>=2.0",
    "rich>=13.0",
]

[project.scripts]
gsd-install = "gsd.installer:install_app"
gsd-sdk     = "gsd.sdk.cli:sdk_app"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
include = ["gsd/assets/**/*"]
```

---

## Implementation Order

```
Phase 1 — Core CLI Layer          (foundation, blocks everything else)
  └── 1.1 State commands
  └── 1.2 Plan commands
  └── 1.3 Git commands
  └── 1.4 Init query

Phase 2 — Installer               (delivery mechanism)
  └── 2.1 Runtime copy logic
  └── 2.2 External skills support

Phase 3 — Skill Template Contract (extensibility)
  └── 3.1 SKILL.template.md
  └── 3.2 Validation command
  └── 3.3 Registry

Phase 4 — Migration               (apply to existing project)
  └── 4.1 Audit command
  └── 4.2 Migrate existing skills
  └── 4.3 Validate migrated skills
```

---

## Success Criteria for v1.0

- [ ] `pip install get-shit-done-py` works and registers `gsd-install` and `gsd-sdk` on `$PATH`
- [ ] `gsd-install --runtime claude --scope local` copies all bundled skills correctly
- [ ] All existing skills migrated from bash to `gsd-sdk` commands pass `skill-audit --strict`
- [ ] `gsd-sdk init <phase>` returns valid JSON consumed by skills without error
- [ ] A new skill built to the template passes `gsd-sdk skill-validate` without modifying the package
- [ ] All state mutations are idempotent (re-running after crash resumes cleanly)
