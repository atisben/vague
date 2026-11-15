---
name: plan-eng
version: 1.0.0
description: |
  Eng manager-mode plan review. Lock in architecture, data flow, edge cases,
  test strategy, and performance. Interactive, opinionated, one issue at a time.
  Trigger: "review the architecture", "engineering review", "lock in the plan".
benefits-from:
  - plan-ideation
sdk_commands:
  - vague context
  - vague memory-log
  - vague memory-search
allowed-tools:
  - Read
  - Write
  - Bash
  - AskUserQuestion
  - WebSearch
---

## Preamble

```bash
eval "$(vague context --shell --skill plan-eng)"
VAGUE_HOME="${VAGUE_HOME:-$HOME/.vague}"
```

---

## Step 0: Load Context

```bash
eval "$(vague context --shell --skill plan-eng)"
VAGUE_HOME="${VAGUE_HOME:-$HOME/.vague}"
vague memory-search --kind doc --skill plan-ideation || echo "NO_DESIGN_DOCS"
vague memory-search --kind doc --skill plan-eng || echo "NO_ENG_PLAN"
[ -f CLAUDE.md ] && cat CLAUDE.md || echo "NO_CLAUDE_MD"
git log --oneline -5 2>/dev/null || true
```

Each search line prints as `scope/key  [skill]  text  (files: <path>)`, newest first. The path is a vault note. Read the newest `design-doc-*` note. If a `ceo-plan-*` note exists, read it too — scope decisions and deferred items from the CEO review should inform architecture choices. An `eng-plan-*` key for this branch means an earlier plan exists: revise that note rather than starting over. Ask the user to confirm which plan to review.

---

## Critical Rule: One Question at a Time

**STOP** after each issue. AskUserQuestion once per issue. Never batch. Always state your recommendation and why. If the fix is obvious and non-controversial, apply it and say what you did — don't waste a question.

---

## Core Principle: Test-Driven Design

This skill is **TDD-first**. The engineering plan is not complete until the test layer is fully specified **before** any implementation function is designed in detail.

The required order of thinking is:

1. **Architecture & data model** — what exists and how it connects.
2. **Test layer** — what observable behaviors prove the system works, written as failing tests *before* implementation begins.
3. **Implementation** — the functions/modules that make those tests pass.

When writing the final plan, the implementation roadmap **must** be expressed as: "write failing test → implement minimum code → make test green → refactor". Reject any plan section that lists implementation work without a corresponding test that gates it.

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

## Section 3: Test Layer (TDD Gate)

**This section runs before any implementation planning. No function design proceeds until the test layer below is locked in.**

For every new behavior in the plan, specify:

- **Test pyramid breakdown** — which behaviors are unit-tested, which need integration tests, which need e2e/manual QA. Justify each placement.
- **Failing tests first** — for each new public function or module, name the specific test file (e.g. `tests/test_<module>.py::test_<behavior>`) that must exist and fail *before* implementation starts.
- **Path coverage** — explicit test cases for the nil path, empty path, and error path from Section 1's data flow diagrams.
- **Fixtures and factories** — what test data, mocks, or fixtures are required? Where do they live?
- **Integration tests** — what cross-component flows need to be exercised end-to-end?
- **Regression guards** — any existing behavior that could silently break? Pin it with a test before touching the code.
- **Manual QA steps** — anything that can't be automated, with explicit reproduction steps.
- **Test runner** — confirm the project uses `uv run pytest` (or equivalent) and that new tests will be picked up by `pre-commit` / CI.

Produce two named subsections in the final plan:

- `## Key Interactions to Verify` — each critical user flow as a one-liner.
- `## Edge Cases` — each edge case that must be tested.

**Exit criterion:** every implementation task in Section 4 must reference at least one test from this section that gates it. If it doesn't, the plan is incomplete — go back and add the test.

**STOP after each issue.**

---

## Section 4: Implementation Plan

Only enter this section once Section 3 is locked. For each module or function:

- Name the failing test(s) from Section 3 it makes pass.
- Sketch the minimum implementation (signature, key branches, dependencies).
- Note any refactor that should follow once the test is green.

Reject any item here that does not map back to a test in Section 3.

**STOP after each issue.**

---

## Section 5: Performance Review

- N+1 query risks — name the specific query
- Caching opportunities — where, what TTL, invalidation strategy
- Memory concerns — any unbounded growth?
- Slow paths — estimate latency for the critical path

**STOP after each issue.**

---

## Section 6: Security Review

- Input validation — what's validated, what's not?
- Authorization — can a user access another user's data?
- Injection risks — SQL, command, template
- Secrets handling — are credentials hard-coded anywhere?
- Rate limiting — any endpoint that needs it?

**STOP after each issue.**

---

## Write the Engineering Plan

The plan is a vault note titled `Eng Plan - [Feature Name]`. Its structure goes in the `<content>` part of the vault template, without its own H1. The `## Next Steps` checkboxes become the template's `# Next Actions` list.

Structure:
```markdown
**Date:** [ISO date]
**Repo / branch:** $SLUG / $BRANCH
**Based on:** [source doc(s)]

## Architecture Diagram
[ASCII dependency graph]

## Data Flow
[ASCII diagrams — happy/nil/empty/error paths]

## Data Model Changes
[Tables, columns, migrations]

## Test Layer (write these first — they must fail before implementation begins)
### Test Pyramid
- [unit / integration / e2e split with justification]

### Failing Tests to Author First
- `tests/test_<module>.py::test_<behavior>` — covers [behavior]

### Fixtures & Factories
- [fixture] in [location]

### Key Interactions to Verify
- [interaction] on [component]

### Edge Cases
- [edge case]

### Critical Paths
- [end-to-end flow that must work]

### Test Runner & CI
- Run locally with `uv run pytest`
- Gated by `pre-commit run --all-files` before commit

## Implementation Plan (TDD: red → green → refactor)
Each item must reference the failing test from the Test Layer it makes pass.
- [ ] Write failing test: `tests/.../test_x.py::test_y`
- [ ] Implement minimum code in `src/.../x.py` to make it green
- [ ] Refactor; ensure `uv run pytest` and `pre-commit` stay green

## Performance Notes
[N+1 risks, caching, slow paths]

## Security Notes
[Auth, validation, injection risks]

## Open Questions
[Unresolved items]

## Reviewer Concerns
[Unresolved issues after review]

# Next Actions
- [ ] /diagram (architecture overview, if the plan touches several components)
- [ ] /dev-implement to implement
- [ ] /dev-ship
```

Show to user, support revision loops, then save it in two steps.

1. Save the note through the `/vault` skill (see its "Saving for Another Skill" section). Use `6. Atomic Notes/Alma/` and add the `alma` tag for Alma work:

   ```
   /vault save "Eng Plan - [Feature Name]" folder "6. Atomic Notes/" tags "engineering,architecture,code" kind "plan"
   ```

2. Point the ledger at the note. The key carries the branch, so a newer plan on the same branch replaces the older pointer:

   ```bash
   eval "$(vague context --shell --skill plan-eng)" >/dev/null
   BRANCH_KEY=$(printf '%s' "$BRANCH" | tr -c 'A-Za-z0-9._-' '-')
   vague memory-log "eng-plan-$BRANCH_KEY" "<one-line summary of the plan>" --doc --files "<VAULT_NOTE path>" --skill plan-eng
   ```

   `BRANCH_KEY` replaces the `/` in a branch name, because a key cannot hold one.

---

## Observation Protocol

Log feedback about this skill with `vague memory-log <key> "<issue → suggestion>" --about plan-eng` (see the Memory guideline).

---

## Handoff

> "Engineering plan saved to the vault. You're ready to build. Run `/dev-implement` to implement, or `/diagram` first to draw the architecture overview."

Log any non-obvious architectural insight the review found, with the `--files` it touches.
