# Skill Authoring Guide

A vague skill is a Markdown file at `{skill-dir}/{name}/SKILL.md` that an AI tool reads and executes as a slash command. Skills interact with the filesystem exclusively through `vague` CLI commands — no raw file I/O, no bash state scripts.

---

## Minimal Skill Template

````markdown
---
name: my-skill
version: 1.0.0
description: |
  One paragraph. What it does, when to use it, proactive trigger phrases.
sdk_commands:
  - vague context
  - vague memory-log
requires_slug: true
allowed-tools:
  - Bash
  - Read
  - Write
  - AskUserQuestion
---

## Preamble

```bash
eval "$(vague context --shell --skill my-skill)"
```

---

## Step 1: [First meaningful action]

[Instructions for the agent]

---

## Step 2: [Second action]

[Instructions for the agent]

---

## Observation Protocol

Log feedback about this skill with `vague memory-log <key> "<issue → suggestion>" --about my-skill` (see the Memory guideline).

---

## Handoff

> "What this skill produces and what to run next."
````

---

## Frontmatter Fields

| Field | Required | Notes |
|-------|----------|-------|
| `name` | Yes | Must match directory name. |
| `version` | Yes | Semantic version (`1.0.0`). Bump on breaking changes. |
| `description` | Yes | Shown in the AI tool's skill picker. |
| `sdk_commands` | Yes | List of `vague` commands this skill calls. |
| `requires_slug` | Yes | `true` for most skills. `false` for global tools like `/vault`. |
| `allowed-tools` | Yes | List only tools the skill actually uses. |
| `benefits-from` | No | Array of skill names this one reads outputs from. |

---

## Preamble Convention

Every skill starts by loading project context in one process:

```bash
eval "$(vague context --shell --skill my-skill)"   # sets SLUG, BRANCH, PROACTIVE, TELEMETRY
```

The command also prints a MEMORY block, at most 1,500 tokens. `eval` runs a `cat` heredoc, so the block lands in the tool output, where the agent reads it before doing any work:

```
vague memory · scope owner-repo · 4 memories
Scratch (shared by this scope's agents, last 7 days):
- [docs-rewrite-in-progress] Agent B is rewriting docs/; leave them alone until it lands.
Memories (most relevant first):
- [tests-need-docker] Tests and mypy run only inside the train container; the host .venv has no pytest.
- [global/verify-subagent-claims] Re-run tests yourself after subagents report success.
- [n-plus-one] Always eager-load associations on list queries.
```

The second line of the block is a logging hint, `To log a learning: vague memory-log <key> "<fact>" --skill <name> …`, built by `logging_hint` in `vague/sdk/core/memory.py`. The block holds recent scratch notes, then full lines for this scope plus `global` (global takes at most a third). When the budget runs out, it switches to key-only index lines and ends with a `vague memory-search` pointer. Ranking is deterministic: memories whose `files` overlap the uncommitted changes first, then memories written by the same `--skill`, then the newest. Observations never load here.

`vague context` never fails: missing config returns defaults, a missing git remote falls back to the folder name, and a broken ledger drops the block.

---

## Proactive Behavior

At the top of your skill's instructions, declare when it should be auto-invoked:

```markdown
**Proactive invocation:** Suggest when the user [describes situation].
```

Check `$PROACTIVE` before auto-invoking:
```
If PROACTIVE is "False", only run when the user explicitly types the slash command.
If you would have auto-invoked, say: "I think /my-skill might help — want me to run it?"
```

---

## Logging Memories

Skills write memory only through `vague memory-log`. Two shared sources already teach the command: the Memory section of `vague/assets/claude/guidelines.md` and the hint line in the preamble block. A skill therefore never repeats the command. Add a one-line step only when the skill has its own trigger, such as "log a pitfall that shipping hit". A skill that spawns subagents must pass memory in each brief, because a subagent never runs the preamble (see `dev-develop` Step 3).

| Need | Flag |
|---|---|
| The fact holds in every repo | `--global` |
| Feedback about a skill, read by `/meta` | `--about <skill>` (always global) |
| A working note for other agents on this project, hidden after 7 days | `--scratch` |
| Correct a fact | Re-use its key |
| Retire a memory | `--status forgotten`, or `actioned` / `declined` for an observation |

**Only log genuine discoveries.** A good test: would this save time in a future session?

Every skill ends with a one-line **Observation Protocol** section before its Handoff. It points at `--about <skill>` and lists only the skill-specific things worth watching for.

Skills do not log their own start or end. The `vague log-event` hook records each skill start in `~/.vague/events/`, and `/retro` reads it from there.

---

## Config

```bash
vague config-get proactive      # "true" or "false"
vague config-set proactive false
vague config-get telemetry      # "local" or "off"
```

---

## AskUserQuestion Pattern

Always use `AskUserQuestion` for decisions (not free-form chat):

```
RECOMMENDATION: Choose A because [one-line reason].

A) [action A]
B) [action B]
C) [action C]
```

Rules:
- One issue = one AskUserQuestion
- Always state your recommendation and why
- If the fix is obvious and unambiguous, apply it and state what you did — don't waste a question

---

## Handoff Pattern

End every skill with:

```markdown
## Handoff

> "[What was produced]. Next: `/next-skill` to [what it does]."
```

If multiple next steps are appropriate:
```markdown
## Handoff

> "Engineering plan saved. Next:
> - `/dev-ship` to implement it
> - `/diagram` to draw the architecture overview"
```

---

## Validating Your Skill

```bash
vague skill-validate ./my-skill/     # checks required frontmatter fields
vague skill-audit ./my-skill/        # scans for legacy bs-* bash patterns
```

A skill passes validation when:
- All required frontmatter fields are present (`name`, `version`, `description`, `sdk_commands`, `requires_slug`)
- No legacy `bs-*` or `source _preamble.sh` patterns remain

---

## Testing a Skill

1. Create a test git repo: `mkdir /tmp/test-vague && cd /tmp/test-vague && git init`
2. Run `vague install` to link bundled skills to the right directory
3. Open your AI tool in the test repo
4. Type the slash command and verify behavior
