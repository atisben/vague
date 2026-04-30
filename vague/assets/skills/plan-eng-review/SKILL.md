---
name: plan-eng-review
version: 1.0.0
description: |
  Eng manager-mode plan review. Lock in architecture, data flow, edge cases,
  test strategy, and performance. Interactive, opinionated, one issue at a time.
  Trigger: "review the architecture", "engineering review", "lock in the plan".
benefits-from:
  - office-hours
  - plan-ceo-review
sdk_commands:
  - vague init
  - vague learnings-log
requires_slug: true
requires_planning: false
allowed-tools:
  - Read
  - Write
  - Bash
  - AskUserQuestion
  - WebSearch
---

## Preamble

```bash
CONTEXT=$(vague init)
SLUG=$(echo "$CONTEXT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['slug'])")
BRANCH=$(echo "$CONTEXT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['branch'])")
PROACTIVE=$(echo "$CONTEXT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['proactive'])")
VAGUE_HOME="${VAGUE_HOME:-$HOME/.vague}"
```

---

## Step 0: Load Context

```bash
ls -t "$VAGUE_HOME/projects/$SLUG/designs/"*.md 2>/dev/null | head -5 || echo "NO_DESIGN_DOCS"
[ -f CLAUDE.md ] && cat CLAUDE.md || echo "NO_CLAUDE_MD"
git log --oneline -5 2>/dev/null || true
```

Read the most recent design doc and CEO plan (if exists). Ask the user to confirm which plan to review.

---

## Critical Rule: One Question at a Time

**STOP** after each issue. AskUserQuestion once per issue. Never batch. Always state your recommendation and why. If the fix is obvious and non-controversial, apply it and say what you did — don't waste a question.

---

## Section 1: Architecture Review

Evaluate and diagram:

- **System design and component boundaries** — Draw the dependency graph in ASCII.
- **Data flow** — For every new data flow, diagram all four paths:
  - Happy path (data flows correctly)
  - Nil path (input is nil/missing)
  - Empty path (input is present but empty)
  - Error path (upstream call fails)
- **State machines** — ASCII diagram for every new stateful object. Include invalid transitions.
- **Coupling** — What is now coupled that wasn't before? Is that justified?
- **Scaling** — What breaks first at 10x load?
- **Single points of failure** — Map them.
- **Security** — Auth boundaries, data access patterns, new API surfaces. For each: who can call it, what do they get, what can they change?
- **Rollback** — If this ships and breaks, what's the rollback? Git revert? Feature flag? DB migration rollback?

**STOP after each issue. One AskUserQuestion per issue.**

---

## Section 2: Data Model Review

- New tables, columns, indexes — are they justified?
- Migration safety — is the migration reversible? Does it lock tables?
- Null handling — what happens when expected data is absent?
- Soft delete vs hard delete — which pattern and why?
- Data types — correct precision, encoding, constraints?

**STOP after each issue.**

---

## Section 3: Test Strategy

For every new behavior in the plan:

- What tests must exist before this ships?
- What test cases cover the nil path, empty path, and error path from Section 1?
- What integration tests are needed?
- What manual QA steps are required?

Write a `## Key Interactions to Verify` section listing each critical user flow.

Write a `## Edge Cases` section listing each edge case that must be tested.

**STOP after each issue.**

---

## Section 4: Performance Review

- N+1 query risks — name the specific query
- Caching opportunities — where, what TTL, invalidation strategy
- Memory concerns — any unbounded growth?
- Slow paths — estimate latency for the critical path

**STOP after each issue.**

---

## Section 5: Security Review

- Input validation — what's validated, what's not?
- Authorization — can a user access another user's data?
- Injection risks — SQL, command, template
- Secrets handling — are credentials hard-coded anywhere?
- Rate limiting — any endpoint that needs it?

**STOP after each issue.**

---

## Write the Engineering Plan

Save to:
```
$VAGUE_HOME/projects/$SLUG/designs/{slug}-{branch}-eng-{YYYYMMDD}.md
```

Structure:
```markdown
# Engineering Plan: [Feature Name]

**Date:** [ISO date]
**Based on:** [source doc(s)]

## Architecture Diagram
[ASCII dependency graph]

## Data Flow
[ASCII diagrams — happy/nil/empty/error paths]

## Data Model Changes
[Tables, columns, migrations]

## Test Strategy
### Key Interactions to Verify
- [interaction] on [component]

### Edge Cases
- [edge case]

### Critical Paths
- [end-to-end flow that must work]

## Performance Notes
[N+1 risks, caching, slow paths]

## Security Notes
[Auth, validation, injection risks]

## Open Questions
[Unresolved items]

## Reviewer Concerns
[Unresolved issues after review]

## Next Steps
- [ ] /design-review (if UI changes)
- [ ] /ship to implement
```

Show to user, support revision loops, then save.

---

## Handoff

> "Engineering plan saved. You're ready to build. Run `/ship` to implement, or `/design-review` first if there are visual components."

Log a learning if any non-obvious architectural insight was discovered:
```bash
vague learnings-log '{"skill":"plan-eng-review","type":"architecture","key":"SHORT_KEY","insight":"INSIGHT","confidence":8,"source":"observed"}'
```
