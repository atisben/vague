---
name: meta
version: 1.0.0
description: |
  Meta-skill for improving all other skills. Reviews observations logged during
  normal skill usage, applies improvements to existing skills, creates new skills,
  and curates the memory ledger. Trigger: "improve skills", "meta review",
  "skill improvement", "what needs fixing in our skills", "review observations".
sdk_commands:
  - vague context
  - vague skill-validate
  - vague skill-list
  - vague memory-log
  - vague memory-search
requires_slug: true
allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - AskUserQuestion
benefits-from:
  - dev-ship
  - dev-investigate
  - plan-eng
  - plan-ideation
  - diagram
  - retro
  - vault
---

## Preamble

```bash
eval "$(vague context --shell --skill meta)"
VAGUE_HOME="${VAGUE_HOME:-$HOME/.vague}"
```

**Proactive invocation:** Suggest when the user discusses skill quality, mentions friction with a skill, or says something like "that skill could be better". If PROACTIVE is "False", say: "I think /meta might help — want me to run it?"

---

## Step 0: Load Context

Every project shares one global store, so this reads the observations logged from every repo:

```bash
# All active observations (they live in the global scope, no words lists them all)
vague memory-search --kind observation

# Every active memory of every scope, newest first, for Step 4
vague memory-search --scope all

# List all skills
vague skill-list
```

When `--scope all` prints more than you can read in one pass, read one scope at a time with `vague memory-search --scope <project>` or `vague memory-search --scope global`.

Each line prints as `global/<key>  [<skill>]  <issue → suggestion>`, where `<skill>` is the skill the observation is about. Actioned and declined observations no longer appear.

If there are no open observations and Step 4 finds nothing to curate, report:

> "No open observations. All skills are current. If you want to log an observation manually, describe what you noticed and I'll record it."

Then offer to:
- **Log a new observation** based on something the user describes
- **Audit skills** for simplification opportunities

If there are open observations, proceed to Step 1.

---

## Step 1: Triage Observations

Group the observations by the `[<skill>]` tag on each line. To list one skill's observations, search for its name: `vague memory-search --kind observation <skill>`. Keys starting with `new-skill-` are new-skill candidates. Present a summary:

```
## Open Observations

### dev-ship (2 observations)
- ship-no-test-step: Missing test step before commit → add a test step
- ship-changelog-dates: Changelog uses mixed date formats → use ISO dates

### dev-investigate (1 observation)
- investigate-no-bisect: No git bisect suggestion → suggest bisect for regressions

### New skill candidates (1)
- new-skill-dependency-audit: Recurring need to check outdated dependencies
```

Ask the user via AskUserQuestion:

> "Which observations should I apply? You can approve all, select specific ones, or decline any."

Options:
- A) Apply all observations
- B) Let me pick specific ones
- C) Show me the details first

---

## Step 2: Apply Improvements to Existing Skills

For each approved observation targeting an existing skill:

1. **Read the target SKILL.md** from `vague/assets/skills/{name}/SKILL.md` (when in the vague repo) or `~/.claude/skills/{name}/SKILL.md` (otherwise)

2. **Integrate the improvement** into the appropriate section of the skill:
   - New rule → add to the relevant step or create a subsection
   - Missing step → insert at the logical position in the workflow
   - Clarification → edit the existing text
   - Anti-pattern → add to an existing anti-patterns list, or create one
   - Simplification → remove the identified dead weight

3. **Preserve the skill's existing structure** — make the change feel native, not bolted on

4. **Write the updated SKILL.md** back to the same location

5. **Mark the observation as actioned:**
   ```bash
   vague memory-log <key> --status actioned
   ```
   Mark a declined one with `--status declined`.

After each skill edit, run validation:
```bash
vague skill-validate vague/assets/skills/{name}/
```

---

## Step 3: Handle New Skill Candidates

For observations whose key starts with `new-skill-`:

1. **Present the proposal** to the user with scope, purpose, and suggested trigger phrases

2. If approved, **scaffold the new skill:**
   ```bash
   mkdir -p vague/assets/skills/{name}/
   ```

3. **Write SKILL.md** following the standard template from `docs/skill-authoring.md`:
   - Frontmatter with all required fields
   - Preamble with `eval "$(vague context --shell --skill <name>)"`
   - Step-by-step instructions
   - Observation Protocol line
   - Handoff section

4. **Validate the new skill:**
   ```bash
   vague skill-validate vague/assets/skills/{name}/
   ```

5. Mark the observation as actioned (`--status actioned`)

---

## Step 4: Curate Memories

Read the `vague memory-search --scope all` output from Step 0 yourself and look for three things. Each line prints as `scope/key  [skill]  text  (files: …)`, without the parts that are empty. Nothing is deleted: every change is a new line in the ledger.

| You find | Action |
|---|---|
| A duplicate: the same fact under two keys in one project | Rewrite one: `vague memory-log <keep-key> "<merged text>"`. Forget the other: `vague memory-log <drop-key> --status forgotten` |
| A cross-project fact: the same fact in two projects | Re-log it: `vague memory-log <key> "<text>" --global`. Forget each original with `--status forgotten` |
| A dead path: a memory whose `files` no longer exist in its repo | Re-log with corrected `--files`, or forget it |

A memory with files ends with `(files: a, b)` in the search output. Check each path in that project's repo.

Run each command from the repo of the memory's scope, or add `--global` for a `global/` memory. Ask the user before you forget anything.

A cross-cutting principle the user names during the session belongs in `vague/assets/claude/guidelines.md`, the block every runtime gets. Apply it to the skills it affects, and note which ones changed.

---

## Step 5: Pre-Flight Verification

Before finishing, re-read every modified SKILL.md and verify:

1. **Structure intact** — frontmatter fields present, preamble is `eval "$(vague context --shell --skill <name>)"`, handoff section exists
2. **Observation Protocol present** — every skill keeps its one-line `--about <skill>` feedback section
3. **Changes are native** — improvements read as if they were always part of the skill, not appended
4. **No regressions** — no existing rules or steps were accidentally removed
5. **Validation passes:**
   ```bash
   vague skill-validate vague/assets/skills/{name}/
   ```

Fix any issues found.

---

## Step 6: Summary and Handoff

Present a summary:

```
## /meta Review Complete

### Skills Updated
- **dev-ship**: Added test verification step before commit (ship-no-test-step)
- **dev-investigate**: Added git bisect suggestion for regression bugs (investigate-no-bisect)

### New Skills Created
- **dependency-audit**: Checks for outdated/vulnerable dependencies

### Observations Actioned: ship-no-test-step, investigate-no-bisect, new-skill-dependency-audit
### Observations Declined: ship-changelog-dates (user prefers the current format)

### Memories Curated
- Merged: tests-need-docker ← docker-pytest (forgotten)
- Promoted to global: concat-empty-list
```

Log a learning only for a fact the curation itself revealed, such as a skill convention that keeps drifting.

> "Skills updated. Next steps:
> - Run `vague install` to deploy changes to your LLM runtime
> - Review changes via `git diff` before committing
> - Run `/dev-ship` to commit and create a PR"

---

## Observation Protocol

Log feedback about this skill with `vague memory-log <key> "<issue → suggestion>" --about meta` (see the Memory guideline).
