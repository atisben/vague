---
name: ship
version: 1.0.0
description: |
  Ship workflow: implement, run tests, review diff, bump VERSION, update CHANGELOG,
  commit, push, create PR. Never push directly — always creates a PR.
  Trigger: "ship", "deploy", "push to main", "create a PR", "merge and push".
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
  - Write
  - Edit
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

**Proactive invocation:** When the user says code is ready, asks about deploying, wants to push, or asks to create a PR — invoke this skill rather than doing it ad-hoc.

---

## Step 1: Detect Context

```bash
VAGUE_HOME="${VAGUE_HOME:-$HOME/.vague}"
# Detect platform
which gh 2>/dev/null && echo "PLATFORM: github" || echo "PLATFORM: unknown"
which glab 2>/dev/null && echo "PLATFORM: gitlab" || true
# Current branch
BRANCH=$(git branch --show-current 2>/dev/null || echo "unknown")
echo "BRANCH: $BRANCH"
# Base branch
BASE=$(git remote show origin 2>/dev/null | grep 'HEAD branch' | awk '{print $NF}' || echo "main")
echo "BASE: $BASE"
# Diff summary
git diff origin/$BASE --stat 2>/dev/null || echo "NO_DIFF"
# Check for pending designs/plans
ls -t "$VAGUE_HOME/projects/$SLUG/designs/"*.md 2>/dev/null | head -5 || echo "NO_PENDING_DESIGNS"
```

If on the base branch, ask: "You're on `$BASE`. Should I create a feature branch first?"

**If there is no diff but pending designs exist:** Read the most recent design/engineering plan. Tell the user: "No code changes yet, but I found a pending plan: [filename]. Should I implement it first?" If yes, implement the plan, then continue with the ship workflow.

---

## Step 2: Merge Base Branch

```bash
git fetch origin $BASE
git merge origin/$BASE --no-edit 2>/dev/null || echo "MERGE_CONFLICTS"
```

If merge conflicts exist, STOP. Resolve them with the user before proceeding.

---

## Step 3: Run Tests

Detect and run the project's test suite:
```bash
# Detect test runner from CLAUDE.md or project files
[ -f CLAUDE.md ] && grep -A2 "## Testing" CLAUDE.md || true
[ -f package.json ] && cat package.json | grep -E '"test"' || true
[ -f Gemfile ] && echo "RUNTIME: ruby" || true
```

Run the tests:
```bash
# Run the detected test command (from CLAUDE.md or auto-detected)
```

**If tests fail:**
- Identify which tests are failing
- Determine if the failure is pre-existing or introduced by this branch
- Pre-existing: add to TODOS and continue
- Introduced: STOP. Fix before shipping.

---

## Step 4: Review the Diff

```bash
git diff origin/$BASE
```

Read the full diff. Check for:
- Accidentally committed debug code, console.log, TODO comments
- Hardcoded secrets or credentials
- Obvious logic errors visible in the diff
- Files that shouldn't be committed (.env, large binaries)

Fix any issues found before proceeding.

---

## Step 5: Bump VERSION (if applicable)

```bash
[ -f VERSION ] && cat VERSION || echo "NO_VERSION_FILE"
[ -f package.json ] && grep '"version"' package.json || true
```

If a version file exists, ask:
> "Current version: [X]. Bump to: [patch/minor/major]?"
> A) Patch (bug fixes)   B) Minor (new features)   C) Major (breaking changes)   D) Skip

Apply the bump.

---

## Step 6: Update CHANGELOG

```bash
[ -f CHANGELOG.md ] && head -30 CHANGELOG.md || echo "NO_CHANGELOG"
```

If CHANGELOG exists, prepend a new entry:
```markdown
## [version] - YYYY-MM-DD

### Added
- [new features]

### Fixed
- [bug fixes]

### Changed
- [changes to existing behavior]
```

---

## Step 7: Commit

```bash
git add -A
```

Show the staged files. Ask for commit message confirmation via AskUserQuestion if the auto-generated message is unclear.

Auto-generate a commit message:
- `feat: [description]` for new features
- `fix: [description]` for bug fixes
- `chore: [description]` for maintenance
- `docs: [description]` for documentation

```bash
git commit -m "[type]: [description]"
```

---

## Step 8: Push and Create PR

```bash
git push origin $BRANCH
```

Create PR (GitHub):
```bash
gh pr create \
  --title "[type]: [description]" \
  --body "## Summary
[What this PR does]

## Changes
[Bullet list of changes from diff]

## Test Plan
[How to verify this works]

## Checklist
- [ ] Tests pass
- [ ] CHANGELOG updated
- [ ] No debug code
" \
  --base $BASE
```

---

## Step 9: Log Completion

```bash
vague timeline-log "{\"skill\":\"ship\",\"event\":\"completed\",\"branch\":\"$BRANCH\",\"outcome\":\"success\",\"session\":\"$SESSION_ID\"}"
```

Log any learnings discovered during implementation:
```bash
# If a non-obvious pattern or pitfall was encountered:
vague learnings-log '{"skill":"ship","type":"pitfall","key":"SHORT_KEY","insight":"INSIGHT","confidence":8,"source":"observed"}'
```

---

---

## Observation Protocol

Throughout this skill's execution, watch for:
- Steps that produce wrong or suboptimal output
- Missing rules the user has to correct
- Workflow inefficiencies or unnecessary steps
- Gaps where a different skill would help

When you notice any of these, log an observation:

```bash
vague observations-log '{{"skill":"ship","type":"improvement","issue":"WHAT_HAPPENED","suggestion":"CONCRETE_CHANGE","principle":"GENERALISABLE_TAKEAWAY","source_skill":"ship"}}'
```

Log silently — do not interrupt the user's workflow to announce observations.

---

## Handoff

> "PR created: [URL]. Next: `/review` for a pre-landing code review, or ask a teammate to review."
