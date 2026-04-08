# Skill Authoring Guide

A bastack skill is a Markdown file at `skills/{name}/SKILL.md` that Claude Code reads and executes as a slash command.

---

## Minimal Skill Template

````markdown
---
name: my-skill
version: 1.0.0
description: |
  One paragraph. What it does, when to use it, proactive trigger phrases.
  Include "(bastack)" at the end so it's identifiable.
allowed-tools:
  - Bash
  - Read
  - Write
  - AskUserQuestion
---

## Preamble

```bash
export BS_SKILL_NAME="my-skill"
source "$(dirname "$0")/../_preamble.sh"
```

---

## Step 1: [First meaningful action]

[Instructions for Claude]

---

## Step 2: [Second action]

[Instructions for Claude]

---

## Handoff

> "What this skill produces and what to run next."
````

---

## Frontmatter Fields

| Field | Required | Notes |
|-------|----------|-------|
| `name` | Yes | Must match directory name. Used by `bs-analytics`. |
| `version` | Yes | Semantic version (`1.0.0`). Bump on breaking changes. |
| `description` | Yes | Shown in Claude Code's skill picker. |
| `allowed-tools` | Yes | List only tools the skill actually uses. |
| `benefits-from` | No | Array of skill names this one reads outputs from. |

---

## Preamble Convention

Every skill must start with:

```bash
export BS_SKILL_NAME="my-skill"
source "$(dirname "$0")/../_preamble.sh"
```

This gives you:
- `$SLUG` — sanitized project slug
- `$BRANCH` — current git branch
- `$PROACTIVE` — "true" | "false"
- `$TELEMETRY` — "local" | "off"
- `$SESSION_ID` — unique session ID

---

## Proactive Behavior

At the top of your skill's instructions, declare when it should be auto-invoked:

```markdown
**Proactive invocation:** Suggest when the user [describes situation].
```

Check `$PROACTIVE` before auto-invoking:
```
If PROACTIVE is "false", only run when the user explicitly types the slash command.
If you would have auto-invoked, say: "I think /my-skill might help — want me to run it?"
```

---

## Logging Learnings

When your skill discovers a non-obvious insight about the codebase:

```bash
~/.bastack/bin/bs-learnings-log '{
  "skill": "my-skill",
  "type": "pitfall",
  "key": "short-kebab-key",
  "insight": "One sentence explaining what was learned and why it matters.",
  "confidence": 8,
  "source": "observed",
  "files": ["path/to/relevant/file"]
}'
```

**Only log genuine discoveries.** Skip obvious things. A good test: would this save time in a future session?

---

## Timeline Events

Fire timeline events so `/retro` can track skill usage:

```bash
# At skill start (done automatically by _preamble.sh):
~/.bastack/bin/bs-timeline-log '{"skill":"my-skill","event":"started","branch":"'$BRANCH'","session":"'$SESSION_ID'"}'

# At skill end (you must do this):
~/.bastack/bin/bs-timeline-log '{"skill":"my-skill","event":"completed","branch":"'$BRANCH'","outcome":"success","session":"'$SESSION_ID'"}'
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

> "Design saved. Next:
> - `/design-html` to turn this into production HTML
> - `/design-review` to audit visual quality on an existing implementation"
```

---

## Testing a Skill

1. Create a test git repo: `mkdir /tmp/test-bastack && cd /tmp/test-bastack && git init`
2. Run `install.sh` to set up symlinks
3. Open Claude Code in the test repo
4. Type the slash command and verify behavior
