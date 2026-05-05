---
name: review
version: 1.0.0
description: |
  Pre-landing code review. Analyzes the diff for SQL safety, LLM trust boundary
  violations, conditional side effects, race conditions, and other structural issues.
  Fix-first: auto-fixes mechanical issues, asks about judgment calls.
  Trigger: "review this PR", "code review", "pre-landing review", "check my diff".
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
  - Edit
  - Write
  - AskUserQuestion
---

## Preamble

```bash
CONTEXT=$(vague init)
SLUG=$(echo "$CONTEXT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['slug'])")
BRANCH=$(echo "$CONTEXT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['branch'])")
PROACTIVE=$(echo "$CONTEXT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['proactive'])")
SESSION_ID="$$-$(date +%s)"
```

**Proactive invocation:** Suggest this skill when the user is about to merge or land code changes.

---

## Step 1: Get the Diff

```bash
BASE=$(git remote show origin 2>/dev/null | grep 'HEAD branch' | awk '{print $NF}' || echo "main")
echo "BASE: $BASE"
git diff origin/$BASE --stat
git diff origin/$BASE
```

Read the **full diff** before commenting. Do not flag issues already addressed in the diff.

---

## Step 2: Check for Pre-existing Failures

```bash
# Run tests (use project's test command from CLAUDE.md or auto-detection)
```

If tests fail, determine: pre-existing or introduced by this branch?
- **Pre-existing**: note it, continue
- **Introduced**: STOP. This blocks landing.

---

## Fix-First Rule

**Every finding gets action — not just critical ones.**

- **AUTO-FIX**: mechanical, unambiguous, low-risk changes → apply directly
- **ASK**: judgment calls, design decisions, trade-offs → present via AskUserQuestion

Apply all AUTO-FIX items first. Then batch ASK items into one question (max).

---

## Section 1: SQL Safety

- Raw string interpolation in queries (SQL injection vector)
- Missing `WHERE` clauses on `UPDATE` or `DELETE`
- N+1 query patterns
- Missing transactions on multi-step writes
- Unbounded queries (no LIMIT on user-controlled input)

---

## Section 2: LLM Trust Boundaries

If the codebase uses LLMs:
- LLM output used directly in SQL queries without sanitization
- LLM output rendered as HTML without escaping (XSS)
- LLM output used in shell commands (command injection)
- Prompt contents logged with PII
- User-controlled input injected into system prompts (prompt injection)

---

## Section 3: Authorization & Data Access

- Can user A access user B's data through this change?
- New endpoints missing authentication checks
- Privilege escalation paths (user → admin)
- Direct object references without ownership validation

---

## Section 4: Error Handling & Failure Modes

- Errors swallowed silently (`rescue nil`, empty catch blocks)
- Missing error propagation — caller doesn't know something failed
- External API calls with no timeout
- External API calls with no retry or circuit breaker
- Partial writes that leave data in inconsistent state

---

## Section 5: Race Conditions & Concurrency

- Read-modify-write patterns without locking
- Status transitions without atomic checks (e.g., double-spend)
- Background jobs that assume data still exists when they run
- Cache invalidation that can leave stale data for too long

---

## Section 6: Input Validation

- User-controlled input used without validation
- File uploads without type/size checks
- Numeric inputs without bounds checking
- Missing required field validation

---

## Section 7: Test Coverage

- New code paths with no test
- Edge cases (nil, empty, error) not tested
- Tests that test implementation rather than behavior
- Tests that will be brittle (time-dependent, order-dependent)

---

## Section 8: Documentation Staleness

- README, CLAUDE.md, or other docs that describe behavior changed by this diff
- Flag as informational: "Consider updating [file] — it describes [feature] which changed."

---

## Present Findings

```
PRE-LANDING REVIEW: N issues (X critical, Y informational)
────────────────────────────────────────────────────────
[AUTO-FIXED] file:line — problem → what was done
[CRITICAL]   file:line — problem
[INFO]       file:line — problem
────────────────────────────────────────────────────────
PR Quality Score: X/10  (10 - critical*2 - informational*0.5)
```

For ASK items, present ONE AskUserQuestion:
```
[N] items need your input:

1. [CRITICAL] file:line — problem description
   Fix: specific recommended fix
   → A) Fix  B) Skip

RECOMMENDATION: Fix all critical items before landing.
```

---

## Log Results

```bash
vague timeline-log "{\"skill\":\"review\",\"event\":\"completed\",\"branch\":\"$(git branch --show-current)\",\"outcome\":\"success\",\"session\":\"$SESSION_ID\"}"
```

Log any non-obvious pattern discovered:
```bash
vague learnings-log '{"skill":"review","type":"pitfall","key":"SHORT_KEY","insight":"INSIGHT","confidence":8,"source":"observed","files":["path/to/file"]}'
```

---

---

## Observation Protocol

Throughout this skill's execution, watch for:
- Steps that produce wrong or suboptimal output
- Missing rules the user has to correct
- Workflow inefficiencies or unnecessary steps
- Gaps where a different skill would help
- **User corrections** — any time the user tells you to do something the skill should have done automatically (e.g. "read the plan", "check the tests first", "use the right branch")

When you notice any of these, log an observation:

```bash
vague observations-log '{"skill":"review","type":"improvement","issue":"WHAT_HAPPENED","suggestion":"CONCRETE_CHANGE","principle":"GENERALISABLE_TAKEAWAY","source_skill":"review"}'
```

**User correction detection:** If the user has to explicitly ask you to perform a step that should be part of this skill's workflow, log it immediately as a `type: correction` observation. These are the most valuable signals for skill improvement.

```bash
vague observations-log '{"skill":"review","type":"correction","issue":"User had to manually ask: WHAT_THEY_SAID","suggestion":"Add this as an explicit step in the skill","principle":"GENERALISABLE_TAKEAWAY","source_skill":"review"}'
```

Log silently — do not interrupt the user's workflow to announce observations.

---

## Handoff

> "Review complete. [N issues auto-fixed, N resolved, N remaining]. When ready: `/ship` to create the PR."
