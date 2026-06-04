---
name: develop
version: 1.0.0
description: |
  Orchestrated development. Breaks a task into phases and delegates each to a
  fresh-context subagent. The orchestrator stays lean (~15% context budget),
  workers get full context for their specific job.
  Trigger: "develop this", "build this feature", "implement this", "orchestrate".
sdk_commands:
  - vague init
  - vague timeline-log
  - vague learnings-log
  - vague observations-log
requires_slug: true
requires_planning: false
allowed-tools:
  - Bash
  - Read
  - Agent
  - AskUserQuestion
benefits-from:
  - office-hours
  - plan-ceo-review
  - plan-eng-review
---

## Preamble

```bash
eval "$(vague context --shell)"
SESSION_ID="$$-$(date +%s)"
```

**Proactive invocation:** When the user describes a multi-step feature or implementation task that would benefit from structured delegation rather than ad-hoc coding.

---

## Core Principle: Orchestrator ≠ Worker

**You are the orchestrator.** You do NOT write code, read large files, or run tests yourself.

Your job:
1. Understand the task and gather just enough context to plan
2. Break the work into independent phases
3. Brief each subagent with everything it needs (context, constraints, file paths, learnings)
4. Collect results, verify they connect, coordinate handoffs
5. Log learnings and observations

**Each `Agent()` call spawns a fresh context.** The subagent sees ONLY what you put in the `prompt` parameter. This means:
- Subagents get a full, clean context budget for their specific job
- You must include all relevant context in the brief (file paths, conventions, constraints, learnings)
- Two subagents cannot see each other's work unless you pass results between them

**Budget rule:** Keep your own context under ~15%. If you're tempted to read a large file or codebase yourself, delegate it to a subagent instead.

---

## Step 1: Gather Context (stay light)

Read only what you need to plan — do NOT deep-dive into code:

```bash
VAGUE_HOME="${VAGUE_HOME:-$HOME/.vague}"
# Current branch
BRANCH=$(git branch --show-current 2>/dev/null || echo "unknown")
echo "BRANCH: $BRANCH"
# Repo structure (top-level only)
ls -1
# Check for existing plans
PLAN_FILE=$(ls -t "$VAGUE_HOME/projects/$SLUG/designs/"*eng*.md "$VAGUE_HOME/projects/$SLUG/designs/"*.md 2>/dev/null | head -1)
echo "PLAN_FILE: ${PLAN_FILE:-NONE}"
# Check for CLAUDE.md project conventions
[ -f CLAUDE.md ] && head -40 CLAUDE.md || true
```

If `$PLAN_FILE` exists, read it — it's your implementation spec.

Ask the user (if not already clear):
> "What should I build? Describe the feature or point me to a plan."

---

## Step 2: Break Into Phases

Decompose the task into 2-5 phases. Each phase must be:
- **Independent enough** to run in a fresh context
- **Small enough** for one subagent to complete well
- **Clearly scoped** — explicit inputs, outputs, and success criteria

Present the plan to the user:

```
PHASE 1: [name] — [what the subagent will do]
  Inputs:  [files/context it needs]
  Outputs: [files it will create/modify]
  
PHASE 2: [name] — [what the subagent will do]  
  Inputs:  [files/context it needs, including Phase 1 outputs]
  Outputs: [files it will create/modify]

...
```

Ask via AskUserQuestion:
> "Here's my plan. Should I proceed, or adjust?"

**Parallelism:** If phases are independent (no output dependencies), note them for parallel execution. If Phase 2 needs Phase 1's output, they must be sequential.

---

## Step 3: Brief and Delegate

For each phase, spawn an `Agent()` with a self-contained brief.

### Brief Template

Every agent brief MUST include:

1. **Goal** — one sentence: what to accomplish
2. **Context** — project conventions, relevant learnings, constraints
3. **Specific files** — exact paths to read/modify (the agent can't discover these efficiently without guidance)
4. **Success criteria** — how to know the work is done
5. **Boundaries** — what NOT to do (don't refactor unrelated code, don't add features beyond scope)

### Example Delegation

```
Agent({
  description: "Implement user auth module",
  prompt: "## Goal
Implement email/password authentication for a Python FastAPI app.

## Context
- Project uses FastAPI + SQLAlchemy + Alembic
- Auth should use bcrypt for password hashing, JWT for tokens  
- Existing user model is in src/models/user.py
- Test conventions: pytest, tests live in tests/ mirroring src/ structure
- CLAUDE.md says: use named parameters in function calls, no type: ignore

## Learnings from prior sessions
- 'Always eager-load associations on list queries' (confidence: 8)

## Files to work with
- src/models/user.py — add password_hash field
- src/api/auth.py — create this file: login, register, refresh endpoints
- src/core/security.py — create: hash_password, verify_password, create_token
- tests/api/test_auth.py — create: test register, login, invalid creds, expired token

## Success criteria
- All 4 test cases pass
- Endpoints return proper HTTP status codes
- Passwords are never stored in plain text

## Boundaries
- Don't modify existing endpoints
- Don't add email verification (out of scope)
- Don't install packages without listing them"
})
```

### Parallel Delegation

If phases are independent, spawn them in a single message:

```
Agent({ description: "Phase 1: ...", prompt: "..." })
Agent({ description: "Phase 2: ...", prompt: "..." })
```

This runs them in parallel, each in its own fresh context.

---

## Step 4: Verify Connections

After each phase completes, check that the outputs connect:

- Does Phase 2's code import what Phase 1 created?
- Do the interfaces match (function signatures, return types, API contracts)?
- Are there gaps between what was planned and what was built?

**If there are gaps:** spawn a focused fix agent to bridge them. Do NOT try to fix it yourself — stay lean.

```
Agent({
  description: "Fix integration gap",
  prompt: "Phase 1 created src/core/security.py with create_token(user_id: int) -> str.
Phase 2's src/api/auth.py calls create_token(user=user_obj).
Fix the call site in auth.py to pass user.id instead of the user object.
File: src/api/auth.py, line ~45."
})
```

---

## Step 5: Final Verification

Spawn a verification agent that checks the combined work:

```
Agent({
  description: "Verify implementation",
  prompt: "## Goal
Verify that the following feature works end-to-end: [feature description].

## What was built
[Summary of what each phase produced]

## Checks
1. Run the full test suite — report pass/fail
2. Check that all new files are properly imported/wired
3. Look for obvious issues: missing error handling at API boundaries, hardcoded values, debug code
4. Verify the feature actually works (not just that tests pass)

## Do NOT fix anything — only report findings."
})
```

If the verification agent reports issues, spawn fix agents for each issue. Then re-verify.

---

## Step 6: Log and Handoff

```bash
vague timeline-log "{\"skill\":\"develop\",\"event\":\"completed\",\"branch\":\"$BRANCH\",\"outcome\":\"success\",\"session\":\"$SESSION_ID\"}"
```

Log any learnings:
```bash
vague learnings-log '{"skill":"develop","type":"pattern","key":"SHORT_KEY","insight":"INSIGHT","confidence":8,"source":"observed"}'
```

---

## Deviation Rules

During delegation, subagents may encounter unexpected situations. Instruct them to follow these rules:

| Rule | Action | Example |
|------|--------|---------|
| R1: Bug in existing code blocks progress | Fix inline, note in output | Broken import in file you need to modify |
| R2: Missing critical correctness code | Add it, note in output | No input validation on a public endpoint |
| R3: Build/test blocker | Fix it, note in output | Missing dependency, broken config |
| R4: Architectural decision needed | **STOP and return to orchestrator** | Needs a new DB table, different library, schema change |

**R4 overrides R1-R3.** When a subagent returns with an R4 stop, present the decision to the user via AskUserQuestion before re-delegating.

Include these rules in every agent brief:
```
## Deviation rules
- Fix bugs, missing validation, and build blockers inline (note what you fixed)
- STOP and report back (don't fix) if you hit an architectural decision: new tables, schema changes, library switches, or major design choices
```

---

## Observation Protocol

Throughout this skill's execution, watch for:
- Steps that produce wrong or suboptimal output
- Missing rules the user has to correct
- Workflow inefficiencies or unnecessary steps
- Gaps where a different skill would help
- **User corrections** — any time the user tells you to do something the skill should have done automatically

When you notice any of these, log an observation:

```bash
vague observations-log '{"skill":"develop","type":"improvement","issue":"WHAT_HAPPENED","suggestion":"CONCRETE_CHANGE","principle":"GENERALISABLE_TAKEAWAY","source_skill":"develop"}'
```

**User correction detection:** If the user has to explicitly ask you to perform a step that should be part of this skill's workflow, log it immediately as a `type: correction` observation.

```bash
vague observations-log '{"skill":"develop","type":"correction","issue":"User had to manually ask: WHAT_THEY_SAID","suggestion":"Add this as an explicit step in the skill","principle":"GENERALISABLE_TAKEAWAY","source_skill":"develop"}'
```

Log silently — do not interrupt the user's workflow to announce observations.

---

## Handoff

> "Feature implemented and verified. Next: `/review` for pre-landing code review, or `/ship` to create a PR."
