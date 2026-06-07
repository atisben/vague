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
  - vague init
  - vague learnings-log
  - vague observations-log
requires_slug: true
requires_planning: false
allowed-tools:
  - Bash
  - Read
  - Write
  - AskUserQuestion
---

## Preamble

```bash
eval "$(vague context --shell)"
SESSION_ID="$$-$(date +%s)"
```

---

## Step 1: [First meaningful action]

[Instructions for the agent]

---

## Step 2: [Second action]

[Instructions for the agent]

---

## Handoff

> "What this skill produces and what to run next."
````

---

## Frontmatter Fields

| Field | Required | Notes |
|-------|----------|-------|
| `name` | Yes | Must match directory name. Used by analytics. |
| `version` | Yes | Semantic version (`1.0.0`). Bump on breaking changes. |
| `description` | Yes | Shown in the AI tool's skill picker. |
| `sdk_commands` | Yes | List of `vague` commands this skill calls. |
| `requires_slug` | Yes | `true` for most skills. `false` for global tools like `/ops-vault`. |
| `requires_planning` | Yes | `true` activates the optional planning layer (`state.md`, `roadmap.md`). |
| `allowed-tools` | Yes | List only tools the skill actually uses. |
| `benefits-from` | No | Array of skill names this one reads outputs from. |

---

## Preamble Convention

Every skill must start by loading project context. Use `vague context --shell`,
which emits eval-able shell variables in a single process (no `python3` JSON
parsing):

```bash
eval "$(vague context --shell)"   # sets SLUG, BRANCH, PROACTIVE, TELEMETRY
SESSION_ID="$$-$(date +%s)"
```

When a skill also needs the surfaced `learnings` array, call `vague init` (or
`vague context` without `--shell`), which returns the full JSON object:

```json
{
  "slug": "owner-repo",
  "branch": "feat/my-feature",
  "proactive": true,
  "telemetry": "local",
  "learnings": [
    {
      "skill": "review", "type": "pitfall", "key": "n-plus-one",
      "insight": "Always eager-load associations on list queries.",
      "confidence": 8, "source": "observed"
    }
  ]
}
```

The `learnings` array contains the top 3 entries by confidence if more than 5 exist, otherwise all entries. **The agent reads this before doing any work** — this is how cross-session and cross-agent memory reaches the LLM context.

`vague context` and `vague init` never fail: missing config returns defaults, missing git remote falls back to `basename $PWD`.

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

## Logging Learnings

When your skill discovers a non-obvious insight about the codebase:

```bash
vague learnings-log '{
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

**Types:** `pattern` · `pitfall` · `preference` · `architecture` · `tool` · `operational`
**Confidence:** 7–9 for observed patterns, 4–6 for inferences, 10 for user-stated facts.

Learnings are written to `~/.vague/projects/{slug}/learnings.md` and surfaced automatically by `vague init` in future sessions — including sessions by different agents and different AI tools.

---

## Logging Observations

When your skill encounters friction, gaps, or improvement opportunities — either in itself or in another skill — log an observation for the `/ops-meta` skill to review later:

```bash
vague observations-log '{
  "skill": "target-skill-name",
  "type": "improvement",
  "issue": "What happened or was observed.",
  "suggestion": "Concrete change proposal.",
  "principle": "Generalisable takeaway.",
  "source_skill": "my-skill"
}'
```

**Types:** `improvement` (existing skill) · `new-skill` (gap suggesting a new skill) · `simplification` (remove dead weight) · `cross-cutting` (applies to all skills) · `correction` (the user had to manually ask for a step the skill should have done — the highest-signal observations)

For new skill candidates, use `"skill": "new:working-name"` as the target.

Observations are written to `~/.vague/projects/{slug}/observations.md` and reviewed by running `/ops-meta`.

Every skill should include a standard **Observation Protocol** section before its Handoff. See the template below or any existing skill for the pattern.

---

## Timeline Events

Fire timeline events so `/ops-retro` can track skill usage:

```bash
# At skill end (do this explicitly — vague init does NOT auto-log):
vague timeline-log "{\"skill\":\"my-skill\",\"event\":\"completed\",\"branch\":\"$BRANCH\",\"outcome\":\"success\",\"session\":\"$SESSION_ID\"}"
```

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

> "Design saved. Next:
> - `/design-html` to turn this into production HTML
> - `/design-review` to audit visual quality on an existing implementation"
```

---

## Validating Your Skill

```bash
vague skill-validate ./my-skill/     # checks required frontmatter fields
vague skill-audit ./my-skill/        # scans for legacy bs-* bash patterns
```

A skill passes validation when:
- All required frontmatter fields are present (`name`, `version`, `description`, `sdk_commands`, `requires_slug`, `requires_planning`)
- No legacy `bs-*` or `source _preamble.sh` patterns remain

---

## Testing a Skill

1. Create a test git repo: `mkdir /tmp/test-vague && cd /tmp/test-vague && git init`
2. Run `vague-install` to copy bundled skills to the right directory
3. Open your AI tool in the test repo
4. Type the slash command and verify behavior
