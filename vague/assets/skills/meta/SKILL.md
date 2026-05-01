---
name: meta
version: 1.0.0
description: |
  Meta-skill for improving all other skills. Reviews observations logged during
  normal skill usage, applies improvements to existing skills, creates new skills,
  and enforces cross-cutting principles. Trigger: "improve skills", "meta review",
  "skill improvement", "what needs fixing in our skills", "review observations".
sdk_commands:
  - vague init
  - vague observations-list
  - vague observations-update
  - vague observations-log
  - vague learnings-log
  - vague skill-validate
  - vague skill-list
requires_slug: true
requires_planning: false
allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - AskUserQuestion
benefits-from:
  - ship
  - review
  - investigate
  - plan-eng-review
  - plan-ceo-review
  - office-hours
  - design-consultation
  - design-html
  - design-review
  - design-shotgun
  - retro
  - learn
  - vault
---

## Preamble

```bash
CONTEXT=$(vague init)
SLUG=$(echo "$CONTEXT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['slug'])")
BRANCH=$(echo "$CONTEXT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['branch'])")
PROACTIVE=$(echo "$CONTEXT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['proactive'])")
VAGUE_HOME="${VAGUE_HOME:-$HOME/.vague}"
```

**Proactive invocation:** Suggest when the user discusses skill quality, mentions friction with a skill, or says something like "that skill could be better". If PROACTIVE is "False", say: "I think /meta might help — want me to run it?"

---

## Step 0: Load Context

```bash
# Load open observations
vague observations-list --status open

# Load principles
cat "$VAGUE_HOME/projects/$SLUG/principles.md" 2>/dev/null || echo "NO_PRINCIPLES"

# List all skills
vague skill-list
```

If there are no open observations and no pending principle propagation, report:

> "No open observations. All skills are current. If you want to log an observation manually, describe what you noticed and I'll record it."

Then offer to:
- **Log a new observation** based on something the user describes
- **Review principles** to check if any need updating
- **Audit skills** for simplification opportunities

If there are open observations, proceed to Step 1.

---

## Step 1: Triage Observations

Group all OPEN observations by target skill. Present a summary:

```
## Open Observations

### ship (3 observations)
- #12: Missing test step before commit — "Ship skill doesn't verify tests pass"
- #15: Changelog format inconsistent — "Uses different date formats"
- #18: No branch protection check — "Pushes without checking CI status"

### investigate (1 observation)
- #14: No git bisect suggestion — "Could suggest bisect for regression bugs"

### New skill candidates (1)
- #16: "new:dependency-audit" — "Recurring need to check outdated dependencies"
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

5. **Mark the observation as ACTIONED:**
   ```bash
   vague observations-update <id> actioned
   ```

After each skill edit, run validation:
```bash
vague skill-validate vague/assets/skills/{name}/
```

---

## Step 3: Handle New Skill Candidates

For observations with `skill: "new:working-name"`:

1. **Present the proposal** to the user with scope, purpose, and suggested trigger phrases

2. If approved, **scaffold the new skill:**
   ```bash
   mkdir -p vague/assets/skills/{name}/
   ```

3. **Write SKILL.md** following the standard template from `docs/skill-authoring.md`:
   - Frontmatter with all required fields
   - Preamble with `vague init`
   - Step-by-step instructions
   - Observation protocol section
   - Handoff section

4. **Validate the new skill:**
   ```bash
   vague skill-validate vague/assets/skills/{name}/
   ```

5. Mark the observation as ACTIONED

---

## Step 4: Propagate Cross-Cutting Principles

Read the principles file:
```bash
cat "$VAGUE_HOME/projects/$SLUG/principles.md" 2>/dev/null
```

For each active principle:
1. Read every skill's SKILL.md
2. Check if the skill already complies with the principle
3. If not, apply the principle and note which skills were updated

If the user identifies a new cross-cutting principle during this session, add it:
```bash
# The skill will write to principles.md directly via the frontmatter pattern
```

---

## Step 5: Pre-Flight Verification

Before finishing, re-read every modified SKILL.md and verify:

1. **Structure intact** — frontmatter fields present, preamble calls `vague init`, handoff section exists
2. **Observation protocol present** — every skill should have the standard observation protocol section
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
- **ship**: Added test verification step before commit (#12), fixed changelog date format (#15)
- **investigate**: Added git bisect suggestion for regression bugs (#14)

### New Skills Created
- **dependency-audit**: Checks for outdated/vulnerable dependencies

### Observations Actioned: #12, #14, #15, #16
### Observations Declined: #18 (user decided branch protection is out of scope)

### Principles Propagated
- "Pre-flight verification" applied to: design-html, design-shotgun
```

Log a learning if any non-obvious insight emerged:
```bash
vague learnings-log '{"skill":"meta","type":"pattern","key":"SHORT_KEY","insight":"INSIGHT","confidence":8,"source":"observed"}'
```

> "Skills updated. Next steps:
> - Run `vague install` to deploy changes to your LLM runtime
> - Review changes via `git diff` before committing
> - Run `/ship` to commit and create a PR"

---

## Observation Protocol

Throughout this skill's execution, watch for:
- Steps that produce wrong or suboptimal output
- Missing rules the user has to correct
- Workflow inefficiencies or unnecessary steps
- Gaps where a different skill would help

When you notice any of these, log an observation:

```bash
vague observations-log '{"skill":"meta","type":"improvement","issue":"WHAT_HAPPENED","suggestion":"CONCRETE_CHANGE","principle":"GENERALISABLE_TAKEAWAY","source_skill":"meta"}'
```

Log silently — do not interrupt the user's workflow to announce observations.
