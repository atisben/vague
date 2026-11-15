---
name: dev-ship
version: 1.0.0
description: |
  Ship workflow: run tests, review diff, bump VERSION, update CHANGELOG,
  commit, push, create PR. Never push directly — always creates a PR.
  Trigger: "ship", "deploy", "push to main", "create a PR", "merge and push".
sdk_commands:
  - vague context
  - vague memory-log
  - vague memory-search
requires_slug: true
allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
  - AskUserQuestion
---

## Preamble

```bash
eval "$(vague context --shell --skill dev-ship)"
```

**Proactive invocation:** When the user says code is ready, asks about deploying, wants to push, or asks to create a PR — invoke this skill rather than doing it ad-hoc.

---

## Step 1: Detect Context

```bash
eval "$(vague context --shell --skill dev-ship)"
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
# Find the engineering plans (doc pointers to vault notes), newest first
vague memory-search --kind doc --skill plan-eng || echo "PLAN: NONE"
```

Each line prints as `scope/key  [skill]  text  (files: <path>)`. The plan for this branch has the key `eng-plan-<branch>`, with every `/` in the branch replaced by `-`. Take the path of that line, or of the newest line when no key matches. Call it `$PLAN_FILE`: it is a vault note.

**If `$PLAN_FILE` exists, read it now.** Use it for context throughout: commit messages, PR description, and the review checklist should reference the plan's goals and test strategy.

If on the base branch, ask: "You're on `$BASE`. Should I create a feature branch first?"

**If there is no diff but pending designs exist:** Tell the user: "No code changes yet, but I found a pending plan: [filename]. Run `/dev-implement` to build it first." Stop there: this skill lands code, it does not write it.

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

## Step 9: Update Plan

If `$PLAN_FILE` exists, update that vault note with Edit:
- Mark completed items in `# Next Actions` (check the `/dev-ship` checkbox)
- Add a `## Shipped` section just above `# Next Actions`:

```markdown
## Shipped

**Date:** [ISO date]
**PR:** [PR URL]
**Branch:** $BRANCH
```

---

## Step 10: Log Learnings

Log a pitfall that shipping hit, such as a CI quirk or a hook that aborts silently.

---

## Observation Protocol

Log feedback about this skill with `vague memory-log <key> "<issue → suggestion>" --about dev-ship` (see the Memory guideline).

---

## Handoff

> "PR created: [URL]. Next: `/dev-review` for a Standards and Spec review, `/code-review` for a pre-landing bug hunt, or ask a teammate to review."
