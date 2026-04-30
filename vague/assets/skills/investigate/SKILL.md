---
name: investigate
version: 1.0.0
description: |
  Systematic debugging. Four phases: investigate, analyze, hypothesize, implement.
  Iron Law: no fixes without root cause.
  Trigger: "debug this", "fix this bug", "why is this broken", "root cause analysis".
sdk_commands:
  - vague init
  - vague learnings-log
requires_slug: true
requires_planning: false
allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
  - AskUserQuestion
  - WebSearch
---

## Preamble

```bash
CONTEXT=$(vague init)
SLUG=$(echo "$CONTEXT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['slug'])")
BRANCH=$(echo "$CONTEXT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['branch'])")
PROACTIVE=$(echo "$CONTEXT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['proactive'])")
```

**Proactive invocation:** When the user reports errors, stack traces, unexpected behavior, or "it was working yesterday" — invoke this skill rather than debugging ad-hoc.

---

## IRON LAW

**Never apply a fix without a confirmed root cause.** A fix without root cause is a guess. Guesses create new bugs.

---

## Phase 1: Investigate

Gather all available evidence before forming any hypothesis.

```bash
# Recent changes
git log --oneline -10 2>/dev/null
git diff HEAD~5..HEAD --stat 2>/dev/null || true
# Environment
echo "NODE: $(node --version 2>/dev/null || echo N/A)"
echo "RUBY: $(ruby --version 2>/dev/null || echo N/A)"
echo "PYTHON: $(python3 --version 2>/dev/null || echo N/A)"
# Recent errors in logs (if available)
tail -50 log/development.log 2>/dev/null || true
```

Ask the user:
1. "What exactly happens? (Paste the full error message / stack trace)"
2. "What were you doing when it happened?"
3. "When did it last work?"
4. "What changed between when it worked and now?"

Do NOT skip any of these questions. All four answers are required before Phase 2.

---

## Phase 2: Analyze

Map the failure:

**1. Identify the failure point:**
Read the stack trace from bottom to top. The last line of YOUR code (not library code) is where to start.

**2. Trace data flow:**
Starting from the failure point, trace backwards:
- Where did this data come from?
- What transformations happened to it?
- Where was it last in a known-good state?

**3. Draw the execution path:**
```
[entry point] → [transform A] → [transform B] → [FAILURE POINT] ← investigate here
```

**4. Check recent changes:**
Cross-reference the failure point with `git log` — did anyone touch this code recently?

**5. Check environment:**
- Does it fail in development but not production (or vice versa)?
- Does it fail for all users or just some?
- Does it fail consistently or intermittently?

---

## Phase 3: Hypothesize

State 2-3 hypotheses about the root cause. For each:

```
HYPOTHESIS A: [What you think the root cause is]
  Evidence for:   [what supports this]
  Evidence against: [what contradicts this]
  Test:           [how to verify or falsify this in < 5 minutes]
```

Order hypotheses by likelihood. Present to user and confirm which to test first.

Then test the highest-likelihood hypothesis:
- Write a reproduction case if possible
- Add targeted logging/debugging to verify the hypothesis
- Run the code with the modification

**If hypothesis is confirmed:** Document the root cause clearly before writing any fix.
**If hypothesis is falsified:** Move to the next hypothesis. Do not start fixing yet.

---

## Phase 4: Implement

Only after root cause is confirmed:

1. **Write the minimal fix** — the smallest change that addresses the root cause
2. **Explain the fix**: "This fixes [root cause] by [mechanism]. The bug was [X] because [Y]."
3. **Add a test** that would have caught this bug (regression test)
4. **Check for related instances**: `grep -r "similar_pattern" .` — is this bug present elsewhere?

Apply the fix.

Run tests to confirm the fix works and nothing else broke:
```bash
# Run relevant tests
```

---

## Log the Learning

Always log what was found:

```bash
vague learnings-log "{\"skill\":\"investigate\",\"type\":\"pitfall\",\"key\":\"SHORT-KEBAB-KEY\",\"insight\":\"Root cause: [mechanism]. Fix: [what was changed]. Watch for: [where else this can appear].\",\"confidence\":9,\"source\":\"observed\",\"files\":[\"path/to/file\"]}"
```

---

## Handoff

> "Root cause confirmed and fixed. Regression test added. Run `/review` before landing, or `/ship` if the fix is small and self-contained."
